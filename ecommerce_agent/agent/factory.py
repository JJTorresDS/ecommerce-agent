from pathlib import Path

from agents import Agent

from ecommerce_agent.agent.hooks import PrintToolHooks
from ecommerce_agent.agent.llm import build_model
from ecommerce_agent.agent.tracing import setup_tracing
from ecommerce_agent.tools import AGENT_TOOLS

INSTRUCTIONS = (
    Path(__file__).with_name("instructions.md").read_text(encoding="utf-8").strip()
)

setup_tracing()

agent = Agent(
    name="ecommerce_agent",
    instructions=INSTRUCTIONS,
    model=build_model(),
    hooks=PrintToolHooks(),
    tools=AGENT_TOOLS,
)


def build_agent() -> Agent:
    return agent
