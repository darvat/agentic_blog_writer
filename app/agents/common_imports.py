import asyncio
from textwrap import dedent
from app.core.config import config
from app.core.logging_config import get_logger
from agents import Agent, Runner
from app.core.console_config import console
from app.agents.hooks.custom_agent_hooks import CustomAgentHooks
from app.tools.web_search_tool import perform_ddg_web_search
from app.tools.bing_websearch import perform_bing_web_search
from app.tools.serper_websearch import perform_serper_web_search
from agents import RunContextWrapper

logger = get_logger(__name__)

# Create quiet hooks for workflow agents to avoid output interference
QuietAgentHooks = lambda: CustomAgentHooks(verbose=False)
VerboseAgentHooks = lambda: CustomAgentHooks(verbose=True) 