from agents import Agent, Tool
from agents.lifecycle import AgentHooks
from agents.run_context import RunContextWrapper
from typing import Any
from rich.console import Console
from rich.panel import Panel

console = Console()

class CustomAgentHooks(AgentHooks):
    async def on_start(
        self,
        context: RunContextWrapper[Any],
        agent: Agent[Any],
    ) -> None:
        console.log(f"[bold green]Agent: {agent.name} started[/bold green]")

    async def on_end(
        self,
        context: RunContextWrapper[Any],
        agent: Agent[Any],
        output: Any,
    ) -> None:
        console.log(f"[bold blue]Agent: {agent.name} ended[/bold blue]")
        
    async def on_tool_start(
        self,
        context: RunContextWrapper[Any],
        agent: Agent[Any],
        tool: Tool,
    ) -> None:
        console.log(f"[bold blue]Agent: {agent.name} called: {tool.name}[/bold blue]\n")
    async def on_tool_end(
        self,
        context: RunContextWrapper[Any],
        agent: Agent[Any],
        tool: Tool,
        result: Any,
    ) -> None:
        console.log(f"[bold green]Agent: {agent.name} tool: {tool.name} ended[/bold green]\n")
        self._print_panel_recursive(result, agent.name, tool.name)

    def _print_panel_recursive(self, item: Any, agent_name: str, tool_name: str) -> None:
        if isinstance(item, list):
            for sub_item in item:
                self._print_panel_recursive(sub_item, agent_name, tool_name)
        elif isinstance(item, dict):
            console.print(
                Panel(
                    renderable=item.model_dump_json(indent=2) if hasattr(item, 'model_dump_json') else str(item),
                    border_style="purple",
                    title=f"Agent: {agent_name} tool: {tool_name} Output",
                )
            )
        else:
            console.print(
                Panel(
                    renderable=str(item),
                    border_style="purple",
                    title=f"Agent: {agent_name} tool: {tool_name} Output",
                )
            )