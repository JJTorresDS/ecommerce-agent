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


def test_db_schema_doc_covers_all_tables():
    schema = (ROOT / "db" / "schema.md").read_text(encoding="utf-8")
    for table in TABLES:
        assert table in schema
    assert "1" in schema and "-1" in schema
    assert "VECTOR" in schema or "vector" in schema
