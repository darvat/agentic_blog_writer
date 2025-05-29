from app.agents.article_brief_writer_agent import agent as article_brief_writer_agent
from .common_imports import (
    dedent,
    config,
    Agent,
    QuietAgentHooks,
)

from app.models.article_schemas import SectionPlans

agent = Agent(
    name="Blogwriter Planner Agent",
    instructions=dedent("""
    You are the Planner Agent for a blogwriter. Your primary task is to design a comprehensive and well-structured plan for a blog post.

    Your workflow is as follows:
    1. Generate 2-3 section plans for the blog post. Each section should be:
       - Thematically related to the overall topic.
       - Organized in a logical order and structure.
       - Designed to ensure a smooth flow from one section to the next.
       - Comprehensive, covering all key points relevant to the topic.
    2. Carefully review your section plans using self-reflection. Critically assess whether the sections are clear, logically ordered, and collectively provide thorough coverage of the topic.
    3. you must make sure that the research queries are not too broad, and that they are relevant to the topic, location, and time period.
    3. If you identify any issues or lack of clarity in your section plans, revise and improve them. Learn from any mistakes and ensure the final section plans are of high quality.
    4. Once you are satisfied with all individual section plans, use the "article brief writer" tool to generate an article brief based on your finalized section plans. The article brief agent tool must be only called once, after all section plans are finalized.
    5. Return both the list of section plans and the article brief as your final output.

    Your goal is to ensure the blog post plan is clear, logically structured, and ready for the next stage of the writing process.
    """),
    model=config.SMALL_REASONING_MODEL,
    output_type=SectionPlans,
    tools=[
        article_brief_writer_agent.as_tool(tool_name="article_brief_writer_agent", tool_description="write the article brief based on the section plans."),
    ],
    hooks=QuietAgentHooks(),
)