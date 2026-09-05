.PHONY: run_app llm_api_tests

run_app:
	uv run uvicorn ecommerce_agent.api.app:app --reload

llm_api_tests:
	uv run pytest llm-api-tests -v
