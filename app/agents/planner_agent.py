from app.agents.article_brief_writer_agent import agent as article_brief_writer_agent
from agents import Agent, RunContextWrapper
from .common_imports import (
    dedent,
    config,
    QuietAgentHooks,
)

from app.models.article_schemas import SectionPlans
from app.models.workflow_schemas import ArticleCreationWorkflowConfig

def planner_dynamic_instructions(
    context: RunContextWrapper[ArticleCreationWorkflowConfig], agent: Agent[ArticleCreationWorkflowConfig]
) -> str:
    article_layout_instruction = (
        dedent("""
        First, you need to generate a suitable article layout 3-5 sections, as none was provided. 
        Then, proceed to design the section plans based on this generated layout.
        """)
        if not context.context.article_layout
        else dedent(f"""
            Your primary task is to design a comprehensive and well-structured plan for a blog post based on the title: "{context.context.title}", the description: "{context.context.description}" and the desired article layout: 
            <article_layout>
            {context.context.article_layout}
            </article_layout>
            You MUST make sure to use the article layout to design the section plans. Exactly as it is, no deviations allowed from the article layout. You must use the exact section names and sub-sections as they are in the article layout.
        """)
    )
    return dedent(f"""
    You are the Planner Agent for a blogwriter. 
    {article_layout_instruction}

    Your workflow is as follows:
    1. Generate the section plans for the blog post. Each section should be:
       - Thematically related to the overall topic (defined by the title: "{context.context.title}" and description: "{context.context.description}").
       - Organized in a logical order and structure, fitting the article layout.
       - Designed to ensure a smooth flow from one section to the next.
       - Comprehensive, covering all key points relevant to the topic.
    2. Carefully review your section plans using self-reflection. Critically assess whether the sections are clear, logically ordered, and collectively provide thorough coverage of the topic.
    3. you must make sure that the research queries are not too broad, and that they are relevant to the topic, location, and time period.
    3. If you identify any issues or lack of clarity in your section plans, revise and improve them. Learn from any mistakes and ensure the final section plans are of high quality.
    4. Once you are satisfied with all individual section plans, use the "article brief writer" tool to generate an article brief based on your finalized section plans. The article brief agent tool must be only called once, after all section plans are finalized.
    5. Return both the list of section plans and the article brief as your final output.

    Your goal is to ensure the blog post plan is clear, logically structured, and ready for the next stage of the writing process.
    """)

agent = Agent[ArticleCreationWorkflowConfig](
    name="Blogwriter Planner Agent",
    instructions=planner_dynamic_instructions,
    model=config.SMALL_REASONING_MODEL,
    output_type=SectionPlans,
    tools=[
        article_brief_writer_agent.as_tool(tool_name="article_brief_writer_agent", tool_description="write the article brief based on the section plans."),
    ],
    hooks=QuietAgentHooks(),
)