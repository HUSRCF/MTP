from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from safetensors import safe_open

from mtp_expert_prefetch.repack.qwen3_moe_gptq import KINDS, PROJECTIONS, tensor_sha256


SAFETENSORS_DTYPE_NAMES = {
    "BOOL": "bool",
    "F16": "float16",
    "BF16": "bfloat16",
    "F32": "float32",
    "F64": "float64",
    "I8": "int8",
    "I16": "int16",
    "I32": "int32",
    "I64": "int64",
    "U8": "uint8",
}


@dataclass(frozen=True)
class RepackedTensorInfo:
    layer: int
    projection: str
    kind: str
    key: str
    shape: tuple[int, ...]
    dtype: str
    sha256: str | None = None


class RepackedMoeExpertStore:
    """Lazy accessor for per-layer repacked Qwen3 MoE expert tensors."""

    def __init__(self, repacked_dir: str | Path, *, device: str = "cpu") -> None:
        self.repacked_dir = Path(repacked_dir).expanduser().resolve()
        self.device = device
        self.summary = self._load_summary()
        self.manifest = self._load_manifest()
        self.layers = tuple(sorted(self.manifest))
        if not self.layers:
            msg = f"No layers found in repack manifest: {self.repacked_dir}"
            raise RuntimeError(msg)
        self.num_experts = int(self.summary.get("num_experts", self.manifest[self.layers[0]]["num_experts"]))
        self.projections = tuple(self.summary.get("projections", PROJECTIONS))
        self.kinds = tuple(self.summary.get("kinds", KINDS))
        self._handles: dict[int, Any] = {}

    def _load_summary(self) -> dict[str, Any]:
        summary_path = self.repacked_dir / "summary.json"
        if not summary_path.exists():
            msg = f"Missing repack summary: {summary_path}"
            raise FileNotFoundError(msg)
        with summary_path.open("r", encoding="utf-8") as handle:
            summary = json.load(handle)
        if not isinstance(summary, dict):
            msg = f"Expected mapping in repack summary: {summary_path}"
            raise TypeError(msg)
        return summary

    def _load_manifest(self) -> dict[int, dict[str, Any]]:
        manifest_path = self.repacked_dir / "manifest.jsonl"
        if not manifest_path.exists():
            msg = f"Missing repack manifest: {manifest_path}"
            raise FileNotFoundError(msg)

        records: dict[int, dict[str, Any]] = {}
        with manifest_path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                record = json.loads(line)
                layer = int(record["layer"])
                if layer in records:
                    msg = f"Duplicate layer {layer} in {manifest_path}:{line_no}"
                    raise RuntimeError(msg)
                records[layer] = record
        return records

    def close(self) -> None:
        self._handles.clear()

    def __enter__(self) -> RepackedMoeExpertStore:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def layer_path(self, layer: int) -> Path:
        record = self._layer_record(layer)
        return self.repacked_dir / record["path"]

    def tensor_key(self, projection: str, kind: str) -> str:
        self._validate_projection_kind(projection, kind)
        return f"experts.{projection}.{kind}"

    def tensor_info(self, layer: int, projection: str, kind: str) -> RepackedTensorInfo:
        record = self._layer_record(layer)
        key = self.tensor_key(projection, kind)
        tensors = record.get("tensors", {})
        if key not in tensors:
            msg = f"Missing tensor metadata for layer={layer} key={key}"
            raise KeyError(msg)
        info = tensors[key]
        return RepackedTensorInfo(
            layer=layer,
            projection=projection,
            kind=kind,
            key=key,
            shape=tuple(int(dim) for dim in info["shape"]),
            dtype=str(info["dtype"]),
            sha256=info.get("sha256"),
        )

    def get_fused_tensor(self, layer: int, projection: str, kind: str) -> torch.Tensor:
        key = self.tensor_key(projection, kind)
        return self._layer_handle(layer).get_tensor(key)

    def get_expert_tensor(
        self,
        layer: int,
        expert: int,
        projection: str,
        kind: str,
    ) -> torch.Tensor:
        if expert < 0 or expert >= self.num_experts:
            msg = f"Expert index out of range: expert={expert}, num_experts={self.num_experts}"
            raise IndexError(msg)
        key = self.tensor_key(projection, kind)
        return self._layer_handle(layer).get_slice(key)[expert]

    def inspect(self, *, check_hashes: bool = False) -> dict[str, Any]:
        missing_files: list[str] = []
        missing_keys: list[dict[str, Any]] = []
        shape_mismatches: list[dict[str, Any]] = []
        dtype_mismatches: list[dict[str, Any]] = []
        hash_mismatches: list[dict[str, Any]] = []

        for layer in self.layers:
            layer_path = self.layer_path(layer)
            if not layer_path.exists():
                missing_files.append(str(layer_path))
                continue
            handle = self._layer_handle(layer)
            available_keys = set(handle.keys())

            for projection in self.projections:
                for kind in self.kinds:
                    info = self.tensor_info(layer, projection, kind)
                    if info.key not in available_keys:
                        missing_keys.append({"layer": layer, "key": info.key})
                        continue

                    tensor_slice = handle.get_slice(info.key)
                    actual_shape = tuple(int(dim) for dim in tensor_slice.get_shape())
                    actual_dtype = normalize_safetensors_dtype(str(tensor_slice.get_dtype()))
                    if actual_shape != info.shape:
                        shape_mismatches.append(
                            {
                                "layer": layer,
                                "key": info.key,
                                "expected": list(info.shape),
                                "actual": list(actual_shape),
                            }
                        )
                    if actual_dtype != info.dtype:
                        dtype_mismatches.append(
                            {
                                "layer": layer,
                                "key": info.key,
                                "expected": info.dtype,
                                "actual": actual_dtype,
                            }
                        )
                    if check_hashes and info.sha256 is not None:
                        digest = tensor_sha256(handle.get_tensor(info.key))
                        if digest != info.sha256:
                            hash_mismatches.append(
                                {
                                    "layer": layer,
                                    "key": info.key,
                                    "expected": info.sha256,
                                    "actual": digest,
                                }
                            )

        ok = not (
            missing_files
            or missing_keys
            or shape_mismatches
            or dtype_mismatches
            or hash_mismatches
        )
        return {
            "ok": ok,
            "repacked_dir": str(self.repacked_dir),
            "layers": list(self.layers),
            "num_layers": len(self.layers),
            "num_experts": self.num_experts,
            "projections": list(self.projections),
            "kinds": list(self.kinds),
            "total_output_tensors": sum(
                int(record.get("num_output_tensors", 0)) for record in self.manifest.values()
            ),
            "missing_files": missing_files,
            "missing_keys": missing_keys,
            "shape_mismatches": shape_mismatches,
            "dtype_mismatches": dtype_mismatches,
            "hash_mismatches": hash_mismatches,
            "checked_hashes": check_hashes,
        }

    def _layer_record(self, layer: int) -> dict[str, Any]:
        try:
            return self.manifest[layer]
        except KeyError as exc:
            msg = f"Layer {layer} is not present in repacked store"
            raise KeyError(msg) from exc

    def _layer_handle(self, layer: int) -> Any:
        self._layer_record(layer)
        handle = self._handles.get(layer)
        if handle is None:
            layer_path = self.layer_path(layer)
            if not layer_path.exists():
                msg = f"Missing repacked layer file: {layer_path}"
                raise FileNotFoundError(msg)
            handle = safe_open(layer_path, framework="pt", device=self.device)
            self._handles[layer] = handle
        return handle

    def _validate_projection_kind(self, projection: str, kind: str) -> None:
        if projection not in self.projections:
            msg = f"Unknown projection {projection!r}; expected one of {self.projections}"
            raise ValueError(msg)
        if kind not in self.kinds:
            msg = f"Unknown tensor kind {kind!r}; expected one of {self.kinds}"
            raise ValueError(msg)


def normalize_safetensors_dtype(dtype: str) -> str:
    return SAFETENSORS_DTYPE_NAMES.get(dtype, dtype)
