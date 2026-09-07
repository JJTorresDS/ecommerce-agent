"""Generate synthetic shopper-style questions from FAQ content.

Input JSON shape (top-level value is a list of records, key name doesn't matter):
    { "<any key>": [ {"id": 1, "content": "## Question\nAnswer text"}, ... ] }

Produces two output files:

1. RETRIEVAL_OUTPUT_PATH — for hit-rate / MRR retrieval evals, keeps the
   document id so a synthetic question can be matched against the doc it
   came from:
       [ {"id": 1, "content": "...", "synthetic_question": "..."}, ... ]

2. MLFLOW_OUTPUT_PATH — for mlflow.genai.evaluate(), in the
   inputs/expectations shape MLflow expects:
       [
           {
               "inputs": {"question": "..."},
               "expectations": {"expected_response": "..."},
           },
           ...
       ]
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from openai import OpenAI

from dotenv import load_dotenv

from ecommerce_agent.config import PROJECT_ROOT

load_dotenv(override=True)

# ---- config -----------------------------------------------------------
MODEL = "gpt-4o-mini"
QUESTIONS_PER_RECORD = 2
INPUT_PATH = PROJECT_ROOT / "evals" / "datasets" / "faq_ground_truth.json"
RETRIEVAL_OUTPUT_PATH = PROJECT_ROOT / "evals" / "datasets" / "retrieval_eval_dataset.json"
MLFLOW_OUTPUT_PATH = PROJECT_ROOT / "evals" / "datasets" / "llm_eval_dataset.json"

client = OpenAI()  # reads OPENAI_API_KEY from env

SYSTEM_PROMPT = f"""
You are simulating a real online shopper who has a question. Given one FAQ
record (a "question" and its "answer"), generate {QUESTIONS_PER_RECORD}
different natural, casual ways a shopper might ask a question that this
answer already fully covers.

Rules:
- Each synthetic question must be answerable using ONLY the given answer —
  don't invent details, numbers, or conditions it doesn't support.
- Mix the phrasing: most questions should avoid reusing the exact key words
  from the original question/answer (paraphrase instead), and 1-2 can
  naturally reuse an obvious keyword the way a real shopper would type it.
- Vary tone/structure across the {QUESTIONS_PER_RECORD}: direct question,
  casual/quick, slightly worried, "does anyone know if...", specific
  scenario, etc. No generic openers like "Hi, I wanted to ask...".

Return ONLY a JSON array of {QUESTIONS_PER_RECORD} strings, e.g.:
["question 1", "question 2", "question 3", "question 4", "question 5"]
No other text, no markdown fences.
"""


def split_content(content: str) -> tuple[str, str]:
    """Split '## Question\\nAnswer' into (question, answer)."""
    question, _, answer = content.partition("\n")
    return question.lstrip("#").strip(), answer.strip()


def parse_json_array(raw: str) -> list[str]:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of strings")
    return [str(q).strip() for q in data if str(q).strip()]


def generate_for_record(record: dict) -> list[str]:
    question, answer = split_content(record["content"])
    user_payload = json.dumps({"question": question, "answer": answer}, ensure_ascii=False)

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.8,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_payload},
        ],
    )
    raw = response.choices[0].message.content or ""
    questions = parse_json_array(raw)

    if len(questions) != QUESTIONS_PER_RECORD:
        raise ValueError(
            f"id {record['id']}: expected {QUESTIONS_PER_RECORD} questions, got {len(questions)}"
        )
    return questions


def load_records(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    # payload is {"<some key>": [records...]} — grab the first (only) list value
    records = next(v for v in payload.values() if isinstance(v, list))
    return records


def main(
    input_path: Path = INPUT_PATH,
    retrieval_output_path: Path = RETRIEVAL_OUTPUT_PATH,
    mlflow_output_path: Path = MLFLOW_OUTPUT_PATH,
) -> None:
    records = load_records(input_path)
    retrieval_dataset = []
    mlflow_dataset = []

    for record in records:
        _, answer = split_content(record["content"])
        synthetic_questions = generate_for_record(record)

        for sq in synthetic_questions:
            retrieval_dataset.append(
                {
                    "id": record["id"],
                    "content": record["content"],
                    "synthetic_question": sq,
                }
            )
            mlflow_dataset.append(
                {
                    "inputs": {"question": sq},
                    "expectations": {"expected_response": answer},
                }
            )
        print(f"id {record['id']}: generated {len(synthetic_questions)} questions")

    retrieval_output_path.write_text(
        json.dumps(retrieval_dataset, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    mlflow_output_path.write_text(
        json.dumps(mlflow_dataset, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nWrote {len(retrieval_dataset)} rows to {retrieval_output_path}")
    print(f"Wrote {len(mlflow_dataset)} rows to {mlflow_output_path}")


if __name__ == "__main__":
    main()