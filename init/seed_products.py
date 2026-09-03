"""
Seed the database with dummy products for testing the ecommerce agent.

Catalog matches static/ecommerce.html (Mimo & Co mock storefront).

Usage:
    uv run python init/seed_products.py
"""

from embeddings.ingest import init_db, upsert_products_batch

DUMMY_PRODUCTS = [
    {
        "name": "KID LOVE VEST",
        "sku": "G-001",
        "price": "$34.950",
        "description": "KID LOVE VEST — Discount, Winter, Girls, 50% off.",
    },
    {
        "name": "JR HARBIN VEST",
        "sku": "G-002",
        "price": "$36.950",
        "description": "JR HARBIN VEST — Discount, Winter, Girls, 50% off.",
    },
    {
        "name": "SYDNEY VEST",
        "sku": "G-003",
        "price": "$37.950",
        "description": "SYDNEY VEST — Discount, Winter, Girls, 50% off.",
    },
    {
        "name": "JR SIBERIA VEST",
        "sku": "G-004",
        "price": "$24.950",
        "description": "JR SIBERIA VEST — Discount, Winter, Girls, 50% off.",
    },
    {
        "name": "ATHENS JACKET",
        "sku": "B-001",
        "price": "$34.930",
        "description": "ATHENS JACKET — Discount, Winter, Boys, 30% off.",
    },
    {
        "name": "JR DENIM LONDON COAT",
        "sku": "B-002",
        "price": "$64.330",
        "description": "JR DENIM LONDON COAT — Discount, Winter, Boys, 30% off.",
    },
    {
        "name": "TURKEY JACKET",
        "sku": "G-005",
        "price": "$62.940",
        "description": "TURKEY JACKET — Discount, Winter, Girls, 40% off.",
    },
    {
        "name": "TURKEY JACKET",
        "sku": "G-006",
        "price": "$56.940",
        "description": "TURKEY JACKET — Discount, Winter, Girls, 40% off.",
    },
    {
        "name": "ATHENS JACKET",
        "sku": "B-003",
        "price": "$34.930",
        "description": "ATHENS JACKET — Discount, Winter, Boys, 30% off.",
    },
    {
        "name": "PRINT JACKET",
        "sku": "G-007",
        "price": "$57.540",
        "description": "PRINT JACKET — Discount, Winter, Girls, 40% off.",
    },
    {
        "name": "KID MURCIA T-SHIRT",
        "sku": "G-008",
        "price": "$29.900",
        "description": "KID MURCIA T-SHIRT — New In, Spring, Girls.",
    },
    {
        "name": "KID FLOWER TANK TOP",
        "sku": "G-009",
        "price": "$29.900",
        "description": "KID FLOWER TANK TOP — New In, Spring, Girls.",
    },
    {
        "name": "KID BALI SHORTS",
        "sku": "G-010",
        "price": "$29.900",
        "description": "KID BALI SHORTS — New In, Spring, Girls.",
    },
    {
        "name": "KID CLUB T-SHIRT",
        "sku": "G-011",
        "price": "$29.900",
        "description": "KID CLUB T-SHIRT — New In, Spring, Girls.",
    },
    {
        "name": "KID RIO CARDIGAN",
        "sku": "G-012",
        "price": "$49.900",
        "description": "KID RIO CARDIGAN — New In, Spring, Girls.",
    },
    {
        "name": "KID MURCIA TANK TOP",
        "sku": "G-013",
        "price": "$25.900",
        "description": "KID MURCIA TANK TOP — New In, Spring, Girls.",
    },
    {
        "name": "KID PRINT TANK TOP",
        "sku": "G-014",
        "price": "$34.900",
        "description": "KID PRINT TANK TOP — New In, Spring, Girls.",
    },
    {
        "name": "KID VIENNA DENIM",
        "sku": "G-015",
        "price": "$59.900",
        "description": "KID VIENNA DENIM — New In, Spring, Girls.",
    },
    {
        "name": "KID PRINT WINDBREAKER",
        "sku": "G-016",
        "price": "$79.900",
        "description": "KID PRINT WINDBREAKER — New In, Spring, Girls.",
    },
    {
        "name": "LIGHTWEIGHT WINDBREAKER",
        "sku": "B-004",
        "price": "$62.900",
        "description": "LIGHTWEIGHT WINDBREAKER — New In, Spring, Boys.",
    },
]


def main():
    print("Creating tables if they do not already exist...")
    try:
        init_db()
    except RuntimeError as exc:
        print(exc)
        raise SystemExit(1) from exc

    print(f"Embedding and inserting {len(DUMMY_PRODUCTS)} dummy products...")
    upsert_products_batch(DUMMY_PRODUCTS)

    print("Done. Dummy products are seeded.")


if __name__ == "__main__":
    main()
