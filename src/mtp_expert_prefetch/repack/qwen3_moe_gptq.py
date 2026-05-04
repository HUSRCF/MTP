from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from safetensors import safe_open
from safetensors.torch import save_file


EXPERT_KEY_RE = re.compile(
    r"^(?P<prefix>model\.language_model\.layers\.(?P<layer>\d+)\.mlp\.experts)"
    r"\.(?P<expert>\d+)\.(?P<projection>down_proj|gate_proj|up_proj)"
    r"\.(?P<kind>g_idx|qweight|qzeros|scales)$"
)

PROJECTIONS = ("down_proj", "gate_proj", "up_proj")
KINDS = ("g_idx", "qweight", "qzeros", "scales")


@dataclass(frozen=True)
class ExpertKey:
    key: str
    layer: int
    expert: int
    projection: str
    kind: str


class ShardedSafeTensorReader:
    def __init__(self, snapshot_path: Path) -> None:
        self.snapshot_path = snapshot_path
        self.index_path = snapshot_path / "model.safetensors.index.json"
        if not self.index_path.exists():
            msg = f"Missing safetensors index: {self.index_path}"
            raise FileNotFoundError(msg)
        with self.index_path.open("r", encoding="utf-8") as handle:
            self.index = json.load(handle)
        self.weight_map: dict[str, str] = self.index["weight_map"]
        self._handles: dict[str, Any] = {}

    def get_tensor(self, key: str) -> torch.Tensor:
        shard_name = self.weight_map[key]
        handle = self._handles.get(shard_name)
        if handle is None:
            shard_path = self.snapshot_path / shard_name
            if not shard_path.exists():
                msg = f"Missing shard for {key}: {shard_path}"
                raise FileNotFoundError(msg)
            handle = safe_open(shard_path, framework="pt", device="cpu")
            self._handles[shard_name] = handle
        return handle.get_tensor(key)


def parse_expert_key(key: str) -> ExpertKey | None:
    match = EXPERT_KEY_RE.match(key)
    if match is None:
        return None
    return ExpertKey(
        key=key,
        layer=int(match.group("layer")),
        expert=int(match.group("expert")),
        projection=match.group("projection"),
        kind=match.group("kind"),
    )


def discover_expert_keys(weight_map: dict[str, str]) -> dict[int, dict[str, dict[str, dict[int, str]]]]:
    grouped: dict[int, dict[str, dict[str, dict[int, str]]]] = {}
    for key in weight_map:
        parsed = parse_expert_key(key)
        if parsed is None:
            continue
        grouped.setdefault(parsed.layer, {}).setdefault(parsed.projection, {}).setdefault(
            parsed.kind, {}
        )[parsed.expert] = parsed.key
    return grouped


def parse_layers(layers: str | None, available_layers: list[int]) -> list[int]:
    if layers is None:
        return available_layers

    selected: set[int] = set()
    for part in layers.split(","):
        token = part.strip()
        if not token:
            continue
        if "-" in token:
            start_text, end_text = token.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            if end < start:
                msg = f"Invalid descending layer range: {token}"
                raise ValueError(msg)
            selected.update(range(start, end + 1))
        else:
            selected.add(int(token))

    unknown = sorted(selected.difference(available_layers))
    if unknown:
        msg = f"Requested layers are not present in checkpoint: {unknown}"
        raise ValueError(msg)
    return [layer for layer in available_layers if layer in selected]


def tensor_sha256(tensor: torch.Tensor) -> str:
    cpu_tensor = tensor.detach().cpu().contiguous()
    if cpu_tensor.dtype == torch.bfloat16:
        payload = cpu_tensor.view(torch.int16).numpy().tobytes()
    else:
        payload = cpu_tensor.numpy().tobytes()
    return hashlib.sha256(payload).hexdigest()


def _required_source_keys(
    layer_group: dict[str, dict[str, dict[int, str]]],
    *,
    layer: int,
    projection: str,
    kind: str,
    num_experts: int,
) -> list[str]:
    expert_map = layer_group.get(projection, {}).get(kind, {})
    missing = [expert for expert in range(num_experts) if expert not in expert_map]
    if missing:
        shown = missing[:16]
        suffix = "..." if len(missing) > len(shown) else ""
        msg = (
            f"Layer {layer} {projection}.{kind} is missing {len(missing)} experts: "
            f"{shown}{suffix}"
        )
        raise RuntimeError(msg)
    return [expert_map[expert] for expert in range(num_experts)]


def repack_layer(
    reader: ShardedSafeTensorReader,
    grouped_keys: dict[int, dict[str, dict[str, dict[int, str]]]],
    *,
    layer: int,
    output_dir: Path,
    num_experts: int,
    verify: bool,
) -> dict[str, Any]:
    output_tensors: dict[str, torch.Tensor] = {}
    tensor_manifest: dict[str, Any] = {}
    layer_group = grouped_keys[layer]

    for projection in PROJECTIONS:
        for kind in KINDS:
            source_keys = _required_source_keys(
                layer_group,
                layer=layer,
                projection=projection,
                kind=kind,
                num_experts=num_experts,
            )
            pieces = [reader.get_tensor(key) for key in source_keys]
            stacked = torch.stack(pieces, dim=0).contiguous()
            output_key = f"experts.{projection}.{kind}"

            if verify:
                for expert, piece in enumerate(pieces):
                    if not torch.equal(stacked[expert], piece):
                        msg = f"Repack verification failed for layer={layer} {output_key} expert={expert}"
                        raise RuntimeError(msg)

            output_tensors[output_key] = stacked
            tensor_manifest[output_key] = {
                "shape": list(stacked.shape),
                "dtype": str(stacked.dtype).replace("torch.", ""),
                "sha256": tensor_sha256(stacked),
                "source_count": len(source_keys),
                "source_shape": list(pieces[0].shape),
                "source_dtype": str(pieces[0].dtype).replace("torch.", ""),
                "source_key_template": (
                    f"model.language_model.layers.{layer}.mlp.experts.{{expert}}."
                    f"{projection}.{kind}"
                ),
            }

    output_path = output_dir / f"layer_{layer:02d}.safetensors"
    save_file(output_tensors, output_path)

    return {
        "layer": layer,
        "path": output_path.name,
        "num_experts": num_experts,
        "num_source_tensors": len(PROJECTIONS) * len(KINDS) * num_experts,
        "num_output_tensors": len(output_tensors),
        "tensors": tensor_manifest,
    }


def repack_qwen3_moe_gptq(
    snapshot_path: Path,
    output_dir: Path,
    *,
    layers: str | None = None,
    num_experts: int = 256,
    verify: bool = False,
    overwrite: bool = False,
) -> Path:
    snapshot_path = snapshot_path.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = output_dir / "manifest.jsonl"
    summary_path = output_dir / "summary.json"
    if manifest_path.exists() and not overwrite:
        msg = f"Refusing to overwrite existing manifest: {manifest_path}. Pass --overwrite."
        raise FileExistsError(msg)

    reader = ShardedSafeTensorReader(snapshot_path)
    grouped_keys = discover_expert_keys(reader.weight_map)
    available_layers = sorted(grouped_keys)
    selected_layers = parse_layers(layers, available_layers)
    if not selected_layers:
        msg = "No expert layers selected for repacking."
        raise RuntimeError(msg)

    total_source_tensors = 0
    total_output_tensors = 0
    with manifest_path.open("w", encoding="utf-8") as manifest:
        for layer in selected_layers:
            layer_manifest = repack_layer(
                reader,
                grouped_keys,
                layer=layer,
                output_dir=output_dir,
                num_experts=num_experts,
                verify=verify,
            )
            total_source_tensors += int(layer_manifest["num_source_tensors"])
            total_output_tensors += int(layer_manifest["num_output_tensors"])
            manifest.write(json.dumps(layer_manifest, sort_keys=True) + "\n")
            print(
                f"repacked layer {layer:02d}: "
                f"{layer_manifest['num_source_tensors']} -> {layer_manifest['num_output_tensors']} tensors"
            )

    summary = {
        "snapshot_path": str(snapshot_path),
        "output_dir": str(output_dir),
        "manifest_path": manifest_path.name,
        "layers": selected_layers,
        "num_layers": len(selected_layers),
        "num_experts": num_experts,
        "projections": list(PROJECTIONS),
        "kinds": list(KINDS),
        "total_source_tensors": total_source_tensors,
        "total_output_tensors": total_output_tensors,
        "reduction_factor": total_source_tensors / total_output_tensors
        if total_output_tensors
        else None,
        "verify": verify,
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def load_repack_manifest(repacked_dir: Path) -> dict[int, dict[str, Any]]:
    manifest_path = repacked_dir / "manifest.jsonl"
    if not manifest_path.exists():
        msg = f"Missing repack manifest: {manifest_path}"
        raise FileNotFoundError(msg)

    records: dict[int, dict[str, Any]] = {}
    with manifest_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            records[int(record["layer"])] = record
    if not records:
        msg = f"Repack manifest is empty: {manifest_path}"
        raise RuntimeError(msg)
    return records


def verify_random_repacked_slices(
    snapshot_path: Path,
    repacked_dir: Path,
    *,
    samples: int = 128,
    seed: int = 0,
    layers: str | None = None,
    num_experts: int | None = None,
    fail_fast: bool = True,
) -> dict[str, Any]:
    snapshot_path = snapshot_path.expanduser().resolve()
    repacked_dir = repacked_dir.expanduser().resolve()
    reader = ShardedSafeTensorReader(snapshot_path)
    manifest = load_repack_manifest(repacked_dir)

    available_layers = sorted(manifest)
    selected_layers = parse_layers(layers, available_layers)
    if not selected_layers:
        msg = "No repacked layers selected for verification."
        raise RuntimeError(msg)

    if num_experts is None:
        num_experts = int(next(iter(manifest.values())).get("num_experts", 256))

    rng = random.Random(seed)
    failures: list[dict[str, Any]] = []
    checked: list[dict[str, Any]] = []
    layer_handles: dict[int, Any] = {}

    def get_repacked_handle(layer: int) -> Any:
        handle = layer_handles.get(layer)
        if handle is None:
            layer_path = repacked_dir / manifest[layer]["path"]
            if not layer_path.exists():
                msg = f"Missing repacked layer file: {layer_path}"
                raise FileNotFoundError(msg)
            handle = safe_open(layer_path, framework="pt", device="cpu")
            layer_handles[layer] = handle
        return handle

    for sample_idx in range(samples):
        layer = rng.choice(selected_layers)
        expert = rng.randrange(num_experts)
        projection = rng.choice(PROJECTIONS)
        kind = rng.choice(KINDS)

        source_key = (
            f"model.language_model.layers.{layer}.mlp.experts.{expert}.{projection}.{kind}"
        )
        repacked_key = f"experts.{projection}.{kind}"

        original = reader.get_tensor(source_key)
        fused = get_repacked_handle(layer).get_tensor(repacked_key)
        if expert >= fused.shape[0]:
            msg = f"Expert index {expert} is out of range for {repacked_key}: {list(fused.shape)}"
            raise RuntimeError(msg)
        restored = fused[expert]
        ok = torch.equal(original, restored)

        check = {
            "sample_idx": sample_idx,
            "layer": layer,
            "expert": expert,
            "projection": projection,
            "kind": kind,
            "source_key": source_key,
            "repacked_key": repacked_key,
            "source_shape": list(original.shape),
            "repacked_slice_shape": list(restored.shape),
            "dtype": str(original.dtype).replace("torch.", ""),
            "ok": ok,
        }
        checked.append(check)
        if not ok:
            check["source_sha256"] = tensor_sha256(original)
            check["repacked_slice_sha256"] = tensor_sha256(restored)
            failures.append(check)
            if fail_fast:
                break

    return {
        "snapshot_path": str(snapshot_path),
        "repacked_dir": str(repacked_dir),
        "samples_requested": samples,
        "samples_checked": len(checked),
        "seed": seed,
        "layers": selected_layers,
        "num_experts": num_experts,
        "failures": failures,
        "ok": len(failures) == 0,
    }
