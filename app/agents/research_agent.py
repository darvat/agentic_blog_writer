from .common_imports import (
    dedent,
    config,
    Agent,
    CustomAgentHooks,
    perform_serper_web_search,
)

from app.models.article_schemas import ResearchNotes

agent = Agent(
    name="Research Agent",
    instructions=dedent("""
    You are a research agent. Your primary responsibility is to take a list of research queries for different sections of a blog post 
    and find relevant information for each query. 
    
    For each section plan provided, you will:
    1. Review the `research_queries` list.
    2. For each query, conduct thorough research using the available tools (web search) with a maximum of 2 search results per query.
    3. Compile the individual findings into `SectionResearchNotes` objects, including snippets and source URLs where possible.
    4. Group these findings into a `ResearchNotes` object for the corresponding section_id.
    5. Provide a summary of the research for each section.
    6. The web search parameters are decided based on the query language and the query itself (e.g.: location, language, etc.).
    
    Your final output should be a `ResearchNotes` object containing a list of `SectionResearchNotes`.
    Make sure to include all web search results in the final output, do not filter out any results.
    """),
    model=config.SMALL_REASONING_MODEL, # Or SMALL_FAST_MODEL if appropriate
    tools=[perform_serper_web_search],
    output_type=ResearchNotes,
    hooks=CustomAgentHooks(),
)