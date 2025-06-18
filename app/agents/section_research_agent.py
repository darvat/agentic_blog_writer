"""
Section-specific research agent for handling individual sections.
This agent focuses on researching a single section at a time for better reliability.
"""

from .common_imports import (
    dedent,
    config,
    Agent,
    VerboseAgentHooks,
    perform_serper_web_search,
    RunContextWrapper,
)

from app.models.article_schemas import SectionResearchNotes
from app.models.workflow_schemas import ArticleCreationWorkflowConfig

def section_research_dynamic_instructions(
    context: RunContextWrapper[ArticleCreationWorkflowConfig], agent: Agent[ArticleCreationWorkflowConfig]
) -> str:
    
    return dedent(f"""
    You are a section-specific research agent. Your task is to research ONE section of a blog post.
    
    Blog post context:
    - Title: {context.context.title}
    - Description: {context.context.description}
    
    YOUR TASK:
    1. You will receive a SINGLE section plan as input
    2. Extract the research queries from this section
    3. Perform web searches for each query (max 3 results per query)
    4. Compile findings and write a summary
    
    INPUT FORMAT:
    {{
        "section_id": 1,
        "title": "Section Title",
        "key_points": ["point1", "point2"],
        "research_queries": ["query1", "query2"] or null
    }}
    
    WORKFLOW:
    1. If research_queries is null or empty:
       - Return empty findings with summary "No research queries provided"
    2. If research_queries exist:
       - Search for each query using perform_serper_web_search
       - Collect all results as findings
       - Write a comprehensive summary of the findings
    
    OUTPUT FORMAT (return ONLY this JSON):
    {{
        "section_id": "1",  // MUST be string
        "findings": [
            {{
                "source_url": "https://example.com",
                "snippet": "Actual text from search result",
                "relevance_score": null,
                "scraped_content": null
            }}
        ],
        "summary": "A comprehensive summary of all findings for this section"
    }}
    
    IMPORTANT:
    - Return ONLY valid JSON, no extra text
    - section_id must be converted to string
    - If no findings, use empty array: "findings": []
    - Always include a meaningful summary
    """)

agent = Agent[ArticleCreationWorkflowConfig](
    name="Section Research Agent",
    instructions=section_research_dynamic_instructions,
    model=config.SMALL_REASONING_MODEL,
    tools=[perform_serper_web_search],
    output_type=SectionResearchNotes,
    hooks=VerboseAgentHooks(),
) 