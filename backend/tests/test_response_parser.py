"""Tests for LLM response parsing: visualizations, raw_data, citations."""

from src.llm.response_parser import parse_response, extract_raw_data


def test_extract_raw_data_labeled_object():
    text = """
Here is the plan.

[DATA_START]
{"label": "Shopping List", "type": "table", "value": [{"item": "eggs", "qty": 12}, {"item": "milk", "qty": 1}]}
[DATA_END]
"""
    rows = extract_raw_data(text)
    assert rows is not None
    assert len(rows) == 1
    assert rows[0]["label"] == "Shopping List"
    assert rows[0]["type"] == "table"
    assert rows[0]["value"][0]["item"] == "eggs"


def test_extract_raw_data_plain_array():
    text = """
[DATA_START]
[{"step": 1, "action": "Preheat"}, {"step": 2, "action": "Mix"}]
[DATA_END]
"""
    rows = extract_raw_data(text)
    assert rows is not None
    assert rows[0]["label"] == "Data"
    assert rows[0]["type"] == "table"
    assert len(rows[0]["value"]) == 2


def test_parse_response_includes_raw_data_and_strips_markers():
    text = """
Dinner is ready.

[DATA_START]
{"label": "Menu", "value": [{"dish": "Pasta"}, {"dish": "Salad"}]}
[DATA_END]

## References
[1] Chef Notes. (2024). "Pasta basics". https://example.com/pasta
"""
    cleaned, _, _, citations, _, visualizations, raw_data = parse_response(text)
    assert "[DATA_START]" not in cleaned
    assert raw_data is not None
    assert raw_data[0]["label"] == "Menu"
    assert citations and citations[0]["number"] == 1
    assert visualizations is None


def test_parse_response_raw_data_only_builds_tuple():
    text = '[DATA_START]\n{"label": "Metrics", "value": {"a": 1}}\n[DATA_END]'
    result = parse_response(text)
    assert len(result) == 7
    assert result[6][0]["type"] == "object"
