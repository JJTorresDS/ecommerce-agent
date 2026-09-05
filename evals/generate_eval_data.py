"""Expand FAQ ground truth into shopper-style synthetic questions."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from openai import OpenAI
from tqdm import tqdm

from ecommerce_agent.config import (
    MISTRAL_BASE_URL,
    OLLAMA_BASE_URL,
    OPENAI_BASE_URL,
    OPENROUTER_BASE_URL,
    PROJECT_ROOT,
    settings,
)

QUESTIONS_PER_RECORD = 5
DEFAULT_INPUT = PROJECT_ROOT / "evals" / "datasets" / "faq_ground_truth.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "evals" / "datasets" / "faq_eval_synthetic.json"

SYSTEM_PROMPT = """
You are simulating a real online shopper who has a question. For each FAQ record
provided, generate 5 different ways a shopper might naturally ask the question that
record already answers.

This data will be used to test whether a semantic embedding model can retrieve the
right FAQ from phrasing alone, and to help decide if keyword/hybrid search is needed
on top of it. So the batch of 5 questions per record should be a MIX:

- 3 to 4 of the 5 should be lexically distant from the original "question" and
  "answer" — conceptually faithful paraphrases that avoid reusing key content words.
- The remaining 1 to 2 can naturally reuse some of the original keywords/phrases,
  the way a real shopper often would (e.g. repeating the product name, the exact
  term "shipping," "return," "warranty," etc.). These should still read like a
  distinct, naturally-phrased question, not just the original title copy-pasted or
  trivially reordered.

For each record, work in three steps:

STEP 1 — Extract the "core lexicon"
List the key content words/phrases from the original "question" and "answer":
nouns, verbs, product/domain terms, and any distinctive multi-word phrases. Ignore
stopwords (a, the, is, do, my, order, etc.). This is the list you'll deliberately
avoid in most questions, and deliberately allow back in for 1-2 of them.

Example:
question: "How long does standard shipping take?"
answer: "Standard shipping takes 5-7 business days after the order is processed."
core lexicon: ["shipping", "standard", "long", "take/takes", "5-7", "business days",
"processed"]

STEP 2 — Generate 5 synthetic questions
Each one must be answerable using only the record's "answer" field — don't introduce
details, numbers, or conditions it doesn't support.

For the 3-4 "lexically distant" questions:
- Replace core-lexicon terms with a synonym, a more general/specific description,
  or a different framing (e.g. "shipping" -> "getting my stuff to me", "5-7 business
  days" -> "a work-week or so", "processed" -> "you've got it going").
- Only reuse a core term if there's truly no other way to say it (brand name,
  required legal term, SKU) — this should be rare within these questions.

For the 1-2 "keyword-overlap" questions:
- Feel free to reuse the product/domain term(s) or other core lexicon naturally,
  the way a shopper typing quickly actually would.
- Still rephrase the surrounding sentence structure so it isn't just the original
  question restated or lightly reordered — it should be a genuinely different way
  of asking, just not one that avoids the obvious keyword.

Across all 5, vary the angle and structure: e.g. a direct question, a "does anyone
know if..." style, a quick/casual version, a slightly worried or urgent version, a
specific/contextual scenario version. Write like a real person typing into a search
bar, chat widget, or forum — casual and natural, not formal or robotic, and not so
short it loses meaning. Don't use generic openers like "Hi, I wanted to ask...".
No made-up personal details (names, order numbers, dates) unless the answer implies
the shopper would need to mention one.

STEP 3 — Self-check
Confirm the mix is roughly 3-4 lexically distant / 1-2 keyword-overlap, and that
even the keyword-overlap questions are phrased distinctly from the original and
from each other. Do this silently — don't show your work in the output.

OUTPUT FORMAT
Return a JSON array. For each of the 5 synthetic questions per record, output one
object:
- "id": copied from the original record
- "question": copied from the original record
- "answer": copied from the original record
- "synthetic_question": your generated question
- "lexical_type": either "distant" or "overlap", indicating which bucket this
  question falls into

Output only the JSON array, no other text.
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
    provider = settings.llm_provider
    if provider == "openai":
        if not settings.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required when LLM_PROVIDER is openai in config.py"
            )
        return OpenAI(api_key=settings.api_key, base_url=OPENAI_BASE_URL), settings.model
    if provider == "ollama":
        return (
            OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama"),
            settings.model,
        )
    if provider == "mistral":
        if not settings.api_key:
            raise RuntimeError(
                "MISTRAL_API_KEY is required when LLM_PROVIDER is mistral in config.py"
            )
        return (
            OpenAI(api_key=settings.api_key, base_url=MISTRAL_BASE_URL),
            settings.model,
        )
    if not settings.api_key:
        raise RuntimeError(
            "OPEN_ROUTER_API_KEY is required when LLM_PROVIDER is openrouter in config.py"
        )
    return (
        OpenAI(base_url=OPENROUTER_BASE_URL, api_key=settings.api_key),
        settings.model,
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
