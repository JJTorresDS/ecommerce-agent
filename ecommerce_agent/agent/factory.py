from agents import Agent, set_tracing_disabled

from ecommerce_agent.agent.hooks import PrintToolHooks
from ecommerce_agent.agent.instructions import INSTRUCTIONS
from ecommerce_agent.agent.llm import build_model
from ecommerce_agent.config import settings
from ecommerce_agent.tools import AGENT_TOOLS

set_tracing_disabled(not settings.agent_tracing)

agent = Agent(
    name="ecommerce_agent",
    instructions=INSTRUCTIONS,
    model=build_model(),
    hooks=PrintToolHooks(),
    tools=AGENT_TOOLS,
)


def build_agent() -> Agent:
    return agent
