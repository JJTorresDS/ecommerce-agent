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
