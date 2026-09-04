from ecommerce_agent.tools.catalog import get_item_details, search_products
from ecommerce_agent.tools.knowledge import (
    list_knowledgebase_documents,
    search_faq_knowledgebase,
)

AGENT_TOOLS = [
    list_knowledgebase_documents,
    search_faq_knowledgebase,
    search_products,
    get_item_details,
]
