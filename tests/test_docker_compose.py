from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_dockerfile_runs_uvicorn_on_all_interfaces():
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "python:3.12" in text
    assert "uvicorn" in text
    assert "0.0.0.0" in text
    assert "8000" in text
    assert "uv run --frozen --no-dev" in text or '"--frozen"' in text


def test_pyproject_limits_python_below_3_14():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'requires-python = ">=3.12,<3.14"' in text
    assert "https://pytorch.org" not in text


def test_compose_defines_postgres_app_and_mlflow():
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    for service in ("postgres:", "app:", "mlflow:"):
        assert service in text
    assert "pgvector/pgvector" in text
    assert "8000:8000" in text
    assert "5000:5000" in text
    assert "POSTGRES_HOST: postgres" in text
    assert "MLFLOW_TRACKING_URI: http://mlflow:5000" in text
    assert "pg_isready" in text
    assert "container_name: postgres-pgvector" not in text
    assert "pgadmin:" in text
    assert "dpage/pgadmin4" in text
    assert "5050:80" in text
    assert "--frozen" in text
    assert "grafana:" in text
    assert "3000:3000" in text
    assert "prometheus:" in text
    assert "9090:9090" in text
    assert "prom/prometheus" in text
    assert "grafana/grafana" in text


def test_inspect_sql_lists_catalog_tables():
    text = (ROOT / "db" / "inspect.sql").read_text(encoding="utf-8")
    for table in (
        "product_embeddings",
        "documents",
        "document_embeddings",
        "agent_sessions",
        "agent_messages",
        "ask_turns",
        "conversation_feedback",
    ):
        assert table in text


def test_env_example_lists_required_secrets():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    for key in (
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "OPENAI_API_KEY",
        "OPEN_ROUTER_API_KEY",
        "MISTRAL_API_KEY",
        "GEMINI_API_KEY",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "PGADMIN_DEFAULT_EMAIL",
        "PGADMIN_DEFAULT_PASSWORD",
        "GRAFANA_ADMIN_USER",
        "GRAFANA_ADMIN_PASSWORD",
    ):
        assert key in text


def test_gitignore_excludes_local_mlflow_and_os_junk():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in (
        "mlruns/",
        "mlartifacts/",
        "mlflow.db",
        "mlflow.db-journal",
        ".env",
        "/secrets/",
        ".DS_Store",
    ):
        assert pattern in text


def test_dockerignore_excludes_local_mlflow_and_secrets():
    text = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    for pattern in (
        "mlruns/",
        "mlartifacts/",
        "mlflow.db",
        "mlflow.db-journal",
        ".env",
        "secrets/",
        ".DS_Store",
    ):
        assert pattern in text


def test_grafana_dashboard_tracks_latency_words_and_feedback():
    dashboard = (ROOT / "grafana" / "dashboards" / "production.json").read_text(
        encoding="utf-8"
    )
    for needle in (
        "ask_latency_seconds",
        "ask_question_words",
        "ask_answer_words",
        "feedback_total",
    ):
        assert needle in dashboard


def test_prometheus_scrapes_app_metrics():
    text = (ROOT / "prometheus" / "prometheus.yml").read_text(encoding="utf-8")
    assert "app:8000" in text
    assert "/metrics" in text
