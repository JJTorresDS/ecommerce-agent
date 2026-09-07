"""Prometheus metrics for production Grafana dashboards."""

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

ASK_LATENCY = Histogram(
    "ask_latency_seconds",
    "Latency of POST /ask in seconds.",
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
)
ASK_QUESTION_WORDS = Histogram(
    "ask_question_words",
    "Word count of the user question on POST /ask.",
    buckets=(1, 5, 10, 20, 50, 100, 200, 500),
)
ASK_ANSWER_WORDS = Histogram(
    "ask_answer_words",
    "Word count of the agent answer on POST /ask.",
    buckets=(1, 5, 10, 20, 50, 100, 200, 500),
)
ASK_TURNS = Counter("ask_turns_total", "Completed POST /ask turns.")
FEEDBACK = Counter(
    "feedback_total",
    "User thumbs-up / thumbs-down feedback.",
    ["rating"],
)

# Register zero-valued feedback series so /metrics always lists the name.
FEEDBACK.labels(rating="up")
FEEDBACK.labels(rating="down")


def word_count(text: str) -> int:
    return len(text.split())


def observe_ask(
    *,
    latency_seconds: float,
    question_words: int,
    answer_words: int,
) -> None:
    ASK_LATENCY.observe(latency_seconds)
    ASK_QUESTION_WORDS.observe(question_words)
    ASK_ANSWER_WORDS.observe(answer_words)
    ASK_TURNS.inc()


def observe_feedback(rating: str) -> None:
    FEEDBACK.labels(rating=rating).inc()


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
