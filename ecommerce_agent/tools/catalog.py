from agents import function_tool

from ecommerce_agent.retrieval.products import get_product_by_sku as _get_product_by_sku
from ecommerce_agent.retrieval.products import search_products as _search_products


@function_tool
def get_item_details(sku: str) -> dict:
    """Look up a product in the catalog by its SKU.

    Args:
        sku: Product SKU, e.g. G-001 or B-004.
    """
    print(f"[tool] get_item_details sku={sku!r}", flush=True)
    product = _get_product_by_sku(sku)
    if product is None:
        print("[tool] get_item_details -> not_found", flush=True)
        return {"status": "not_found", "sku": sku}
    print("[tool] get_item_details -> success", flush=True)
    return {"status": "success", **product}


@function_tool
def search_products(query: str, top_k: int = 5) -> list[dict]:
    """Search the product catalog for items semantically similar to `query`."""
    print(f"[tool] search_products query={query!r} top_k={top_k}", flush=True)
    results = _search_products(query, top_k=top_k)
    print(f"[tool] search_products -> {len(results)} result(s)", flush=True)
    return results
