"""
Structured citation extraction - returns JSON-serializable objects instead of formatted strings.
"""

import re
import json
from typing import List, Dict, Any, Optional


def extract_citations_structured(content: str, sources: List[Dict[str, Any]] = None) -> str:
    """
    Extract citations as structured objects (not formatted strings).
    
    Args:
        content: The content that may contain references, URLs, or [SOURCES_START] markers
        sources: Optional list of source dictionaries with keys like 'url', 'title', 'author', 'date'
        
    Returns:
        JSON string of citation dictionaries
    """
    citations = []
    seen_urls = set()
    
    # First, extract structured sources from [SOURCES_START] markers (from tool outputs)
    sources_pattern = r'\[SOURCES_START\](.*?)\[SOURCES_END\]'
    sources_matches = re.finditer(sources_pattern, content, re.DOTALL)
    for match in sources_matches:
        try:
            sources_json = match.group(1).strip()
            extracted_sources = json.loads(sources_json)
            if isinstance(extracted_sources, list):
                for source in extracted_sources:
                    if isinstance(source, dict) and source.get("url"):
                        url = source.get("url")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            citations.append({
                                "type": source.get("type", "web"),
                                "url": url,
                                "title": source.get("title"),
                                "author": source.get("author"),
                                "date": source.get("date"),
                                "source": source.get("source"),
                                "description": source.get("description")
                            })
        except (json.JSONDecodeError, ValueError):
            # If parsing fails, continue to other extraction methods
            pass
    
    # Extract URLs from content (fallback for URLs not in structured format)
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, content)
    
    for url in urls:
        if url not in seen_urls:
            seen_urls.add(url)
            citations.append({
                "type": "web",
                "url": url,
                "title": None,
                "author": None,
                "date": None,
                "source": None,
                "description": None
            })
    
    # Add provided sources parameter
    if sources:
        for source in sources:
            if isinstance(source, dict):
                citation = {
                    "type": source.get("type", "web"),
                    "url": source.get("url"),
                    "title": source.get("title"),
                    "author": source.get("author"),
                    "date": source.get("date"),
                    "source": source.get("source"),  # For news sources
                    "description": source.get("description")
                }
                # Only add if URL is unique
                if citation.get("url") and citation["url"] not in seen_urls:
                    seen_urls.add(citation["url"])
                    citations.append(citation)
    
    # Return as JSON string for agent to parse
    return json.dumps(citations, indent=2)

