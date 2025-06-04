from .common_imports import (
    dedent,
    config,
    Agent,
    QuietAgentHooks,
    perform_serper_web_search,
    RunContextWrapper,
)

from app.models.article_schemas import ResearchNotes
from app.models.workflow_schemas import ArticleCreationWorkflowConfig

def research_dynamic_instructions(
    context: RunContextWrapper[ArticleCreationWorkflowConfig], agent: Agent[ArticleCreationWorkflowConfig]
) -> str:
    
    if not context.context.article_layout:
        article_instruction = dedent(f"""
        You are a research agent. Your primary responsibility is to take a list of research queries for different sections of a blog post 
        and find relevant information for each query. 
        The title of the blog post is: {context.context.title}
        The description of the blog post is: {context.context.description}
        """)
    else:
        article_instruction = dedent(f"""
        You are a research agent. Your primary responsibility is to take a list of research queries for different sections of a blog post 
        and find relevant information for each query. 
        The title of the blog post is: {context.context.title}
        The description of the blog post is: {context.context.description}
        The article layout is: {context.context.article_layout}
        """)
    return dedent(f"""
    {article_instruction}
    
    For each section plan provided, you will:
    1. Review the `research_queries` list.
    2. For each query, conduct thorough research using the available tools (web search) with a maximum of 2 search results per query.
    3. Compile the individual findings into `SectionResearchNotes` objects, including snippets and source URLs where possible.
    4. Group these findings into a `ResearchNotes` object for the corresponding section_id.
    5. Provide a summary of the research for each section.
    6. The web search parameters are decided based on the query language and the query itself (e.g.: location, language, etc.).
    
    Your final output should be a `ResearchNotes` object containing a list of `SectionResearchNotes`.
    Make sure to include all web search results in the final output, do not filter out any results.
    """)

agent = Agent[ArticleCreationWorkflowConfig](
    name="Research Agent",
    instructions=research_dynamic_instructions,
    model=config.SMALL_REASONING_MODEL, # Or SMALL_FAST_MODEL if appropriate
    tools=[perform_serper_web_search],
    output_type=ResearchNotes,
    hooks=QuietAgentHooks(),
)