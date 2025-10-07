from typing import List, Dict, Any
import requests
import os
from dotenv import load_dotenv

load_dotenv()

class WebSearch:
    def __init__(self):
        # Using Tavily AI - FREE tier: 1000 requests/month, NO credit card required!
        self.api_key = os.getenv('TAVILY_API_KEY', '')
        self.enabled = bool(self.api_key)
        self.base_url = "https://api.tavily.com/search"

    async def search_web_sources(self, queries: List[str], max_results: int = 5) -> List[Dict[str, Any]]:
        """Search web using Tavily AI API (FREE, no credit card needed!)"""

        if not self.enabled:
            print("WARNING: Tavily API key not found. Set TAVILY_API_KEY in .env")
            print("Get FREE API key (no credit card): https://app.tavily.com/")
            return []

        all_results = []

        for query in queries:
            try:
                payload = {
                    "api_key": self.api_key,
                    "query": query,
                    "search_depth": "advanced",  # Use advanced for more current results
                    "include_answer": True,
                    "max_results": max_results,
                    "include_raw_content": False,
                    "include_images": False
                }

                print(f"DEBUG: Tavily Search query: {query}")

                response = requests.post(
                    self.base_url,
                    json=payload,
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()

                    # Extract results
                    results = data.get('results', [])
                    answer = data.get('answer', '')

                    print(f"DEBUG: Tavily found {len(results)} results")
                    if answer:
                        print(f"DEBUG: Tavily answer: {answer[:100]}...")

                    # Add the AI-generated answer as the first result if available
                    if answer:
                        all_results.append({
                            'query': query,
                            'title': 'AI Summary',
                            'url': '',
                            'content': answer,
                            'score': 2.0  # Higher score for AI answer
                        })

                    for result in results[:max_results]:
                        all_results.append({
                            'query': query,
                            'title': result.get('title', 'No title'),
                            'url': result.get('url', ''),
                            'content': result.get('content', ''),
                            'score': result.get('score', 1.0)
                        })
                        print(f"  - {result.get('title', '')[:60]}")

                elif response.status_code == 401:
                    print("ERROR: Tavily API key is invalid")
                else:
                    print(f"ERROR: Tavily API returned status {response.status_code}: {response.text}")

            except Exception as e:
                print(f"Web search error for '{query}': {e}")
                continue

        return all_results

# Global instance
web_search = WebSearch()

async def search_web_sources(queries: List[str], max_results: int = 3) -> List[Dict[str, Any]]:
    return await web_search.search_web_sources(queries, max_results)
