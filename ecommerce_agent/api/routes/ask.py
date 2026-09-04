from fastapi import APIRouter
from agents import Runner
from langfuse import propagate_attributes

from ecommerce_agent.agent.factory import agent
from ecommerce_agent.agent.tracing import get_client
from ecommerce_agent.api.schemas import Answer, Question
from ecommerce_agent.config import settings

router = APIRouter()


@router.post("/ask", response_model=Answer)
async def ask(payload: Question) -> Answer:
    print(f"[agent] called with question: {payload.question!r}", flush=True)
    result = await _run_agent(payload)
    print(f"[agent] finished, answer: {result.final_output!r}", flush=True)
    return Answer(answer=result.final_output)


async def _run_agent(payload: Question):
    if not settings.langfuse_enabled:
        return await Runner.run(agent, payload.question)

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
            result = await Runner.run(agent, payload.question)
            observation.update(output=result.final_output)
            return result
