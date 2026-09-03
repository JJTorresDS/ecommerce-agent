from agents import function_tool
from vector_store import get_product_by_sku as _get_product_by_sku
from vector_store import search_products as _search_products
# --- Define your tools ------------------------------------------------------
# Decorate plain Python functions with @function_tool. Use type hints and a
# clear docstring — the model relies on both to decide when/how to call it.

@function_tool
def get_item_details(sku: str) -> dict:
    """Look up a product in the catalog by its SKU.

    Args:
        sku: Product SKU, e.g. G-001 or B-004.
    """
    product = _get_product_by_sku(sku)
    if product is None:
        return {"status": "not_found", "sku": sku}
    return {"status": "success", **product}


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
 