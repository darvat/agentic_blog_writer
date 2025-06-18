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
    
    CRITICAL WORKFLOW - FOLLOW THESE STEPS EXACTLY:
    
    STEP 1 - UNDERSTANDING INPUT:
    - You will receive a JSON input with a "section_plans" array
    - Each section has: section_id (int), title, key_points, and research_queries (may be null)
    - You MUST process ALL sections, even if they have no research queries
    
    STEP 2 - SYSTEMATIC RESEARCH PROCESS:
    For each section in the input:
    1. Extract the section_id (convert to string for output)
    2. If the section has research_queries:
       - Perform web search for each query (max 3 results per query)
       - Collect ALL search results as findings
       - If a search fails, continue with the next query
       - Write a summary based on the findings
    3. If the section has NO research_queries or null:
       - Create entry with empty findings array []
       - Set summary to "No research queries provided for this section"
    
    STEP 3 - COLLECTING RESULTS:
    - Maintain a running list of all section research notes
    - Each section MUST have an entry in your final output
    - Missing sections will cause the workflow to fail
    
    STEP 4 - OUTPUT STRUCTURE:
    Return ONLY valid JSON matching this exact structure:
    
    {{
      "notes_by_section": [
        {{
          "section_id": "1",  // MUST be string, not int
          "findings": [
            {{
              "source_url": "https://example.com",
              "snippet": "Actual search result text from the web search",
              "relevance_score": null,
              "scraped_content": null
            }}
            // More findings...
          ],
          "summary": "Brief summary of ALL findings for this section, or explanation if no research was done"
        }},
        // ALL sections must be included
      ]
    }}
    
    CRITICAL RULES:
    1. Process EVERY section from the input - no exceptions
    2. Convert integer section_ids to strings in output
    3. If search fails, continue processing other queries/sections
    4. Empty findings array is valid: "findings": []
    5. Always include meaningful summary (never null or empty)
    6. Return ONLY the JSON - no extra text before or after
    7. The number of sections in output MUST match input
    
    COMMON MISTAKES TO AVOID:
    - Don't stop if one search fails - continue with others
    - Don't skip sections without research_queries
    - Don't forget to convert section_id to string
    - Don't return partial results - process ALL sections
    
    EXAMPLE THINKING PROCESS:
    "I received 8 sections. Section 1 has 2 queries, I'll search both. Section 2 has 3 queries, I'll search all. 
    Section 8 has null queries, I'll create empty entry. My output will have exactly 8 sections."
    """)

agent = Agent[ArticleCreationWorkflowConfig](
    name="Research Agent",
    instructions=research_dynamic_instructions,
    model=config.SMALL_REASONING_MODEL, 
    tools=[perform_serper_web_search],
    output_type=ResearchNotes,
    hooks=VerboseAgentHooks(),  # Changed back from VerboseAgentHooks to QuietAgentHooks
)