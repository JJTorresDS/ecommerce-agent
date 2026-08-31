"""
Seed the database with dummy products for testing the ecommerce agent.

Usage:
    uv run python seed_products.py
"""

from embeddings.ingest import init_db, upsert_products_batch

DUMMY_PRODUCTS = [
    {
        "product_id": "SKU-001",
        "content": "Zapatillas Nike Air Max para correr, hombre, talla 42, color negro",
    },
    {
        "product_id": "SKU-002",
        "content": "Tenis deportivos Adidas running, mujer, talla 38, color blanco",
    },
    {
        "product_id": "SKU-003",
        "content": "Camiseta de algodón para hombre, cuello redondo, talla M, color azul",
    },
    {
        "product_id": "SKU-004",
        "content": "Pantalón deportivo jogger unisex, talla L, color gris",
    },
    {
        "product_id": "SKU-005",
        "content": "Mochila resistente al agua para laptop de 15 pulgadas, color negro",
    },
    {
        "product_id": "SKU-006",
        "content": "Audífonos inalámbricos Bluetooth con cancelación de ruido, color blanco",
    },
    {
        "product_id": "SKU-007",
        "content": "Reloj inteligente deportivo con monitor de ritmo cardíaco, resistente al agua",
    },
    {
        "product_id": "SKU-008",
        "content": "Botella térmica de acero inoxidable, 1 litro, mantiene la temperatura 12 horas",
    },
    {
        "product_id": "SKU-009",
        "content": "Chaqueta impermeable para hombre, ideal para lluvia, talla XL, color verde",
    },
    {
        "product_id": "SKU-010",
        "content": "Bolso de mano para mujer, cuero sintético, color café, correa ajustable",
    },
]


def main():
    print("Initializing database (creating table if needed)...")
    init_db()

    print(f"Embedding and inserting {len(DUMMY_PRODUCTS)} dummy products...")
    upsert_products_batch(DUMMY_PRODUCTS)

    print("Done. Dummy products are seeded.")


if __name__ == "__main__":
    main()