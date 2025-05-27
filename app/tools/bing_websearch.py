from datetime import datetime, timedelta
import os
import requests
from typing import List, Dict, Optional
from agents import function_tool
import dotenv
from app.agents.common_imports import console

dotenv.load_dotenv()

@function_tool
async def perform_bing_web_search(query: str, mkt: str, max_results: Optional[int] = None) -> List[Dict[str, str]]:
    """Asynchronously performs a web search using Bing's Web Search API.

    This function utilizes the Bing Web Search API to fetch search results
    for a given query. The API requires a subscription key and endpoint
    to be set in the environment variables.

    Args:
        query: The search query string to search for.
        mkt: The market to search in. Could also be other markets like 'hu-HU', 'en-GB', 'de-DE', 'fr-FR', etc.
        max_results: Optional; The maximum number of search results to return.
                     If None or not provided, defaults to 5.
    Returns:
        A list of dictionaries, where each dictionary represents a search result.
        Each result contains 'title', 'href' (URL), and 'body' (snippet).
        Returns an empty list if the search fails or encounters an error.
    """
    actual_max_results = max_results if max_results is not None else 3
    console.print(f"Performing Bing web search for: {query} (max_results={actual_max_results})")
    console.print(100*'-')

    try:
        subscription_key = os.getenv('BING_SEARCH_V7_SUBSCRIPTION_KEY')
        endpoint = os.getenv('BING_SEARCH_V7_ENDPOINT') + "v7.0/search"

        if not subscription_key or not endpoint:
            raise ValueError("Bing Search API credentials not found in environment variables")
        
        if mkt == "":
            mkt = 'en-US'
        console.print(f"Using {mkt} market for Bing web search")
        params = {
            'q': query,
            'mkt': mkt,
            'count': actual_max_results
        }
        
        # search in last 365 days 
        today = datetime.now().date()
        past_date = today - timedelta(days=365)
        params['freshness'] = f"{past_date.strftime('%Y-%m-%d')}..{today.strftime('%Y-%m-%d')}"
        
        console.print(f"Using freshness for Bing web search: {params['freshness']}")
            
        headers = {'Ocp-Apim-Subscription-Key': subscription_key}

        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()
        
        results = []
        search_results = response.json()
        
        if 'webPages' in search_results and 'value' in search_results['webPages']:
            for item in search_results['webPages']['value']:
                results.append({
                    'title': item.get('name', ''),
                    'href': item.get('url', ''),
                    'body': item.get('snippet', '')
                })

        return results

    except Exception as e:
        console.print(f"[bold red]Error during Bing web search:[/bold red] {e}")
        return [] 