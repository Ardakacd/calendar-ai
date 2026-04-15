"""
Internet Search Tool — Tavily

Used by the Leisure Search Agent to find external events, activities,
concerts, sports games, and other real-world information.
"""

from langchain_community.tools.tavily_search import TavilySearchResults
from config import settings


def internet_search_tool_factory() -> TavilySearchResults:
    """
    Create a Tavily search tool instance.

    Requires TAVILY_API_KEY in environment / .env file.
    Free tier: 1000 searches / month — https://tavily.com
    """
    return TavilySearchResults(
        max_results=5,
        include_answer=True,          # Tavily generates a short direct answer on top
        include_raw_content=True,     # full page content — needed to extract exact times
        tavily_api_key=settings.TAVILY_API_KEY,
    )
