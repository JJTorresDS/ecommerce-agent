from fastapi import APIRouter

from ecommerce_agent.api.schemas import FeedbackIn, FeedbackOut
from ecommerce_agent.monitoring import record_feedback

router = APIRouter()


@router.post("/feedback", response_model=FeedbackOut)
def feedback(payload: FeedbackIn) -> FeedbackOut:
    record_feedback(
        session_id=payload.session_id,
        rating=payload.rating,
        turn_id=payload.turn_id,
    )
    return FeedbackOut(ok=True)
