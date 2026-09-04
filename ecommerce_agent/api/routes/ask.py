from fastapi import APIRouter
from agents import Runner

from ecommerce_agent.agent.factory import agent
from ecommerce_agent.api.schemas import Answer, Question

router = APIRouter()


@router.post("/ask", response_model=Answer)
async def ask(payload: Question) -> Answer:
    print(f"[agent] called with question: {payload.question!r}", flush=True)
    result = await Runner.run(agent, payload.question)
    print(f"[agent] finished, answer: {result.final_output!r}", flush=True)
    return Answer(answer=result.final_output)
