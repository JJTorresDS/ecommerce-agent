# ecommerce-agent

uv run uvicorn app:app --reload

ollama stop qwen2.5:7b

para inizliazar la base:

docker exec -i postgres-pgvector psql -U postgres -d pyrolabs-local < init.sql