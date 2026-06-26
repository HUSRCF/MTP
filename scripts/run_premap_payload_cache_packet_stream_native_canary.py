#!/usr/bin/env python3
"""Run a manifest-backed native packet-stream producer-state canary.

The older stream canary used a synthetic steps x layers expert stream. This
canary consumes packet exports emitted by the online vLLM prelaunch shadow path
and checks that native graph replay can reproduce the shifted issue-generation
contract while still avoiding payload transfer and current WNA16 kernel args.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import run_premap_payload_cache_producer_state_stream_stub as stream_stub

PACKET_STREAM_MAGIC = 0x5054434D
PACKET_STREAM_VERSION = 2
MAX_PACKET_COUNT = 65536
MAX_EXPERT_ROWS = 16 * 1024 * 1024
STREAM_HASH_OFFSET = 0xCBF29CE484222325
STREAM_HASH_PRIME = 0x100000001B3
STREAM_HASH_MASK = (1 << 64) - 1

FALSE_SAFETY_FIELDS = (
    "kernel_arg_pass",
    "kernel_arg_pass_allowed",
    "passed_to_kernel",
    "passes_current_wna16_args",
    "uses_current_wna16_args",
    "current_wna16_arg_compatible",
    "changes_kernel_launch_args",
    "payload_transfer_enabled",
    "payload_deref_allowed",
    "ready_credit",
    "ready_before_demand_credit",
    "real_ready_credit_granted",
    "measures_tpot",
    "measures_vllm_latency",
)

OPTIONAL_FALSE_SAFETY_FIELDS = ("current_wna16_arg_compatible",)


def _stream_hash_mix(value: int, item: int) -> int:
    return ((int(value) ^ (int(item) & 0xFFFFFFFF)) * STREAM_HASH_PRIME) & STREAM_HASH_MASK


def _expected_native_packet_issue_hash(issue_expert_rows: list[list[int]]) -> str:
    aggregate_hash = STREAM_HASH_OFFSET
    for row in issue_expert_rows:
        local_hash = STREAM_HASH_OFFSET
        for expert in row:
            local_hash = _stream_hash_mix(local_hash, expert)
        local_hash = _stream_hash_mix(local_hash, len(row))
        aggregate_hash = _stream_hash_mix(aggregate_hash, local_hash & 0xFFFFFFFF)
    return f"{aggregate_hash:016x}"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _int_field(payload: dict[str, Any], key: str, failures: list[str]) -> int | None:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        failures.append(f"{key}_invalid")
        return None
    if value < 0:
        failures.append(f"{key}_negative")
        return None
    return value


def _zero_int(value: Any) -> bool:
    return type(value) is int and value == 0


def _normalize_native_result(native: Any) -> dict[str, Any]:
    if not isinstance(native, dict):
        return {
            "ok": False,
            "passed": False,
            "failures": ["native_result_not_object"],
            "native_returncode": 1,
        }
    failures = native.get("failures")
    if failures is None:
        native["failures"] = []
    elif not isinstance(failures, list) or any(
        not isinstance(item, str) for item in failures
    ):
        native["failures"] = ["native_failures_invalid"]
    return native


def _bool_false_field(
    payload: dict[str, Any],
    key: str,
    failures: list[str],
    *,
    packet_index: int,
) -> None:
    value = payload.get(key)
    if key in OPTIONAL_FALSE_SAFETY_FIELDS and key not in payload:
        return
    if value is not False:
        failures.append(f"packet_{packet_index}_{key}_not_false")


def _manifest_false_field(
    manifest: dict[str, Any],
    key: str,
    failures: list[str],
) -> None:
    if key in OPTIONAL_FALSE_SAFETY_FIELDS and key not in manifest:
        return
    if manifest.get(key) is not False:
        failures.append(f"manifest_{key}_not_false")


def _parse_expert_list(
    payload: dict[str, Any],
    key: str,
    *,
    count: int | None,
    max_num_experts: int | None,
    failures: list[str],
    packet_index: int,
) -> list[int]:
    raw = payload.get(key)
    if not isinstance(raw, list):
        failures.append(f"packet_{packet_index}_{key}_invalid")
        raw = []
    parsed: list[int] = []
    for expert_index, expert in enumerate(raw):
        if isinstance(expert, bool) or not isinstance(expert, int) or expert < 0:
            failures.append(f"packet_{packet_index}_{key}_{expert_index}_invalid")
            continue
        if max_num_experts is not None and expert >= max_num_experts:
            failures.append(f"packet_{packet_index}_{key}_{expert_index}_oob")
            continue
        parsed.append(expert)
    if count is not None and count != len(parsed):
        failures.append(f"packet_{packet_index}_{key}_count_mismatch")
    return parsed


def _packet_paths_from_manifest(
    manifest: dict[str, Any],
    failures: list[str],
) -> list[Path]:
    raw_paths = manifest.get("online_packet_export_paths")
    if not isinstance(raw_paths, list) or not raw_paths:
        failures.append("online_packet_export_paths_missing")
        return []
    paths: list[Path] = []
    for index, raw_path in enumerate(raw_paths):
        if not isinstance(raw_path, str) or not raw_path:
            failures.append(f"online_packet_export_path_{index}_invalid")
            continue
        path = Path(raw_path)
        if not path.is_absolute():
            path = REPO_ROOT / path
        if not path.exists():
            failures.append(f"online_packet_export_path_{index}_missing")
            continue
        paths.append(path)
    return paths


def _materialize_packet_stream(
    *,
    manifest_path: Path,
    output_bin: Path,
) -> dict[str, Any]:
    failures: list[str] = []
    manifest = _load_json(manifest_path)
    if manifest.get("passed") is not True or manifest.get("ok") is not True:
        failures.append("manifest_not_passed")
    value = manifest.get("payload_bytes")
    if isinstance(value, bool) or value != 0:
        failures.append("manifest_payload_bytes_nonzero")
    for key in FALSE_SAFETY_FIELDS:
        _manifest_false_field(manifest, key, failures)

    packet_paths = _packet_paths_from_manifest(manifest, failures)
    packets = [_load_json(path) for path in packet_paths]
    if len(packets) > MAX_PACKET_COUNT:
        failures.append("packet_count_exceeds_safety_bound")

    layer_ids: list[int] = []
    current_counts: list[int] = []
    previous_counts: list[int] = []
    issue_counts: list[int] = []
    state_override_flags: list[int] = []
    current_expert_rows: list[list[int]] = []
    previous_expert_rows: list[list[int]] = []
    issue_expert_rows: list[list[int]] = []
    transition_topk_values: set[int] = set()
    max_num_expert_values: set[int] = set()
    max_layer_id = 0
    max_current_count = 0
    max_previous_count = 0
    max_issue_count = 0
    carried_state_by_layer: dict[int, list[int]] = {}
    state_override_count = 0

    for packet_index, packet in enumerate(packets):
        for key in FALSE_SAFETY_FIELDS:
            _bool_false_field(packet, key, failures, packet_index=packet_index)
        context = packet.get("_export_context")
        if not isinstance(context, dict):
            failures.append(f"packet_{packet_index}_export_context_missing")
            context = {}
        for key in FALSE_SAFETY_FIELDS:
            _bool_false_field(context, key, failures, packet_index=packet_index)
        context_payload_bytes = context.get("payload_bytes")
        if isinstance(context_payload_bytes, bool) or context_payload_bytes != 0:
            failures.append(f"packet_{packet_index}_context_payload_bytes_nonzero")
        payload_bytes = packet.get("payload_bytes")
        if isinstance(payload_bytes, bool) or payload_bytes != 0:
            failures.append(f"packet_{packet_index}_payload_bytes_nonzero")
        if packet.get("state_owner") != "producer":
            failures.append(f"packet_{packet_index}_state_owner_not_producer")

        layer_id = _int_field(packet, "layer_id", failures)
        current_count = _int_field(packet, "current_expert_count", failures)
        previous_count = _int_field(packet, "previous_expert_count", failures)
        issue_count = _int_field(packet, "issue_candidate_count", failures)
        transition_topk_count = _int_field(packet, "transition_topk_count", failures)
        max_num_experts = _int_field(packet, "max_num_experts", failures)
        if max_num_experts == 0:
            failures.append(f"packet_{packet_index}_max_num_experts_zero")

        parsed_current_experts = _parse_expert_list(
            packet,
            "current_experts",
            count=current_count,
            max_num_experts=max_num_experts,
            failures=failures,
            packet_index=packet_index,
        )
        parsed_previous_experts = _parse_expert_list(
            packet,
            "previous_experts",
            count=previous_count,
            max_num_experts=max_num_experts,
            failures=failures,
            packet_index=packet_index,
        )
        parsed_issue_experts = _parse_expert_list(
            packet,
            "issue_candidate_experts",
            count=issue_count,
            max_num_experts=max_num_experts,
            failures=failures,
            packet_index=packet_index,
        )
        if layer_id is None:
            layer_id = 0
        if current_count is None:
            current_count = len(parsed_current_experts)
        if previous_count is None:
            previous_count = len(parsed_previous_experts)
        if issue_count is None:
            issue_count = len(parsed_issue_experts)
        if transition_topk_count is not None:
            transition_topk_values.add(transition_topk_count)
        if max_num_experts is not None:
            max_num_expert_values.add(max_num_experts)
        issue_limit = (
            previous_count
            if not transition_topk_count
            else min(previous_count, transition_topk_count)
        )
        expected_issue_experts = parsed_previous_experts[:issue_limit]
        if parsed_issue_experts != expected_issue_experts:
            failures.append(f"packet_{packet_index}_issue_experts_not_previous_topk")
        max_layer_id = max(max_layer_id, layer_id)
        max_current_count = max(max_current_count, current_count)
        max_previous_count = max(max_previous_count, previous_count)
        max_issue_count = max(max_issue_count, issue_count)
        carried_previous = carried_state_by_layer.get(layer_id, [])
        state_override = 1 if carried_previous != parsed_previous_experts else 0
        state_override_count += state_override
        carried_state_by_layer[layer_id] = list(parsed_current_experts)

        layer_ids.append(layer_id)
        current_counts.append(current_count)
        previous_counts.append(previous_count)
        issue_counts.append(issue_count)
        state_override_flags.append(state_override)
        current_expert_rows.append(parsed_current_experts)
        previous_expert_rows.append(parsed_previous_experts)
        issue_expert_rows.append(parsed_issue_experts)

    if len(transition_topk_values) != 1:
        failures.append("transition_topk_count_not_unique")
        transition_topk_count = 0
    else:
        transition_topk_count = next(iter(transition_topk_values))
    if len(max_num_expert_values) != 1:
        failures.append("max_num_experts_not_unique")
        max_num_experts = 0
    else:
        max_num_experts = next(iter(max_num_expert_values))

    packet_count = len(current_expert_rows)
    layer_count = max_layer_id + 1 if packet_count else 0
    max_experts_per_packet = max(
        max_current_count,
        max_previous_count,
        max_issue_count,
        1,
    )
    if packet_count * max_experts_per_packet > MAX_EXPERT_ROWS:
        failures.append("packet_stream_expert_rows_exceed_safety_bound")
    expected_issue_hash = _expected_native_packet_issue_hash(issue_expert_rows)

    expected_issue_count = _int_field(
        manifest, "shifted_issue_total_issue_candidates", failures
    )
    expected_nonempty_previous = _int_field(
        manifest, "checked_nonempty_packet_count", failures
    )
    checked_packet_count = _int_field(manifest, "checked_packet_count", failures)
    if checked_packet_count is not None and checked_packet_count != packet_count:
        failures.append("checked_packet_count_mismatch")

    output_bin.parent.mkdir(parents=True, exist_ok=True)
    if not failures:
        with output_bin.open("wb") as handle:
            handle.write(
                struct.pack(
                    "<8I",
                    PACKET_STREAM_MAGIC,
                    PACKET_STREAM_VERSION,
                    packet_count,
                    layer_count,
                    max_experts_per_packet,
                    transition_topk_count,
                    max_num_experts,
                    0,
                )
            )
            handle.write(struct.pack(f"<{packet_count}I", *layer_ids))
            handle.write(struct.pack(f"<{packet_count}I", *current_counts))
            handle.write(struct.pack(f"<{packet_count}I", *previous_counts))
            handle.write(struct.pack(f"<{packet_count}I", *issue_counts))
            handle.write(struct.pack(f"<{packet_count}I", *state_override_flags))

            def padded_flatten(rows: list[list[int]]) -> list[int]:
                flat: list[int] = []
                for row in rows:
                    padded = row + [-1] * (max_experts_per_packet - len(row))
                    flat.extend(padded)
                return flat

            flat_current_experts = padded_flatten(current_expert_rows)
            flat_previous_experts = padded_flatten(previous_expert_rows)
            flat_issue_experts = padded_flatten(issue_expert_rows)
            handle.write(
                struct.pack(f"<{len(flat_current_experts)}i", *flat_current_experts)
            )
            handle.write(
                struct.pack(f"<{len(flat_previous_experts)}i", *flat_previous_experts)
            )
            handle.write(
                struct.pack(f"<{len(flat_issue_experts)}i", *flat_issue_experts)
            )
    return {
        "passed": not failures,
        "failures": failures,
        "manifest_json": str(manifest_path),
        "packet_stream_bin": str(output_bin),
        "packet_count": packet_count,
        "layer_count": layer_count,
        "max_experts_per_packet": max_experts_per_packet,
        "transition_topk_count": transition_topk_count,
        "max_num_experts": max_num_experts,
        "state_override_count": state_override_count,
        "expected_issue_candidate_count": expected_issue_count,
        "expected_issue_candidate_hash": expected_issue_hash,
        "expected_previous_nonempty_packet_count": expected_nonempty_previous,
        "expected_checked_packet_count": checked_packet_count,
    }


def run_canary(args: argparse.Namespace) -> dict[str, Any]:
    output: dict[str, Any] = {
        "mode": "payload_cache_producer_state_packet_stream_native_canary",
        "manifest_json": str(args.manifest_json),
        "packet_stream_bin": str(args.packet_stream_bin),
        "payload_bytes": 0,
        "ready_credit": False,
        "ready_before_demand_credit": False,
        "real_ready_credit_granted": False,
        "kernel_arg_pass": False,
        "kernel_arg_pass_allowed": False,
        "payload_transfer_enabled": False,
        "payload_deref_allowed": False,
        "passed_to_kernel": False,
        "changes_kernel_launch_args": False,
        "current_wna16_arg_compatible": False,
        "uses_current_wna16_args": False,
        "passes_current_wna16_args": False,
        "measures_tpot": False,
        "measures_vllm_latency": False,
    }
    materialized = _materialize_packet_stream(
        manifest_path=args.manifest_json,
        output_bin=args.packet_stream_bin,
    )
    output["materialized"] = materialized
    failures = list(materialized.get("failures", []))
    if not materialized.get("passed"):
        output["passed"] = False
        output["ok"] = False
        output["failures"] = failures
        return output

    native_args = argparse.Namespace(
        device=args.device,
        steps=int(materialized["packet_count"]),
        layers=int(materialized["layer_count"]),
        experts_per_layer=int(materialized["max_experts_per_packet"]),
        transition_topk_count=int(materialized["transition_topk_count"]),
        max_num_experts=int(materialized["max_num_experts"]),
        step_shift=1,
        layer_stride=17,
        state_hash_base=int(args.state_hash_base),
        disable_vectorized_copy=bool(args.disable_vectorized_copy),
        graph_replay=not bool(args.no_graph_replay),
        packet_stream_bin=args.packet_stream_bin,
        offload_arch=args.offload_arch,
        hip_visible_devices=args.hip_visible_devices,
        force_build=args.force_build,
        output_json=args.native_output_json,
    )
    native = _normalize_native_result(stream_stub.run_stub(native_args))
    args.native_output_json.parent.mkdir(parents=True, exist_ok=True)
    args.native_output_json.write_text(
        json.dumps(native, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    output["native_output_json"] = str(args.native_output_json)
    output["native"] = native

    native_failures = native.get("failures")
    native_parse_failed = (
        isinstance(native_failures, list)
        and "native_json_parse_error" in native_failures
    )
    native_stderr = str(native.get("stderr", ""))
    native_runtime_blocked = native_parse_failed and (
        "hipSetDevice" in native_stderr
        or "no ROCm-capable device" in native_stderr
        or "No HIP GPUs are available" in native_stderr
    )
    if native_runtime_blocked:
        failures.append("native_runtime_blocked")
        output["native_runtime_blocked"] = True
        output["native_runtime_blocked_reason"] = native_stderr.strip()
        output["comparisons"] = {
            "packet_count_match": None,
            "previous_nonempty_packet_count_match": None,
            "issue_candidate_count_match": None,
            "expected_issue_candidate_count_match": None,
            "state_override_count_match": None,
            "state_mismatch_count_zero": None,
            "issue_expert_mismatch_count_zero": None,
        }
        output["passed"] = False
        output["ok"] = False
        output["failures"] = failures
        return output

    if native.get("passed") is not True or native.get("ok") is not True:
        failures.append("native_not_passed")
    if not _zero_int(native.get("native_returncode")):
        failures.append("native_returncode_nonzero")
    if native.get("native_graph_replay") is not True:
        failures.append("native_graph_replay_not_true")
    if native.get("packet_stream_input") is not True:
        failures.append("native_packet_stream_input_not_true")
    if native.get("persistent_state_on_device") is not True:
        failures.append("native_persistent_state_not_true")
    if native.get("issue_generation_on_device") is not True:
        failures.append("native_issue_generation_not_true")
    for key in FALSE_SAFETY_FIELDS:
        if key not in native:
            failures.append(f"native_{key}_missing")
        elif native.get(key) is not False:
            failures.append(f"native_{key}_not_false")
    if "payload_bytes" not in native:
        failures.append("native_payload_bytes_missing")
    elif not _zero_int(native.get("payload_bytes")):
        failures.append("native_payload_bytes_nonzero")

    comparisons = {
        "packet_count_match": native.get("packet_count")
        == materialized.get("packet_count"),
        "previous_nonempty_packet_count_match": native.get(
            "previous_nonempty_packet_count"
        )
        == materialized.get("expected_previous_nonempty_packet_count"),
        "issue_candidate_count_match": native.get("issue_candidate_count")
        == materialized.get("expected_issue_candidate_count"),
        "issue_candidate_hash_match": native.get("issue_candidate_hash")
        == materialized.get("expected_issue_candidate_hash"),
        "expected_issue_candidate_count_match": native.get(
            "expected_issue_candidate_count"
        )
        == materialized.get("expected_issue_candidate_count"),
        "state_override_count_match": native.get("state_override_count")
        == materialized.get("state_override_count"),
        "state_mismatch_count_zero": _zero_int(native.get("state_mismatch_count")),
        "issue_expert_mismatch_count_zero": native.get(
            "issue_expert_mismatch_count"
        ) is not None
        and _zero_int(native.get("issue_expert_mismatch_count")),
    }
    output["comparisons"] = comparisons
    for key, passed in comparisons.items():
        if not passed:
            failures.append(key.replace("_match", "_mismatch"))

    output["passed"] = not failures
    output["ok"] = not failures
    output["failures"] = failures
    return output


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-json", type=Path, required=True)
    parser.add_argument("--packet-stream-bin", type=Path, required=True)
    parser.add_argument("--native-output-json", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--hip-visible-devices")
    parser.add_argument("--offload-arch", default="gfx1100")
    parser.add_argument("--state-hash-base", type=int, default=0x8A45D2C91FE01237)
    parser.add_argument("--disable-vectorized-copy", action="store_true")
    parser.add_argument("--no-graph-replay", action="store_true")
    parser.add_argument("--force-build", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    payload = run_canary(args)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
