from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

import pytest
from mtp_expert_prefetch.tracing import router_mtp
from mtp_expert_prefetch.tracing.vllm_router_trace import (
    _patch_vllm_warning_once_scope_import_for_trace,
)


@pytest.mark.parametrize("backend", ["vllm", "VLLM", " vllm "])
def test_trace_router_mtp_dispatches_vllm_backend(
    monkeypatch, tmp_path: Path, backend: str
) -> None:
    config_path = tmp_path / "trace.yaml"
    model_path = tmp_path / "model.yaml"
    sentinel_manifest = tmp_path / "vllm_manifest.json"
    calls: list[Path] = []

    def fake_load_yaml(path: Path) -> dict:
        if path == config_path:
            return {"model": "model.yaml", "output_dir": "unused"}
        if path == model_path:
            return {"backend": backend}
        raise AssertionError(f"unexpected YAML path: {path}")

    def fake_resolve_path(value: str, *, base_dir: Path) -> Path:
        assert base_dir == tmp_path
        assert value == "model.yaml"
        return model_path

    def fake_trace_router_mtp_vllm(path: str | Path) -> Path:
        calls.append(Path(path))
        return sentinel_manifest

    monkeypatch.setattr(router_mtp, "find_project_root", lambda _path: tmp_path)
    monkeypatch.setattr(router_mtp, "load_yaml", fake_load_yaml)
    monkeypatch.setattr(router_mtp, "resolve_path", fake_resolve_path)
    fake_vllm_trace = ModuleType("mtp_expert_prefetch.tracing.vllm_router_trace")
    fake_vllm_trace.trace_router_mtp_vllm = fake_trace_router_mtp_vllm
    monkeypatch.setitem(
        sys.modules,
        "mtp_expert_prefetch.tracing.vllm_router_trace",
        fake_vllm_trace,
    )

    manifest_path = router_mtp.trace_router_mtp(config_path)

    assert manifest_path == sentinel_manifest
    assert calls == [config_path]


def test_trace_router_mtp_does_not_dispatch_non_vllm_backend(
    monkeypatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "trace.yaml"
    model_path = tmp_path / "model.yaml"
    output_dir = tmp_path / "out"

    def fake_load_yaml(path: Path) -> dict:
        if path == config_path:
            return {"model": "model.yaml", "output_dir": "out", "trace": {}}
        if path == model_path:
            return {"backend": "transformers"}
        raise AssertionError(f"unexpected YAML path: {path}")

    def fake_resolve_path(value: str, *, base_dir: Path) -> Path:
        assert base_dir == tmp_path
        if value == "model.yaml":
            return model_path
        if value == "out":
            return output_dir
        raise AssertionError(f"unexpected resolve path value: {value}")

    def fail_if_called(_path: str | Path) -> Path:
        raise AssertionError("non-vLLM backend should not dispatch to vLLM trace")

    monkeypatch.setattr(router_mtp, "find_project_root", lambda _path: tmp_path)
    monkeypatch.setattr(router_mtp, "load_yaml", fake_load_yaml)
    monkeypatch.setattr(router_mtp, "resolve_path", fake_resolve_path)
    monkeypatch.setattr(router_mtp, "_load_trace_texts", lambda _config, _root: [])
    monkeypatch.setattr(router_mtp, "_disable_optional_cuda_kernels_on_rocm", lambda: None)
    fake_vllm_trace = ModuleType("mtp_expert_prefetch.tracing.vllm_router_trace")
    fake_vllm_trace.trace_router_mtp_vllm = fail_if_called
    monkeypatch.setitem(
        sys.modules,
        "mtp_expert_prefetch.tracing.vllm_router_trace",
        fake_vllm_trace,
    )

    with pytest.raises(RuntimeError, match="produced no text records"):
        router_mtp.trace_router_mtp(config_path)


def test_patch_vllm_warning_once_scope_import_is_local_and_idempotent(
    monkeypatch,
) -> None:
    fake_vllm = ModuleType("vllm")
    fake_logger = ModuleType("vllm.logger")

    def original_should_log(scope: str) -> bool:
        raise AssertionError(f"scope check should not import distributed: {scope}")

    fake_logger._should_log_with_scope = original_should_log
    monkeypatch.setitem(sys.modules, "vllm", fake_vllm)
    monkeypatch.setitem(sys.modules, "vllm.logger", fake_logger)

    assert _patch_vllm_warning_once_scope_import_for_trace() is True
    assert fake_logger._mtp_warning_once_scope_import_patched is True
    assert fake_logger._mtp_original_should_log_with_scope is original_should_log
    assert fake_logger._should_log_with_scope("local") is True

    assert _patch_vllm_warning_once_scope_import_for_trace() is True
    assert fake_logger._mtp_original_should_log_with_scope is original_should_log
