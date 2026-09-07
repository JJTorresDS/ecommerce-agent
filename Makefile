.PHONY: run_app llm_api_tests evaluate_llms evaluate_retrieval

run_app:
	uv run uvicorn ecommerce_agent.api.app:app --reload

llm_api_tests:
	uv run pytest llm-api-tests -v

evaluate_llms:
	@test -n "$(PROVIDER)" || (echo "PROVIDER is required, e.g. make evaluate_llms PROVIDER=mistral EXPERIMENT=ecommerce-agent-llm_eval" && exit 1)
	@test -n "$(EXPERIMENT)" || (echo "EXPERIMENT is required, e.g. make evaluate_llms PROVIDER=mistral EXPERIMENT=ecommerce-agent-llm_eval" && exit 1)
	uv run python evals/evaluate_llm_response.py --provider $(PROVIDER) --experiment $(EXPERIMENT) $(if $(N),--n $(N),)

evaluate_retrieval:
	@test -n "$(SEARCH_TYPE)" || (echo "SEARCH_TYPE is required, e.g. make evaluate_retrieval SEARCH_TYPE=genai_001_embedding" && exit 1)
	uv run python evals/evaluate_knowledge_search.py --search-type $(SEARCH_TYPE)
