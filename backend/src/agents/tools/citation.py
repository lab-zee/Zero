"""
Citation and source tracking tool.
Extracts and formats citations from research results.
"""

import re
from typing import List, Dict, Any


def extract_citations(content: str, sources: List[Dict[str, Any]] = None) -> str:
    """
    Extract and format citations from content and sources.
    
    Args:
        content: The content that may contain references
        sources: Optional list of source dictionaries with keys like 'url', 'title', 'author', 'date'
        
    Returns:
        Formatted citations string
    """
    citations = []
    
    # Extract URLs from content
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, content)
    
    # Add unique URLs as citations
    seen_urls = set()
    for url in urls:
        if url not in seen_urls:
            seen_urls.add(url)
            citations.append({
                "type": "web",
                "url": url,
                "title": None,
                "author": None,
                "date": None
            })
    
    # Add provided sources
    if sources:
        for source in sources:
            if isinstance(source, dict):
                citation = {
                    "type": source.get("type", "web"),
                    "url": source.get("url"),
                    "title": source.get("title"),
                    "author": source.get("author"),
                    "date": source.get("date"),
                    "source": source.get("source")  # For news sources
                }
                # Only add if URL is unique
                if citation.get("url") and citation["url"] not in seen_urls:
                    seen_urls.add(citation["url"])
                    citations.append(citation)
    
    if not citations:
        return "No citations found in the provided content."
    
    # Format citations
    formatted = ["## Sources & Citations\n"]
    for i, citation in enumerate(citations, 1):
        formatted.append(f"{i}. ")
        if citation.get("title"):
            formatted.append(f"**{citation['title']}**")
        if citation.get("author"):
            formatted.append(f" by {citation['author']}")
        if citation.get("source"):
            formatted.append(f" ({citation['source']})")
        if citation.get("date"):
            formatted.append(f" - {citation['date']}")
        if citation.get("url"):
            formatted.append(f"\n   URL: {citation['url']}")
        formatted.append("\n")
    
    return "".join(formatted)


def format_sources_for_response(sources: List[Dict[str, Any]]) -> str:
    """
    Format sources in a clean, readable format for inclusion in responses.
    
    Args:
        sources: List of source dictionaries
        
    Returns:
        Formatted sources string
    """
    if not sources:
        return ""
    
    formatted = ["\n\n### Sources\n"]
    for i, source in enumerate(sources, 1):
        formatted.append(f"{i}. ")
        if source.get("title"):
            formatted.append(f"{source['title']}")
        if source.get("url"):
            formatted.append(f" - {source['url']}")
        if source.get("date"):
            formatted.append(f" ({source['date']})")
        formatted.append("\n")
    
    return "".join(formatted)

