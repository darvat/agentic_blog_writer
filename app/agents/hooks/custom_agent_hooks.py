from agents import Agent, Tool
from agents.lifecycle import AgentHooks
from agents.run_context import RunContextWrapper
from typing import Any
from rich.console import Console
from rich.panel import Panel

console = Console()

class CustomAgentHooks(AgentHooks):
    def __init__(self, verbose: bool = False):
        """
        Initialize agent hooks with optional verbose mode.
        
        Args:
            verbose: If True, prints detailed agent lifecycle events.
                    If False, only prints minimal events to avoid interference.
        """
        self.verbose = verbose
    
    async def on_start(
        self,
        context: RunContextWrapper[Any],
        agent: Agent[Any],
    ) -> None:
        if self.verbose:
            console.log(f"[dim]Agent: {agent.name} started[/dim]")

    async def on_end(
        self,
        context: RunContextWrapper[Any],
        agent: Agent[Any],
        output: Any,
    ) -> None:
        if self.verbose:
            console.log(f"[dim]Agent: {agent.name} ended[/dim]")
        
    async def on_tool_start(
        self,
        context: RunContextWrapper[Any],
        agent: Agent[Any],
        tool: Tool,
    ) -> None:
        # Only log tool usage, not full details to avoid spam
        pass
        
    async def on_tool_end(
        self,
        context: RunContextWrapper[Any],
        agent: Agent[Any],
        tool: Tool,
        result: Any,
    ) -> None:
        # Only log tool completion, not full results to avoid spam
        pass

    def _print_panel_recursive(self, item: Any, agent_name: str, tool_name: str) -> None:
        # Disabled by default to avoid output interference
        if self.verbose:
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