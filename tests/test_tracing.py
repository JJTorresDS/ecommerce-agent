from types import SimpleNamespace
from unittest.mock import MagicMock

from ecommerce_agent.agent import tracing as tracing_mod


def test_setup_tracing_instruments_openai_agents_when_enabled(monkeypatch):
    instrumentor = MagicMock()
    order: list[str] = []

    def fake_client():
        order.append("client")
        return MagicMock()

    class FakeInstrumentor:
        def instrument(self):
            order.append("instrument")
            instrumentor.instrument()

    monkeypatch.setattr(
        tracing_mod,
        "settings",
        SimpleNamespace(langfuse_enabled=True, agent_tracing=False),
    )
    monkeypatch.setattr(tracing_mod, "_instrumented", False)
    monkeypatch.setattr(tracing_mod, "OpenAIAgentsInstrumentor", FakeInstrumentor)
    monkeypatch.setattr(tracing_mod, "get_client", fake_client)
    disabled = MagicMock()
    monkeypatch.setattr(tracing_mod, "set_tracing_disabled", disabled)

    tracing_mod.setup_tracing()

    instrumentor.instrument.assert_called_once()
    disabled.assert_called_once_with(False)
    assert order == ["client", "instrument"]


def test_secret_attribute_names_are_redacted():
    assert tracing_mod._should_redact_attribute("scope.attributes.public_key")
    assert tracing_mod._should_redact_attribute("OPENAI_API_KEY")
    assert not tracing_mod._should_redact_attribute("llm_provider")


def test_setup_tracing_skips_instrumentation_without_keys(monkeypatch):
    instrumentor = MagicMock()
    monkeypatch.setattr(
        tracing_mod,
        "settings",
        SimpleNamespace(langfuse_enabled=False, agent_tracing=False),
    )
    monkeypatch.setattr(tracing_mod, "_instrumented", False)
    monkeypatch.setattr(
        tracing_mod,
        "OpenAIAgentsInstrumentor",
        lambda: instrumentor,
    )

    tracing_mod.setup_tracing()

    instrumentor.instrument.assert_not_called()
