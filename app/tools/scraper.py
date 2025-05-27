from agents import function_tool
import re
from firecrawl.firecrawl import FirecrawlApp
from typing import Dict, Any
from newspaper import Article
from crawl4ai import *
from app.agents.common_imports import console
from app.core.config import config

firecrawl = FirecrawlApp(config.FIRECRAWL_API_KEY)

@function_tool
async def firecrawl_scrape(url: str) -> Dict[str, Any]:
    """Scrapes a website using Firecrawl's API.

    This function uses the Firecrawl API to scrape a website and return its content.

    Args:
        url: The URL of the website to scrape.

    Returns:
        A dictionary containing the raw scrape result from Firecrawl.
    """
    console.print(f"Scraping {url}")
    console.print(100*'-')
    try:
        response = firecrawl.scrape_url(url, formats=["markdown"], only_main_content=True)
        
        cleaned_markdown = re.sub(r'!?\[(.*?)\]\(.*?\)', r'\1', response.markdown)
        return cleaned_markdown
    except Exception as e:
        console.print(f"[bold red]Error during Firecrawl scrape:[/bold red] {e}")
        return ""
    
    
@function_tool
async def scrape_website_newspaper4k(url: str) -> Dict[str, Any]:
    """Scrapes a website using Newspaper4k.

    This function uses Newspaper4k to scrape a website and return its content.

    Args:
        url: The URL of the website to scrape. 

    Returns:
        A dictionary containing the raw scrape result from Newspaper4k.
    """
    console.print(f"Scraping with Newspaper4k: {url}")
    console.print(100*'-')
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        console.print(f"[bold red]Error during Newspaper4k scrape:[/bold red] {e}")
        return ""
    
@function_tool
async def scrape_website_Crawl4AI(url: str) -> Dict[str, Any]:
    """Scrapes a website using Crawl4AI.

    This function uses Crawl4AI to scrape a website and return its content.

    Args:
        url: The URL of the website to scrape. 

    Returns:
        A dictionary containing the raw scrape result from Crawl4AI.
    """
    console.print(f"Scraping with Crawl4AI: {url}")
    console.print(100*'-')  
    
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                url=url,
            )
            return result.markdown
    except Exception as e:
        console.print(f"[bold red]Error during Crawl4AI scrape:[/bold red] {e}")
        return ""
    