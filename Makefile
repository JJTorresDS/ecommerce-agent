.PHONY: run_app llm_api_tests evaluate_llms

run_app:
	uv run uvicorn ecommerce_agent.api.app:app --reload

llm_api_tests:
	uv run pytest llm-api-tests -v

evaluate_llms:
	uv run python evals/evaluate_llm_provider_latency.py
