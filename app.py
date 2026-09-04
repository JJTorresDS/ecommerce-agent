"""Backward-compatible entry. Prefer: uv run uvicorn ecommerce_agent.api.app:app --reload"""

from ecommerce_agent.api.app import app

__all__ = ["app"]
