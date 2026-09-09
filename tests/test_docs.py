from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "mlruns",
    "mlartifacts",
    "__pycache__",
    ".pytest_cache",
}

TABLES = (
    "product_embeddings",
    "documents",
    "document_embeddings",
    "agent_sessions",
    "agent_messages",
    "ask_turns",
    "conversation_feedback",
)


def _markdown_paths() -> list[Path]:
    paths = []
    for path in ROOT.rglob("*.md"):
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        paths.append(path)
    return sorted(paths)


def test_readme_references_all_markdown_files():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    missing = []
    for path in _markdown_paths():
        rel = path.relative_to(ROOT).as_posix()
        if rel == "README.md":
            continue
        if rel not in readme:
            missing.append(rel)
    assert missing == [], f"README.md must mention: {', '.join(missing)}"


def test_evaluation_md_embeds_asset_images():
    text = (ROOT / "evals" / "evaluation.md").read_text(encoding="utf-8")
    for name in (
        "terminal-search-eval.png",
        "mlflow-agent-eval.png",
        "grafana-monitoring.png",
        "langraph-observability.png",
    ):
        assert f"../assets/{name}" in text


def test_readme_overview_embeds_app_screenshots():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    overview = readme.find("## Overview")
    run = readme.find("## Run")
    assert overview != -1
    assert run != -1
    assert overview < run
    for name in ("app_ui.png", "app_api.png"):
        assert f"assets/{name}" in readme
    for needle in (
        "product",
        "document",
        "embedding",
        "memory",
        "feedback",
    ):
        assert needle in readme[overview:run].lower()


def test_db_schema_doc_covers_all_tables():
    schema = (ROOT / "db" / "schema.md").read_text(encoding="utf-8")
    for table in TABLES:
        assert table in schema
    assert "1" in schema and "-1" in schema
    assert "VECTOR" in schema or "vector" in schema
