from ai_layer.llm_utils import extract_json_from_text


def test_extract_plain_json_object() -> None:
    parsed, error = extract_json_from_text('{"summary": "hello"}')
    assert error is None
    assert parsed == {"summary": "hello"}


def test_extract_fenced_json() -> None:
    content = """Here you go:
```json
{"key_points": ["one point that is long enough"]}
```
"""
    parsed, error = extract_json_from_text(content)
    assert error is None
    assert parsed is not None
    assert "key_points" in parsed


def test_extract_embedded_json() -> None:
    content = 'Sure. {"answer": "ok"} Thanks.'
    parsed, error = extract_json_from_text(content)
    assert error is None
    assert parsed == {"answer": "ok"}


def test_extract_rejects_non_object() -> None:
    parsed, error = extract_json_from_text("[1, 2, 3]")
    assert parsed is None
    assert error


def test_extract_invalid() -> None:
    parsed, error = extract_json_from_text("not json at all")
    assert parsed is None
    assert error
