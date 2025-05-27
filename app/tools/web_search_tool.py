from duckduckgo_search import DDGS
from agents import function_tool
from typing import List, Dict, Optional
import dotenv
import os
from app.agents.common_imports import console
from asyncio_throttle import Throttler

dotenv.load_dotenv()

# Initialize a throttler to allow 1 request per second
throttler = Throttler(rate_limit=1, period=1.0)

@function_tool
async def perform_ddg_web_search(query: str, max_results: Optional[int] = None) -> List[Dict[str, str]]:
    """Asynchronously performs a web search using DuckDuckGo's text search.

    This function utilizes the `duckduckgo_search` library to fetch search results
    for a given query, specifically targeting the 'us-en' region. It is rate-limited.

    Args:
        query: The search query string to search for.
        max_results: Optional; The maximum number of search results to return.
                     If None or not provided, defaults to 5.

    Returns:
        A list of dictionaries, where each dictionary represents a search result.
        Each result typically contains keys like 'title', 'href' (URL), and
        'body' (snippet). Returns an empty list if the search fails or
        encounters an error.
    """
    async with throttler:
        actual_max_results = max_results if max_results is not None else 5
        console.print(f"Performing web search for: {query} (max_results={actual_max_results})")
        console.print(100*'-')
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=actual_max_results, timelimit="y", region=os.getenv("DDG_REGION")))
            # console.print(f"Web search results: {results}")
            return results
        except Exception as e:
            console.print(f"[bold red]Error during web search:[/bold red] {e}")
            return []