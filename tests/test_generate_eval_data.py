import json

from ecommerce_agent.config import PROJECT_ROOT
from evals.generate_eval_data import (
    QUESTIONS_PER_RECORD,
    load_records,
    parse_json_array,
    split_content,
)

GROUND_TRUTH = PROJECT_ROOT / "evals" / "datasets" / "faq_ground_truth.json"


def test_load_records_reads_faq_chunks():
    records = load_records(GROUND_TRUTH)
    assert len(records) >= 1
    first = records[0]
    assert {"id", "content"} <= set(first)
    shipping = next(r for r in records if r["id"] == 1)
    assert "How long does shipping take?" in shipping["content"]
    assert "3–5 business days" in shipping["content"]


def test_split_content_separates_heading_and_answer():
    question, answer = split_content(
        "## How long does shipping take?\nStandard shipping takes 3–5 business days."
    )
    assert question == "How long does shipping take?"
    assert "3–5 business days" in answer


def test_parse_json_array_accepts_fenced_json():
    raw = """```json
["when does it arrive", "how many days"]
```"""
    assert parse_json_array(raw) == ["when does it arrive", "how many days"]


def test_main_writes_retrieval_and_mlflow_datasets(tmp_path, monkeypatch):
    from evals import generate_eval_data as mod

    source = load_records(GROUND_TRUTH)[:1]
    input_path = tmp_path / "faq_ground_truth.json"
    input_path.write_text(
        json.dumps({"faq_dataset": source}), encoding="utf-8"
    )
    retrieval_path = tmp_path / "retrieval.json"
    mlflow_path = tmp_path / "mlflow.json"
    synthetics = [f"synthetic {i}" for i in range(QUESTIONS_PER_RECORD)]
    monkeypatch.setattr(mod, "generate_for_record", lambda record: synthetics)

    mod.main(input_path, retrieval_path, mlflow_path)

    retrieval = json.loads(retrieval_path.read_text(encoding="utf-8"))
    mlflow_rows = json.loads(mlflow_path.read_text(encoding="utf-8"))
    assert len(retrieval) == QUESTIONS_PER_RECORD
    assert retrieval[0]["id"] == source[0]["id"]
    assert retrieval[0]["content"] == source[0]["content"]
    assert retrieval[0]["synthetic_question"] == "synthetic 0"
    assert mlflow_rows[0]["inputs"]["question"] == "synthetic 0"
    assert "expected_response" in mlflow_rows[0]["expectations"]
