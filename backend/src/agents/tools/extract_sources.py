"""
Universal source extraction and citation tool.

Handles ALL types of sources:
- Internal documents (user-uploaded files)
- Web sources (news, reports, academic)
- Existing content (extract citations from agent outputs)
- Case studies with outcomes
- Data sources

This tool is context-aware and adapts to whatever content it receives.
"""

import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from ddgs import DDGS
except ImportError:
    DDGS = None


def extract_sources(
    content: str = None,
    search_query: str = None,
    file_context: List[Dict[str, Any]] = None,
    answer_mode: str = "light",
    include_case_studies: bool = False,
    max_sources: int = None
) -> str:
    """
    Universal source extraction and citation tool.

    Works in multiple modes:
    1. **Extract from content**: Parse existing content for URLs, citations, file references
    2. **Search for sources**: When content needs external backing (web, news, reports)
    3. **Reference files**: Cite internal documents the user provided
    4. **Find case studies**: Search for real-world examples with metrics

    Args:
        content: Existing content to extract citations from (optional)
        search_query: Topic to search for external sources (optional)
        file_context: List of file metadata dicts with {id, name, type, summary} (optional)
        answer_mode: "summary" (up to 3), "light" (up to 8), "extended" (up to 20), "project_plan" (up to 10), "roadmap" (up to 15)
        include_case_studies: Whether to find case studies with outcomes
        max_sources: Override default source count

    Returns:
        JSON with:
        {
            "citations": [
                {
                    "number": 1,
                    "type": "file|web|news|academic|industry_report|case_study|data",
                    "url": "...",
                    "title": "...",
                    "author": "...",
                    "date": "...",
                    "source": "...",
                    "description": "...",
                    "file_id": N  # If internal document
                },
                ...
            ],
            "case_studies": [...],
            "metadata": {...}
        }
    """

    # Determine source count targets based on answer mode (flexible, not rigid)
    # These are maximums to aim for - use fewer if quality sources aren't available
    if max_sources is None:
        source_targets = {
            "summary": 3,         # Executive Summary: Aim for 2-3 high-quality sources
            "light": 8,           # One-Pager/Memo: Aim for 5-8 sources
            "extended": 20,       # Executive Report: Aim for 10-20 comprehensive sources
            "project_plan": 10,   # 30-60-90 Plan: Aim for 8-10 actionable sources
            "roadmap": 15         # Framework/Roadmap: Aim for 12-15 strategic sources
        }
        max_sources = source_targets.get(answer_mode, 8)

    citations = []
    case_studies = []
    seen_urls = set()
    current_year = datetime.now().year

    # MODE 1: Extract citations from internal files
    if file_context:
        for file_data in file_context:
            file_id = file_data.get("id")
            file_name = file_data.get("name", "Untitled Document")
            file_type = file_data.get("type", "document")
            file_summary = file_data.get("summary", "")

            citations.append({
                "number": len(citations) + 1,
                "type": "file",
                "url": None,
                "title": file_name,
                "author": file_data.get("author"),
                "date": file_data.get("date"),
                "source": "Internal Document",
                "description": file_summary[:200] if file_summary else f"Internal {file_type}",
                "file_id": file_id
            })

    # MODE 2: Extract citations from existing content
    if content:
        # Extract URLs from content
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, content)

        for url in urls:
            if url not in seen_urls and len(citations) < max_sources:
                seen_urls.add(url)

                # Infer source type from URL
                source_type = _infer_source_type(url)

                # Try to extract title from surrounding context
                title = _extract_title_from_context(content, url)

                citations.append({
                    "number": len(citations) + 1,
                    "type": source_type,
                    "url": url,
                    "title": title or url,
                    "author": None,
                    "date": None,
                    "source": _extract_domain_name(url),
                    "description": None
                })

        # Extract structured citations from [SOURCES_START] markers
        sources_pattern = r'\[SOURCES_START\](.*?)\[SOURCES_END\]'
        sources_matches = re.finditer(sources_pattern, content, re.DOTALL)

        for match in sources_matches:
            try:
                sources_json = match.group(1).strip()
                extracted = json.loads(sources_json)

                if isinstance(extracted, list):
                    for source in extracted:
                        url = source.get("url")
                        if url and url not in seen_urls and len(citations) < max_sources:
                            seen_urls.add(url)
                            citations.append({
                                "number": len(citations) + 1,
                                "type": source.get("type", "web"),
                                "url": url,
                                "title": source.get("title"),
                                "author": source.get("author"),
                                "date": source.get("date"),
                                "source": source.get("source"),
                                "description": source.get("description")
                            })
            except (json.JSONDecodeError, ValueError):
                pass

    # MODE 3: Search for external sources (if search_query provided and not enough sources yet)
    if search_query and len(citations) < max_sources:
        if DDGS is None:
            return json.dumps({
                "error": "Cannot search external sources: ddgs package not installed",
                "citations": citations,
                "case_studies": case_studies,
                "metadata": {"source_count": len(citations)}
            })

        try:
            # Make query date-aware for time-sensitive topics
            enhanced_query = _make_query_date_aware(search_query, current_year)

            # Calculate how many more sources we need
            remaining = max_sources - len(citations)

            with DDGS() as ddgs:
                results = list(ddgs.text(enhanced_query, max_results=remaining))

                for result in results:
                    url = result.get('href', '')
                    if url and url not in seen_urls:
                        seen_urls.add(url)

                        title = result.get('title', 'Untitled')
                        body = result.get('body', '')
                        source_type = _infer_source_type(url)
                        author, source_name = _extract_author_source(title, url)

                        citations.append({
                            "number": len(citations) + 1,
                            "type": source_type,
                            "url": url,
                            "title": title,
                            "author": author,
                            "date": _extract_date(body, title) or str(current_year),
                            "source": source_name,
                            "description": body[:200]
                        })
        except Exception as e:
            # Continue with citations we already have
            pass

    # MODE 4: Find case studies (if requested) - include for all modes except summary
    if include_case_studies and search_query and answer_mode in ["light", "extended", "project_plan", "roadmap"]:
        case_studies = _search_case_studies(search_query, answer_mode, current_year)

    # Renumber all citations sequentially
    for idx, citation in enumerate(citations, 1):
        citation["number"] = idx

    return json.dumps({
        "citations": citations,
        "case_studies": case_studies,
        "metadata": {
            "query": search_query,
            "answer_mode": answer_mode,
            "source_count": len(citations),
            "case_study_count": len(case_studies),
            "has_internal_files": bool(file_context),
            "search_date": datetime.now().isoformat()
        }
    }, indent=2)


def _search_case_studies(query: str, answer_mode: str, current_year: int) -> List[Dict[str, Any]]:
    """Search for case studies with measurable outcomes."""
    if DDGS is None:
        return []

    case_studies = []
    case_count_map = {"light": 3, "extended": 5, "project_plan": 4, "roadmap": 5}
    case_count = case_count_map.get(answer_mode, 3)

    try:
        case_query = f"{query} case study success story {current_year}"

        with DDGS() as ddgs:
            results = list(ddgs.text(case_query, max_results=case_count))

            for result in results:
                title = result.get('title', '')
                url = result.get('href', '')
                body = result.get('body', '')

                case_studies.append({
                    "title": title,
                    "url": url,
                    "company": _extract_company_name(title, body),
                    "summary": body[:300],
                    "outcome": _extract_outcome(body),
                    "metrics": _extract_metrics(body)
                })
    except Exception:
        pass

    return case_studies


def _make_query_date_aware(query: str, current_year: int) -> str:
    """Add current year to time-sensitive queries."""
    time_sensitive = ["trend", "recent", "current", "latest", "report", "forecast", "outlook", "2026"]

    if any(keyword in query.lower() for keyword in time_sensitive):
        return f"{query} {current_year}"

    return query


def _infer_source_type(url: str) -> str:
    """Infer source type from URL domain."""
    url_lower = url.lower()

    if any(d in url_lower for d in ['.edu', 'scholar.google', 'arxiv', 'researchgate', 'jstor']):
        return "academic"

    if any(d in url_lower for d in ['mckinsey', 'bcg.com', 'bain', 'gartner', 'forrester', 'idc.com', 'statista']):
        return "industry_report"

    if any(d in url_lower for d in ['techcrunch', 'bloomberg', 'reuters', 'wsj', 'ft.com', 'forbes', 'cnbc']):
        return "news"

    if 'case-study' in url_lower or 'casestudy' in url_lower:
        return "case_study"

    return "web"


def _extract_domain_name(url: str) -> str:
    """Extract clean domain name from URL."""
    match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    if match:
        domain = match.group(1).split('.')[0]
        return domain.title()
    return "Unknown"


def _extract_title_from_context(content: str, url: str) -> Optional[str]:
    """Try to extract title from markdown link syntax around URL."""
    # Look for [Title](url) pattern
    pattern = rf'\[([^\]]+)\]\({re.escape(url)}\)'
    match = re.search(pattern, content)
    if match:
        return match.group(1)
    return None


def _extract_author_source(title: str, url: str) -> tuple:
    """Extract author and source from title or URL."""
    # Patterns: "Title - Author" or "Title | Source"
    if ' - ' in title:
        parts = title.split(' - ')
        if len(parts) >= 2:
            return parts[-1].strip(), parts[-1].strip()

    if ' | ' in title:
        parts = title.split(' | ')
        if len(parts) >= 2:
            return None, parts[-1].strip()

    return None, _extract_domain_name(url)


def _extract_date(body: str, title: str) -> Optional[str]:
    """Extract publication year."""
    year_pattern = r'\b(202[0-6])\b'

    match = re.search(year_pattern, title)
    if match:
        return match.group(1)

    match = re.search(year_pattern, body)
    if match:
        return match.group(1)

    return None


def _extract_company_name(title: str, body: str) -> Optional[str]:
    """Extract company name from case study."""
    # Pattern: "How [Company]..."
    match = re.search(r'How ([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)?)', title)
    if match:
        return match.group(1)

    # Pattern: Company name at start
    match = re.search(r'^([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)?)', title)
    if match:
        return match.group(1)

    return None


def _extract_outcome(body: str) -> Optional[str]:
    """Extract quantifiable outcome."""
    patterns = [
        r'(\d+%\s+(?:increase|growth|improvement|boost|reduction))',
        r'(increased.*?by\s+\d+%)',
        r'(reduced.*?by\s+\d+%)',
        r'(\d+x\s+(?:growth|increase))',
        r'(\$\d+[MBK]\s+(?:revenue|savings|increase))'
    ]

    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def _extract_metrics(body: str) -> List[str]:
    """Extract all metrics from text."""
    metrics = []

    # Percentages
    pct_matches = re.findall(r'\d+%', body)
    metrics.extend(pct_matches[:3])  # Max 3

    # Dollar amounts
    dollar_matches = re.findall(r'\$\d+(?:\.\d+)?[MBK]?', body)
    metrics.extend(dollar_matches[:2])  # Max 2

    # Multipliers
    mult_matches = re.findall(r'\d+x', body)
    metrics.extend(mult_matches[:2])  # Max 2

    return metrics[:5]  # Max 5 total


# Tool definition
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "extract_sources",
        "description": """Universal tool for extracting and citing sources from ANY content.

        Use this to:
        - Cite internal documents (files user uploaded)
        - Extract citations from existing content/analysis
        - Search for external sources (web, news, reports)
        - Find case studies with metrics
        - Back up claims with credible sources

        Works with:
        - User-uploaded files (PDFs, docs, spreadsheets)
        - Web sources (industry reports, news, academic)
        - Existing agent outputs (extract citations)
        - Case studies (real examples with outcomes)

        Adapts to answer_mode (targets, not rigid requirements):
        - summary: up to 3 high-quality sources
        - light: up to 8 sources
        - extended: up to 20 comprehensive sources

        Quality over quantity - use fewer if good sources aren't available.""",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Existing content to extract citations from (e.g., agent outputs, analysis results)"
                },
                "search_query": {
                    "type": "string",
                    "description": "Topic to search for external sources. Use when you need more sources beyond what's in content."
                },
                "file_context": {
                    "type": "array",
                    "description": "Internal files to cite. Array of {id, name, type, summary, author, date}",
                    "items": {"type": "object"}
                },
                "answer_mode": {
                    "type": "string",
                    "enum": ["summary", "light", "extended", "project_plan", "roadmap"],
                    "description": "Target source count (flexible): summary=up to 3, light=up to 8, extended=up to 20, project_plan=up to 10, roadmap=up to 15. Use fewer if quality sources unavailable.",
                    "default": "light"
                },
                "include_case_studies": {
                    "type": "boolean",
                    "description": "Whether to find case studies with measurable outcomes",
                    "default": False
                },
                "max_sources": {
                    "type": "integer",
                    "description": "Override default source count",
                    "minimum": 1,
                    "maximum": 30
                }
            },
            "required": []
        }
    }
}
