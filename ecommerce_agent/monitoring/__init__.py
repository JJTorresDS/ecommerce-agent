"""Production monitoring: Prometheus metrics + Postgres persistence."""

from ecommerce_agent.monitoring.metrics import (
    observe_ask,
    observe_feedback,
    word_count,
)
from ecommerce_agent.monitoring.store import persist_ask_turn, persist_feedback


def record_ask_turn(
    *,
    session_id: str | None,
    question: str,
    answer: str,
    question_words: int,
    answer_words: int,
    latency_ms: float,
) -> str:
    turn_id = persist_ask_turn(
        session_id=session_id,
        question=question,
        answer=answer,
        question_words=question_words,
        answer_words=answer_words,
        latency_ms=latency_ms,
    )
    observe_ask(
        latency_seconds=latency_ms / 1000.0,
        question_words=question_words,
        answer_words=answer_words,
    )
    return turn_id


def record_feedback(
    *,
    session_id: str,
    rating: int,
    turn_id: str | None = None,
) -> None:
    persist_feedback(session_id=session_id, rating=rating, turn_id=turn_id)
    observe_feedback(rating)
