from .common_imports import (
    dedent,
    config,
    Agent,
    # QuietAgentHooks,
    VerboseAgentHooks,
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
        The article layout is: 
        <article_layout>
        {context.context.article_layout}
        </article_layout>
        You MUST make sure to use the article layout to design the section plans. Exactly as it is, no deviations allowed from the article layout. You must use the exact section names and sub-sections as they are in the article layout.
        """)
    return dedent(f"""
    {article_instruction}
    
    TASK: Research ALL sections provided in the input systematically.
    
    WORKFLOW:
    1. Parse the input to get all section plans
    2. For each section plan:
       - Check if it has research_queries
       - For each query, perform web search (max 3 results)
       - Collect the search results as findings
       - Write a brief summary
    3. Create SectionResearchNotes for each section (use string section_id)
    4. Return all sections in ResearchNotes format
    
    CRITICAL: If a section has no research_queries, still create a SectionResearchNotes entry with empty findings array and section_id.
    
    REQUIRED OUTPUT: Return ONLY valid JSON that exactly matches this structure:
    
    {{
      "notes_by_section": [
        {{
          "section_id": "1",
          "findings": [
            {{
              "source_url": "https://example.com",
              "snippet": "Search result text...",
              "relevance_score": null,
              "scraped_content": null
            }}
          ],
          "summary": "Brief summary of research"
        }}
      ]
    }}
    
    IMPORTANT:
    - Return valid JSON only, no extra text
    - Include ALL sections from input
    - Use string section_ids ("1", "2", etc.)
    - If no findings, use empty array: "findings": []
    - Always include summary field (can be "No research performed" if needed)
    """)

agent = Agent[ArticleCreationWorkflowConfig](
    name="Research Agent",
    instructions=research_dynamic_instructions,
    model=config.LARGE_FAST_MODEL, 
    tools=[perform_serper_web_search],
    output_type=ResearchNotes,
    hooks=VerboseAgentHooks(),  # Changed back from VerboseAgentHooks to QuietAgentHooks
)