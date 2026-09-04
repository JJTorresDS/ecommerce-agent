"""Expand FAQ ground truth into shopper-style synthetic questions."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from openai import OpenAI
from tqdm import tqdm

from ecommerce_agent.config import PROJECT_ROOT, settings

QUESTIONS_PER_RECORD = 5
DEFAULT_INPUT = PROJECT_ROOT / "evals" / "datasets" / "faq_ground_truth.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "evals" / "datasets" / "faq_eval_synthetic.json"

SYSTEM_PROMPT = """\
You are simulating a real online shopper who has a question. For each FAQ record
provided, generate 5 different ways a shopper might naturally ask the question that
record already answers.

For each of the 5 questions, output one record containing:
- "id": copied from the original record
- "question": copied from the original record
- "answer": copied from the original record
- "synthetic_question": your generated question

So each input record should produce 5 output records — identical except for
"synthetic_question".

Guidelines for writing the synthetic questions:
- Each one must be answerable using only the record's "answer" field — don't
  introduce details, numbers, or conditions that aren't supported by it.
- Reuse as few exact words/phrases from the original "question" and "answer" as
  possible. Paraphrase, don't rearrange.
- Make each of the 5 phrasings meaningfully different from the others — vary the
  angle, wording, and sentence structure (e.g., a direct question, a "does anyone
  know if..." style, a quick/casual version, a slightly worried or urgent version,
  a more specific/contextual version).
- Write like a real person typing into a search bar, chat widget, or forum —
  casual and natural, not formal or robotic, but also not so short that it loses
  meaning (avoid one-or-two-word fragments; avoid long, over-explained paragraphs).
- Don't use overly generic openers like "Hi, I wanted to ask..." — get straight to
  the question, the way people actually type.
- No made-up personal details (names, order numbers, dates) unless the original
  answer implies the shopper would need to mention one.

Return the output as a JSON array of these expanded records
"""


def load_ground_truth(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("faq_dataset")
    if not isinstance(records, list) or not records:
        raise ValueError(f"{path} has no faq_dataset records")
    return records


def parse_llm_records(raw: str) -> list[dict]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                return value
    raise ValueError("LLM output is not a JSON array of records")


def _norm_id(value: object) -> object:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return value


def expand_records(source: list[dict], llm_rows: list[dict]) -> list[dict]:
    by_id: dict[object, list[str]] = defaultdict(list)
    for row in llm_rows:
        question = (row.get("synthetic_question") or "").strip()
        if not question:
            continue
        by_id[_norm_id(row["id"])].append(question)

    expanded = []
    for record in source:
        record_id = _norm_id(record["id"])
        synthetics = by_id.get(record_id, [])
        if len(synthetics) != QUESTIONS_PER_RECORD:
            raise ValueError(
                f"id {record['id']}: expected {QUESTIONS_PER_RECORD} "
                f"synthetic questions, got {len(synthetics)}"
            )
        for synthetic in synthetics:
            expanded.append(
                {
                    "id": record["id"],
                    "question": record["question"],
                    "answer": record["answer"],
                    "synthetic_question": synthetic,
                }
            )
    return expanded


def _chat_client() -> tuple[OpenAI, str]:
    if settings.local_model:
        return (
            OpenAI(base_url=settings.ollama_base_url, api_key="ollama"),
            settings.ollama_model,
        )
    if not settings.open_router_api_key:
        raise RuntimeError("OPEN_ROUTER_API_KEY is required when LOCAL_MODEL is false")
    return (
        OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.open_router_api_key,
        ),
        settings.openrouter_model,
    )


def complete_json(prompt: str, records: list[dict]) -> list[dict]:
    client, model = _chat_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": json.dumps(records, ensure_ascii=False),
            },
        ],
        temperature=0.8,
    )
    content = response.choices[0].message.content or ""
    return parse_llm_records(content)


def generate_eval_dataset(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
) -> Path:
    source = load_ground_truth(input_path)
    llm_rows: list[dict] = []
    for record in tqdm(source, total=len(source), desc="FAQ records"):
        llm_rows.extend(complete_json(SYSTEM_PROMPT, [record]))
    expanded = expand_records(source, llm_rows)
    output_path.write_text(
        json.dumps(expanded, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic FAQ eval questions from ground truth."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    path = generate_eval_dataset(args.input, args.output)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
