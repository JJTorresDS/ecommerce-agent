"""Shared TestClient and fixtures from dummy catalog + FAQ Google Doc."""

from __future__ import annotations

import csv
import io
import os

os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "postgres")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "pyrolabs-local")
os.environ.setdefault("AGENT_TRACING", "false")
# Blank Langfuse keys before importing the app so tests never export traces.
os.environ["LANGFUSE_PUBLIC_KEY"] = ""
os.environ["LANGFUSE_SECRET_KEY"] = ""

import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ecommerce_agent.api.app import app
from ecommerce_agent.config import PROJECT_ROOT

FAQ_DOCUMENT_ID = "1FlKHKxwltF_2S9ADmkfT3B0ajapSMrVKYWRUXf13mno"
FAQ_DOCUMENT_URL = (
    f"https://docs.google.com/document/d/{FAQ_DOCUMENT_ID}/edit"
    "?tab=t.0#heading=h.l1ncunxa9ncf"
)
FAQ_TITLE = "Pre Sales Agent FAQ doc"
FAQ_TEXT = (
    "Frequently Asked Questions\n"
    "How do I contact customer service? Chat with us here, "
    "email support@jonas-demo.com, or call.\n"
)
FAQ_STRUCTURED_TEXT = (
    "# Frequently Asked Questions\n"
    "FAQ covering shipping, returns, and customer support.\n"
    "\n"
    "## How do I contact customer service?\n"
    "Chat with us here, email support@jonas-demo.com, or call.\n"
    "\n"
    "## Do you accept credit cards\n"
    "Yes\n"
    "\n"
    "## Are you opened on holidays\n"
    "Loremp ipsum\n"
)


def _load_dummy_products() -> list[dict]:
    path = PROJECT_ROOT / "db" / "seed_products.py"
    spec = importlib.util.spec_from_file_location("seed_products", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.DUMMY_PRODUCTS


DUMMY_PRODUCTS = _load_dummy_products()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def dummy_products() -> list[dict]:
    return DUMMY_PRODUCTS


@pytest.fixture
def dummy_products_csv(dummy_products: list[dict]) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["sku", "description"])
    writer.writeheader()
    for product in dummy_products:
        writer.writerow(
            {"sku": product["sku"], "description": product["description"]}
        )
    return buf.getvalue().encode("utf-8")
