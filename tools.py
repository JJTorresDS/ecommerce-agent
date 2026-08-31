from agents import function_tool
from vector_store import search_products as _search_products
# --- Define your tools ------------------------------------------------------
# Decorate plain Python functions with @function_tool. Use type hints and a
# clear docstring — the model relies on both to decide when/how to call it.

@function_tool
def get_item_details(item_id: str) -> dict:
    """Get the current weather for a given city.

    Args:
        city: Name of the city to look up.
    """
    # Replace with a real API call as needed.
    return {
        "status": "success",
        "city": item_id,
        "temperature_c": 22,
        "condition": "Sunny",
    }


@function_tool
def search_faq_knowledgebase(query: str) -> dict:
    """Search the FAQ knowledgebase for a given query.

    Args:
        query: The query to search for.
    """
    return {"status": "success", "result": query}

@function_tool
def search_products(query: str, top_k: int = 5) -> list[dict]:
    """Search the product catalog for items semantically similar to `query`."""
    return _search_products(query, top_k=top_k)
 