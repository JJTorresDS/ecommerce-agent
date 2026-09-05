import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from ecommerce_agent.config import PROJECT_ROOT
from evals.generate_eval_data import (
    QUESTIONS_PER_RECORD,
    expand_records,
    load_ground_truth,
    parse_llm_records,
)

GROUND_TRUTH = PROJECT_ROOT / "evals" / "datasets" / "faq_ground_truth.json"


def test_load_ground_truth_reads_faq_dataset():
    records = load_ground_truth(GROUND_TRUTH)
    assert len(records) >= 1
    first = records[0]
    assert {"id", "question", "answer"} <= set(first)
    shipping = next(r for r in records if r["id"] == 17)
    assert shipping["question"] == "How long does shipping take?"
    assert "3–5 business days" in shipping["answer"]


def test_expand_records_copies_original_fields_and_adds_synthetics():
    source = [
        {
            "id": 17,
            "question": "How long does shipping take?",
            "answer": "Standard shipping takes 3–5 business days; express is 1–2 business days.",
        }
    ]
    llm_rows = [
        {
            "id": 17,
            "question": "IGNORE",
            "answer": "IGNORE",
            "synthetic_question": q,
        }
        for q in [
            "when will my package get here",
            "is express faster than regular shipping",
            "anyone know how many days delivery takes",
            "i need this soon how long is shipping",
            "typical wait for standard vs express",
        ]
    ]

    expanded = expand_records(source, llm_rows)

    assert len(expanded) == QUESTIONS_PER_RECORD
    assert {row["synthetic_question"] for row in expanded} == {
        "when will my package get here",
        "is express faster than regular shipping",
        "anyone know how many days delivery takes",
        "i need this soon how long is shipping",
        "typical wait for standard vs express",
    }
    for row in expanded:
        assert row["id"] == 17
        assert row["question"] == "How long does shipping take?"
        assert "3–5 business days" in row["answer"]


def test_expand_records_requires_five_synthetics_per_faq():
    source = [
        {
            "id": 18,
            "question": "Do you ship internationally?",
            "answer": "No, we only ship within Argentina.",
        }
    ]
    llm_rows = [
        {
            "id": 18,
            "synthetic_question": "do you ship outside the country",
        }
    ]
    with pytest.raises(ValueError, match="expected 5"):
        expand_records(source, llm_rows)


def test_parse_llm_records_accepts_fenced_json_array():
    raw = """```json
[{"id": 17, "synthetic_question": "when does it arrive"}]
```"""
    rows = parse_llm_records(raw)
    assert rows == [{"id": 17, "synthetic_question": "when does it arrive"}]


def test_generate_writes_synthetic_dataset(tmp_path, monkeypatch):
    from evals import generate_eval_data as mod

    source = load_ground_truth(GROUND_TRUTH)[:1]
    input_path = tmp_path / "faq_ground_truth.json"
    input_path.write_text(
        json.dumps({"faq_dataset": source}), encoding="utf-8"
    )
    output_path = tmp_path / "faq_eval_synthetic.json"

    fake_rows = [
        {
            "id": source[0]["id"],
            "question": source[0]["question"],
            "answer": source[0]["answer"],
            "synthetic_question": f"synthetic {i}",
        }
        for i in range(QUESTIONS_PER_RECORD)
    ]
    monkeypatch.setattr(mod, "complete_json", lambda prompt, records: fake_rows)

    written = mod.generate_eval_dataset(input_path, output_path)

    assert written == output_path
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(payload) == QUESTIONS_PER_RECORD
    assert payload[0]["id"] == source[0]["id"]
    assert payload[0]["question"] == source[0]["question"]
    assert payload[0]["answer"] == source[0]["answer"]
    assert payload[0]["synthetic_question"] == "synthetic 0"


def test_generate_wraps_records_in_tqdm(tmp_path, monkeypatch):
    from evals import generate_eval_data as mod

    source = load_ground_truth(GROUND_TRUTH)[:1]
    input_path = tmp_path / "faq_ground_truth.json"
    input_path.write_text(
        json.dumps({"faq_dataset": source}), encoding="utf-8"
    )
    output_path = tmp_path / "faq_eval_synthetic.json"
    fake_rows = [
        {
            "id": source[0]["id"],
            "question": source[0]["question"],
            "answer": source[0]["answer"],
            "synthetic_question": f"synthetic {i}",
        }
        for i in range(QUESTIONS_PER_RECORD)
    ]
    monkeypatch.setattr(mod, "complete_json", lambda prompt, records: fake_rows)

    seen = {}

    def fake_tqdm(iterable, **kwargs):
        seen["items"] = list(iterable)
        seen["kwargs"] = kwargs
        return seen["items"]

    monkeypatch.setattr(mod, "tqdm", fake_tqdm)

    mod.generate_eval_dataset(input_path, output_path)

    assert seen["items"] == source
    assert seen["kwargs"]["total"] == 1
    assert "FAQ" in seen["kwargs"]["desc"]


def test_chat_client_uses_mistral(monkeypatch):
    from evals import generate_eval_data as mod

    captured = {}

    def fake_openai(**kwargs):
        captured.update(kwargs)
        return Mock()

    monkeypatch.setattr(
        mod,
        "settings",
        SimpleNamespace(
            llm_provider="mistral",
            api_key="mistral-key",
            model="mistral-small-2603",
        ),
    )
    monkeypatch.setattr(mod, "OpenAI", fake_openai)

    _client, model = mod._chat_client()

    assert captured["api_key"] == "mistral-key"
    assert captured["base_url"] == mod.MISTRAL_BASE_URL
    assert "api.mistral.ai" in captured["base_url"]
    assert model == "mistral-small-2603"

