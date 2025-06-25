"""
Research recovery agent for analyzing failed research attempts and generating improved queries.
This agent is used when section research fails to ensure no section is left un-researched.
"""

from .common_imports import (
    dedent,
    config,
    Agent,
    VerboseAgentHooks,
    RunContextWrapper,
)

from app.models.article_schemas import SectionPlan
from app.models.workflow_schemas import ArticleCreationWorkflowConfig
from pydantic import BaseModel

class ImprovedSectionPlan(BaseModel):
    """Section plan with improved research queries"""
    section_id: int
    title: str
    key_points: list[str]
    research_queries: list[str]
    improvement_rationale: str

def research_recovery_dynamic_instructions(
    context: RunContextWrapper[ArticleCreationWorkflowConfig], agent: Agent[ArticleCreationWorkflowConfig]
) -> str:
    
    return dedent(f"""
    You are a research recovery agent. Your task is to analyze failed research attempts and generate improved research queries.
    
    Blog post context:
    - Title: {context.context.title}
    - Description: {context.context.description}
    
    YOUR TASK:
    You will receive a section plan that has failed research. Your job is to:
    1. Analyze why the original research queries might have failed
    2. Generate new, more effective research queries
    3. Provide rationale for the improvements
    
    COMMON RESEARCH FAILURE REASONS:
    - Queries too broad or generic
    - Queries too specific or narrow
    - Queries using technical jargon that returns no results
    - Queries not aligned with current trends/information
    - Queries lacking context or specificity
    
    IMPROVEMENT STRATEGIES:
    - Make queries more specific and actionable
    - Include current year for time-sensitive topics
    - Use alternative terminology and synonyms
    - Break complex queries into simpler components
    - Add context keywords related to the blog title
    - Use question-based queries for better results
    
    INPUT FORMAT:
    {{
        "section_id": 1,
        "title": "Section Title",
        "key_points": ["point1", "point2"],
        "research_queries": ["failed_query1", "failed_query2"] or null,
        "failure_reason": "Explanation of why research failed"
    }}
    
    OUTPUT FORMAT (return ONLY this JSON):
    {{
        "section_id": 1,
        "title": "Section Title", 
        "key_points": ["point1", "point2"],
        "research_queries": ["improved_query1", "improved_query2", "improved_query3"],
        "improvement_rationale": "Explanation of why these new queries should work better"
    }}
    
    GUIDELINES:
    - Generate 3-5 new research queries per section
    - Make queries specific to the section's key points
    - Include context from the blog title/description when relevant
    - Ensure queries are likely to return concrete, useful results
    - Avoid overly technical or niche terminology unless necessary
    - Consider different angles and approaches to the topic
    
    IMPORTANT:
    - Return ONLY valid JSON, no extra text
    - New queries should be significantly different from failed ones
    - Focus on actionable, searchable terms
    """)

agent = Agent[ArticleCreationWorkflowConfig](
    name="Research Recovery Agent",
    instructions=research_recovery_dynamic_instructions,
    model=config.SMALL_REASONING_MODEL,
    tools=[],  # No tools needed, just query analysis and generation
    output_type=ImprovedSectionPlan,
    hooks=VerboseAgentHooks(),
) 