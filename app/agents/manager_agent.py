from app.agents.research_agent import agent as research_agent
from .common_imports import (
    asyncio,
    dedent,
    config,
    Agent,
    Runner,
    console,
    logger,
    CustomAgentHooks,
)

from app.agents.planner_agent import agent as planner_agent
from app.models.article_schemas import ResearchNotes



agent = Agent(
    name="Blogwriter Manager Agent",
    instructions=dedent("""
    You are the Manager Agent for a blog writing workflow. 

    Your task is to coordinate the creation of a high-quality blog post by orchestrating the work of two specialized agents: the Planner Agent and the Research Agent.
    The planner agent is responsible for planning the blog post sections and the article brief.
    The research agent is responsible for conducting research for the blog post sections.

    Workflow:
    1. Begin by instructing the Planner Agent to generate a detailed article brief and a set of section plans for the blog post. If any part of the brief or section plans is unclear, incomplete, or could be improved, request clarification or revisions from the Planner Agent until you are satisfied with the quality and clarity. You MUST only call the planner agent once, it will manage the entire workflow for itself.
    2. Once the planning phase is complete and you have a clear article brief and section plans, pass the complete article brief and all section plans to the Research Agent in a single request to conduct comprehensive research for all sections. You MUST only call the research agent once, it will manage the entire workflow for itself. Ensure that the research is thorough and relevant for all planned sections.
    3. You must make sure to include all relevant web search results in the final output, try not to filter out any results. Only filter out results that are absolutely not relevant to the blog post topic.
    
    Your goal is to ensure that the blog post is well-structured, thoroughly researched, and ready for drafting.
    """),
    model=config.SMALL_REASONING_MODEL,
    tools=[
        planner_agent.as_tool(tool_name="planner_agent", tool_description="plan the blog post sections."),
        research_agent.as_tool(tool_name="research_agent", tool_description="perform web research for the blog post"),
    ],
    output_type=ResearchNotes,
    hooks=CustomAgentHooks(),
)

async def main():
    """
    Main function to run the manager agent.
    """
    result = await Runner.run(agent, "Write a blog post about the benefits of using AI in the workplace.")
    logger.debug(f"Result: {result}")
    console.rule()
    from rich.panel import Panel
    console.print(Panel(result.final_output.model_dump_json(), border_style="yellow", title="Final Output from Manager Agent"))

if __name__ == "__main__":
    asyncio.run(main())