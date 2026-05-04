from mtp_expert_prefetch.data.material import render_text


def test_render_text_template() -> None:
    text = render_text(
        {"inputs": "Question?", "targets": "Answer."},
        {"text_template": "User:\n{inputs}\n\nAssistant:\n{targets}"},
    )

    assert text == "User:\nQuestion?\n\nAssistant:\nAnswer."


def test_render_text_fields() -> None:
    text = render_text(
        {"inputs": "Question?", "targets": "Answer."},
        {"text_fields": ["inputs", "targets"]},
    )

    assert text == "Question?\n\nAnswer."
