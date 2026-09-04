"""Backward-compatible entry. Prefer: uv run python db/seed_products.py"""

import importlib.util
from pathlib import Path

_path = Path(__file__).resolve().parent.parent / "db" / "seed_products.py"
_spec = importlib.util.spec_from_file_location("db_seed_products", _path)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)

DUMMY_PRODUCTS = _mod.DUMMY_PRODUCTS
main = _mod.main

if __name__ == "__main__":
    main()
