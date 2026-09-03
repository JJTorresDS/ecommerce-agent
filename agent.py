"""
Boilerplate: OpenAI Agents SDK agent using the Responses API, backed by either
a local Ollama model or OpenRouter, selected via .env, with tools.

Requirements:
    pip install openai-agents openai python-dotenv

.env:
    LOCAL_MODEL=true          # true -> Ollama, false -> OpenRouter
    OPEN_ROUTER_API_KEY=...   # only needed when LOCAL_MODEL=false

If using Ollama, make sure it's running locally and you've pulled a model
that supports tool calling, e.g.:
    ollama pull qwen2.5:7b

Note: models like deepseek-r1 do NOT support tool calling and will error out.
Llama 3.x and Qwen2.5 are solid choices for local tool use.

This file only DEFINES the agent (`agent`). Instantiate/run it from your
notebook — see the usage snippet in the comment at the bottom.
"""

import os
from dotenv import load_dotenv
from agents import Agent, OpenAIResponsesModel
from openai import AsyncOpenAI
from tools import (
    get_item_details,
    search_faq_knowledgebase,
    search_products,
)
load_dotenv()

# --- Provider selection (.env: LOCAL_MODEL=true/false) ----------------------
# NOTE: assuming "LOCA_MODEL" in the request was a typo for "LOCAL_MODEL".
# Rename this string if you actually want the key spelled "LOCA_MODEL".
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "false").strip().lower() == "true"

if LOCAL_MODEL:
    # --- Ollama connection (OpenAI-compatible endpoint) ---------------------
    MODEL_NAME = "qwen2.5:7b"  # change to whatever you've pulled

    client = AsyncOpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama",  # required by the client, value is irrelevant for Ollama
    )
else:
    # --- OpenRouter connection ------------------------------------------------
    MODEL_NAME = "nvidia/nemotron-3.5-lightning:free" # change to whatever OpenRouter model you want

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPEN_ROUTER_API_KEY"),
    )

model = OpenAIResponsesModel(
    model=MODEL_NAME,
    openai_client=client,
)




from agents.lifecycle import AgentHooksBase


class PrintToolHooks(AgentHooksBase):
    async def on_tool_start(self, context, agent, tool):
        args = getattr(context, "tool_arguments", None)
        print(f"[tool] called {tool.name} args={args}", flush=True)

    async def on_tool_end(self, context, agent, tool, result):
        preview = repr(result)
        if len(preview) > 400:
            preview = preview[:400] + "..."
        print(f"[tool] {tool.name} returned {preview}", flush=True)


# --- Define the agent --------------------------------------------------------
agent = Agent(
    name="ecommerce_agent",
    instructions="""
You are a helpful assistant.
Use the available tools whenever they are relevant to answering the user's
request. If a tool isn't relevant, just answer directly.

""",
    model=model,
    hooks=PrintToolHooks(),
    tools=[
        get_item_details,
        search_faq_knowledgebase,
        search_products,
    ],
)


# ---------------------------------------------------------------------------
# Usage from a Jupyter notebook:
#
# from agent import agent
# from agents import Runner
#
# # Jupyter supports top-level await:
# result = await Runner.run(agent, "What's the weather in Buenos Aires, and what's 12 + 30?")
# print(result.final_output)
#
# # Or synchronously:
# # result = Runner.run_sync(agent, "What's the weather in Buenos Aires?")
# # print(result.final_output)
# ---------------------------------------------------------------------------