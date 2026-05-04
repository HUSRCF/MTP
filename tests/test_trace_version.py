import pytest

from mtp_expert_prefetch.tracing.router_mtp import _check_transformers_model_type


def test_check_transformers_model_type_reraises_unrelated_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeAutoConfig:
        @staticmethod
        def from_pretrained(*_args: object, **_kwargs: object) -> None:
            raise ValueError("different problem")

    import transformers

    monkeypatch.setattr(transformers, "AutoConfig", FakeAutoConfig)

    with pytest.raises(ValueError, match="different problem"):
        _check_transformers_model_type("fake/model", True)


def test_check_transformers_model_type_rewrites_qwen35_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeAutoConfig:
        @staticmethod
        def from_pretrained(*_args: object, **_kwargs: object) -> None:
            raise ValueError("unknown model type qwen3_5_moe")

    import transformers

    monkeypatch.setattr(transformers, "AutoConfig", FakeAutoConfig)

    with pytest.raises(RuntimeError, match="qwen3_5_moe"):
        _check_transformers_model_type("fake/model", True)
