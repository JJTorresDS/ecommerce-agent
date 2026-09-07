from fastapi import APIRouter
from prometheus_client import CONTENT_TYPE_LATEST

from ecommerce_agent.monitoring.metrics import render_metrics

router = APIRouter()


@router.get("/metrics")
def metrics():
    from fastapi.responses import Response

    payload, media_type = render_metrics()
    return Response(content=payload, media_type=media_type or CONTENT_TYPE_LATEST)
