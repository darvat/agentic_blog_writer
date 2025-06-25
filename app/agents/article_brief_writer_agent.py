from .common_imports import (
    dedent,
    config,
    Agent,
    QuietAgentHooks,
)

from app.models.article_schemas import ArticleBrief

agent = Agent(
    name="Blogwriter Article Brief Writer Agent",
    instructions=dedent("""
    You are a article brief writer agent for a blogwriter.
    You are responsible for writing the article brief based on the section plans.
    You must return a article brief.    
    """),
    model=config.SMALL_REASONING_MODEL,
    output_type=ArticleBrief,
    hooks=QuietAgentHooks(),
)