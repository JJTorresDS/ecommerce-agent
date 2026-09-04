# ecommerce-agent

uv run uvicorn app:app --reload

ollama stop qwen2.5:7b

para inizliazar la base:

docker exec -i postgres-pgvector psql -U postgres -d pyrolabs-local < init.sql

alternative
uv run python -c "from init.seed_products import main; main()"

## Running the app

If you are using a docker to host your postres db, make sure it is running since the get_item_details tool will return an item from a database.

## Pending

[ ]- Add traces
[ ]- Run a daily cron to check if the "updated_at" date of the Google docs in the db are older then the last_modifed from the google dog. If its older, re-embed the document.