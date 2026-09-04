.PHONY: run_app

run_app:
	uv run uvicorn ecommerce_agent.api.app:app --reload
