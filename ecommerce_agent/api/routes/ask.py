from time import perf_counter

from fastapi import APIRouter
from agents import Runner
from langfuse import propagate_attributes

from ecommerce_agent.agent.factory import agent
from ecommerce_agent.agent.memory import PostgresSession
from ecommerce_agent.agent.tracing import get_client
from ecommerce_agent.api.schemas import Answer, Question
from ecommerce_agent.config import settings
from ecommerce_agent.monitoring import record_ask_turn
from ecommerce_agent.monitoring.metrics import word_count

router = APIRouter()


@router.post("/ask", response_model=Answer)
async def ask(payload: Question) -> Answer:
    print(f"[agent] called with question: {payload.question!r}", flush=True)
    started = perf_counter()
    result = await _run_agent(payload)
    latency_ms = (perf_counter() - started) * 1000
    answer_text = result.final_output or ""
    turn_id = record_ask_turn(
        session_id=payload.session_id,
        question=payload.question,
        answer=answer_text,
        question_words=word_count(payload.question),
        answer_words=word_count(answer_text),
        latency_ms=latency_ms,
    )
    print(f"[agent] finished, answer: {answer_text!r}", flush=True)
    return Answer(answer=answer_text, turn_id=turn_id)


def _runner_kwargs(payload: Question) -> dict:
    if not payload.session_id:
        return {}
    return {"session": PostgresSession(payload.session_id)}


async def _run_agent(payload: Question):
    run_kwargs = _runner_kwargs(payload)
    if not settings.langfuse_enabled:
        return await Runner.run(agent, payload.question, **run_kwargs)

    langfuse = get_client()
    attribute_kwargs: dict = {
        "tags": ["ask", "chat"],
        "metadata": {
            "llm_provider": settings.llm_provider,
            "model": settings.model,
        },
    }
    if payload.session_id:
        attribute_kwargs["session_id"] = payload.session_id
    with langfuse.start_as_current_observation(
        as_type="span",
        name="ask",
        input=payload.question,
    ) as observation:
        with propagate_attributes(**attribute_kwargs):
            result = await Runner.run(agent, payload.question, **run_kwargs)
            observation.update(output=result.final_output)
            return result
