"""
News search tool using DuckDuckGo.
"""

import json
try:
    from ddgs import DDGS
except ImportError:
    DDGS = None


def news_search(query: str, max_results: int = 5) -> str:
    """
    Search for recent news using DuckDuckGo.
    
    Args:
        query: News search query
        max_results: Maximum number of results to return
        
    Returns:
        Formatted news results as a string with structured source data for citations
    """
    if DDGS is None:
        return "Error: ddgs package not installed. Please install it with: pip install ddgs"
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=max_results))
            
            if not results:
                return f"No news found for query: {query}"
            
            formatted_results = []
            
            for i, result in enumerate(results, 1):
                title = result.get('title', 'No title')
                source = result.get('source', 'Unknown')
                date = result.get('date', 'Unknown')
                url = result.get('url', '')
                body = result.get('body', 'No description')
                
                # Format as markdown with clickable link
                formatted_results.append(
                    f"{i}. [{title}]({url})\n"
                    f"   Source: {source} | Date: {date}\n"
                    f"   {body}\n"
                )
            
            return "\n".join(formatted_results)
    except Exception as e:
        return f"Error performing news search: {str(e)}"
