import asyncio

from agents import Runner
from .common_imports import (
    Agent,
    dedent,
    config,
    logger,
    CustomAgentHooks,
)
from app.tools.scraper import scrape_website_Crawl4AI
from app.models.article_schemas import ResearchNotes # Assuming this schema exists

agent = Agent(
    name="Web Scraper Agent",
    instructions=dedent("""
    You are a web scraper agent. Your primary responsibility is to take a URL and scrape its content using the available tools.
    In the `ResearchNotes` object, you will find a list of `SectionResearchNotes` objects, each containing a list of `ResearchFinding` objects.
    Each `ResearchFinding` object contains a `source_url` field, which is the URL of the website that the research finding is from.
    You will use the `scrape_website_Crawl4AI` tool to scrape the content of the website that the research finding is from.
    You must clean the scraped content to remove any HTML tags and other unwanted characters, irrelevant content, headers, footers, promotional content, advertisements, etc.
    You will then return the cleaned scraped content as an string and update the `scraped_website` field of the `ResearchFinding` object.
    You will do this for each `ResearchFinding` object in the `ResearchNotes` object.
    You will then return the updated `ResearchNotes` object.
    You can only touch the `scraped_website` field of the `ResearchFinding` object, do not touch any other fields.    
    """),
    model=config.SMALL_FAST_MODEL,
    tools=[scrape_website_Crawl4AI],
    output_type=ResearchNotes,
    hooks=CustomAgentHooks(),
)


## let'use the following input to test the agent:

async def test_web_scraper_agent():
    input_data = ResearchNotes(
        notes_by_section=[
            {
                "section_id": "1",
                "summary": "Research indicates AI automation can save professionals 4–12 hours per week (equivalent to adding a teammate) and yield 5.4% average time savings. Workflow automation drives 10–50% task time reductions, while sales processes see up to 1–2 hours saved per activity. Case studies across industries report cost cuts up to 32%, leaner staffing, and recurring savings via AI-driven procurement and maintenance.",
                "findings": [
                    {
                        "source_url": "https://www.thomsonreuters.com/en/press-releases/2024/july/ai-set-to-save-professionals-12-hours-per-week-by-2029",
                        "snippet": "Survey respondents predict AI to free up 12 hours per week within the next five years, with four hours per week saved in the next year alone – the equivalent of adding an additional colleague for every 10 team members.",
                        "scraped_website":""
                    },
                    {
                        "source_url": "https://www.cflowapps.com/workflow-automation-statistics/",
                        "snippet": "73% of the leaders in the IT industry attribute 10-50% of time savings in performing tasks to automation. 25% of organizations are currently using AI in their process automation, and 53% intend to implement it soon.",
                        "scraped_website":""
                    }
                ]
            },
            {
                "section_id": "2",
                "summary": "AI-driven decisions span pricing, supply chain, risk management, and personalized marketing, delivering faster, data-backed strategies. Predictive analytics success is tracked via KPIs such as ROI, accuracy, lift, adoption rate, and reduction in decision lead times, demonstrating measurable improvements in forecasting and operational performance.",
                "findings": [
                    {
                        "source_url": "https://socialnomics.net/2023/05/10/8-business-examples-of-ai-and-data-driven-decisions/",
                        "snippet": "Profiles eight real-life examples where AI and data-driven insights revolutionized strategic planning, pricing, and customer engagement.",
                        "scraped_website":""
                    },
                    {
                        "source_url": "https://kaopiz.com/en/articles/ai-use-cases-in-business/",
                        "snippet": "Top 8 AI use cases in business for 2025 include dynamic pricing, inventory optimization, predictive maintenance, and personalized marketing.",
                        "scraped_website":""
                    }
                ]
            }
        ],
        general_findings=[]
    )
    final_result = await Runner.run(agent, input_data)
    print(final_result)

if __name__ == "__main__":
    asyncio.run(test_web_scraper_agent())
