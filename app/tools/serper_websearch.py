import requests
import json
import os
import dotenv
from agents import function_tool
from typing import List, Dict, Optional, Any
import httpx
from app.agents.common_imports import console

dotenv.load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
if not SERPER_API_KEY:
    raise ValueError("SERPER_API_KEY environment variable not set.")

@function_tool
async def perform_serper_web_search(
    query: str,
    location: Optional[str] = None,
    gl: Optional[str] = None,
    hl: Optional[str] = None,
    tbs: Optional[str] = None,
    num_results: Optional[int] = None,
) -> List[Dict[str, str]]:
    """Asynchronously performs a web search using the Serper Google Search API
    and returns a list of organic results.

    Args:
        query: The search query string.
        location: Optional; The location for the search (e.g., "United States"). Defaults to "United States".
        gl: Optional; The country code for the search (e.g., "us"). Defaults to "us".
        hl: Optional; The language code for the search (e.g., "en"). Defaults to "en".
        tbs: Optional; Time-based search filter (e.g., "qdr:y" for past year). Defaults to "qdr:y".
        num_results: Optional; The number of search results to request. Defaults to 10.

    Returns:
        A list of dictionaries, where each dictionary represents an organic search result
        containing 'title', 'href' (URL), and 'body' (snippet). Returns an empty
        list if the search fails, encounters an error, or returns no organic results.
    """
    # Assign default values if arguments are None
    loc = location if location is not None else "United States"
    g_lang = gl if gl is not None else "us"
    h_lang = hl if hl is not None else "en"
    time_based_search = tbs if tbs is not None else "qdr:y"
    num = num_results if num_results is not None else 2

    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": query,
        "location": loc,
        "gl": g_lang,
        "hl": h_lang,
        "tbs": time_based_search,
        "num": num
    })
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }

    console.print(f"Performing Serper web search for: {query} (location={loc}, gl={g_lang}, hl={h_lang}, tbs={time_based_search}, num={num})")
    console.print(100*'-')

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, content=payload)
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            results_data = response.json()
            # console.print(f"Raw Serper search results: {results_data}")

            # Extract and reformat organic results
            organic_results = results_data.get("organic", [])
            formatted_results = [
                {
                    "title": item.get("title", ""),
                    "href": item.get("link", ""),
                    "body": item.get("snippet", "")
                }
                for item in organic_results
                if item.get("link") # Ensure there's a link
            ]
            # console.print(f"Formatted Serper results: {formatted_results}")
            return formatted_results
    except httpx.RequestError as e:
        console.print(f"[bold red]Error during Serper web search (Request Error):[/bold red] {e}")
        return []
    except httpx.HTTPStatusError as e:
        console.print(f"[bold red]Error during Serper web search (HTTP Status Error):[/bold red] {e.response.status_code} - {e.response.text}")
        return []
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred during Serper web search:[/bold red] {e}")
        return []

# Example usage (for testing)
# if __name__ == "__main__":
#     import asyncio
#     async def main():
#         results = await perform_serper_web_search("hentes fizetés Magyarország")
#         console.print(json.dumps(results, indent=2, ensure_ascii=False))
#     asyncio.run(main())