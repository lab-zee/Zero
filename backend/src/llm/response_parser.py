"""
Parse and structure LLM responses to identify clarifications vs. strategic guidance.
"""

import re
import json
from typing import Optional, Tuple, List, Dict, Any

def sanitize_hallucinated_images(text: str) -> str:
    """Remove hallucinated/malformed markdown image references from LLM output.

    LLMs sometimes generate fake image URLs (e.g. from files.oaiusercontent.com)
    with extremely long or repetitive signatures. This strips those out.
    """
    # Match markdown image syntax: ![alt](url)
    img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'

    def check_image(match):
        alt = match.group(1)
        url = match.group(2)
        # Reject URLs that are excessively long (hallucinated signatures)
        if len(url) > 500:
            return f'*[Image: {alt}]*' if alt else ''
        # Reject URLs from known external CDNs that the LLM hallucinates
        hallucinated_domains = [
            'files.oaiusercontent.com',
            'oaidalleapiprodscus.blob.core.windows.net',
        ]
        for domain in hallucinated_domains:
            if domain in url:
                return f'*[Image: {alt}]*' if alt else ''
        return match.group(0)

    return re.sub(img_pattern, check_image, text)


def parse_response(response_text: str) -> Tuple[str, bool, Optional[List[str]], Optional[List[Dict[str, Any]]], Optional[List[str]], Optional[List[Dict[str, Any]]]]:
    """
    Parse LLM response to extract structured information.

    Returns:
        Tuple of (cleaned_response, is_clarification, clarification_questions, citations, recommendations, visualizations)
    """
    response = sanitize_hallucinated_images(response_text.strip())
    is_clarification = False
    clarification_questions = None
    citations = None
    recommendations = None
    visualizations = None
    
    # Extract numbered inline citations (e.g., [1], [2], [3]) and References section
    # New format: Claims have [1], [2] citations, full details in References section

    # First, extract the References section
    references_pattern = r'##?\s*References\s*\n(.*?)(?=##|\n\n###|$)'
    references_match = re.search(references_pattern, response, re.DOTALL | re.IGNORECASE)

    citations = []
    if references_match:
        references_text = references_match.group(1)
        # Parse individual references like: [1] Author. (Year). "Title". URL
        reference_pattern = r'\[(\d+)\]\s*(.+?)(?=\n\[|\Z)'
        reference_matches = re.findall(reference_pattern, references_text, re.DOTALL)

        for num, ref_text in reference_matches:
            # Try to extract URL from reference
            url_pattern = r'https?://[^\s<>"\)]+[^\s<>"\)\.]'
            url_match = re.search(url_pattern, ref_text)
            url = url_match.group(0) if url_match else None

            # Clean up reference text (remove URL for title extraction)
            ref_clean = re.sub(url_pattern, '', ref_text).strip()

            # Try to extract author/org (text before year or first period)
            author_pattern = r'^([^.]+?)\.?\s*(?:\(\d{4}\)|$)'
            author_match = re.match(author_pattern, ref_clean)
            author = author_match.group(1).strip() if author_match else None

            # Try to extract year
            year_pattern = r'\((\d{4})\)'
            year_match = re.search(year_pattern, ref_text)
            date = year_match.group(1) if year_match else None

            # Try to extract title (text in quotes)
            title_pattern = r'["""\'](.*?)["""\']'
            title_match = re.search(title_pattern, ref_text)
            title = title_match.group(1) if title_match else ref_clean[:100]

            citations.append({
                "number": int(num),
                "type": "web",
                "url": url,
                "title": title,
                "author": author,
                "date": date,
                "description": ref_clean[:200]  # Include snippet for context
            })

    # Fallback: Also extract markdown links for backwards compatibility
    if not citations:
        markdown_link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        markdown_links = re.findall(markdown_link_pattern, response)

        if markdown_links:
            seen_urls = set()
            for title, url in markdown_links:
                if url and url not in seen_urls and url.startswith('http'):
                    seen_urls.add(url)
                    citations.append({
                        "type": "web",
                        "url": url,
                        "title": title,
                        "author": None,
                        "date": None
                    })
    
    # Recommendations are now included as markdown links in the response
    # Extract them from the "Suggested Readings & Resources" section if present
    recommendations_section = re.search(r'### Suggested Readings & Resources\n(.*?)(?=\n\n|$)', response, re.DOTALL)
    if recommendations_section:
        recommendations_text = recommendations_section.group(1)
        # Extract markdown links from recommendations
        rec_links = re.findall(markdown_link_pattern, recommendations_text)
        recommendations = [f"[{title}]({url})" if url.startswith('http') else title for title, url in rec_links]
    
    # Extract visualizations if present (ECharts JSON format)
    visualizations = extract_visualizations(response)
    if visualizations:
        # Remove visualization blocks from response
        for viz in visualizations:
            if viz.get('raw_text'):
                response = response.replace(viz['raw_text'], '')
            # Also remove the markers
            response = re.sub(r'\[VISUALIZATION_START\].*?\[VISUALIZATION_END\]', '', response, flags=re.DOTALL)

    # Safety net: remove any remaining ECharts-like JSON blocks that couldn't be parsed
    # This prevents raw JSON from showing up in the response text
    response = _strip_remaining_echarts_json(response)

    # Check if response contains clarification markers
    if "[CLARIFICATION NEEDED]" in response.upper() or "CLARIFICATION NEEDED" in response.upper():
        is_clarification = True
        clarification_questions = extract_clarification_questions(response)
    
    # Check for question patterns (heuristic fallback)
    if not is_clarification:
        question_count = count_questions(response)
        # If response has 1-3 questions and is relatively short, likely a clarification
        if question_count >= 1 and question_count <= 3 and len(response) < 500:
            is_clarification = True
            clarification_questions = extract_questions_from_text(response)
    
    return response, is_clarification, clarification_questions, citations, recommendations, visualizations

def extract_visualizations(response: str) -> Optional[List[Dict[str, Any]]]:
    """Extract ECharts visualization JSON from response text."""
    visualizations = []
    found_configs = set()  # Track found configs to avoid duplicates
    
    # First, look for visualization blocks wrapped in markers: [VISUALIZATION_START]... [VISUALIZATION_END]
    viz_pattern = r'\[VISUALIZATION_START\](.*?)\[VISUALIZATION_END\]'
    matches = re.finditer(viz_pattern, response, re.DOTALL)
    
    for match in matches:
        viz_content = match.group(1).strip()
        
        # Try to parse as ECharts JSON
        try:
            echarts_config = json.loads(viz_content)
            config_key = json.dumps(echarts_config, sort_keys=True)
            if config_key not in found_configs:
                found_configs.add(config_key)
                viz_data = _process_echarts_config(echarts_config)
                viz_data["raw_text"] = match.group(0)
                visualizations.append(viz_data)
        except json.JSONDecodeError:
            pass
    
    # Also look for JSON objects directly in the response that look like ECharts configs
    # Look for objects with series, xAxis, yAxis, or title properties
    # Use a more robust JSON extraction that properly handles nested objects and arrays
    # Try to find JSON objects that are likely ECharts configs (not tool arguments)
    
    # Method 1: Look for JSON objects that start with common ECharts properties
    # This helps avoid matching tool argument JSON which has "data", "chart_type", "title" as top-level keys
    echarts_start_patterns = [
        r'\{\s*"(?:title|series|xAxis|yAxis|legend|tooltip)"\s*:',  # Starts with ECharts-specific keys
    ]
    
    for pattern in echarts_start_patterns:
        matches = re.finditer(pattern, response, re.DOTALL)
        for match in matches:
            start_pos = match.start()
            # Try to extract the complete JSON object starting from this position
            try:
                # Find the matching closing brace by counting braces
                brace_count = 0
                in_string = False
                escape_next = False
                json_str = ""
                
                for i, char in enumerate(response[start_pos:], start_pos):
                    if escape_next:
                        escape_next = False
                        json_str += char
                        continue
                    
                    if char == '\\':
                        escape_next = True
                        json_str += char
                        continue
                    
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        json_str += char
                        continue
                    
                    json_str += char
                    
                    if not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                # Found complete JSON object
                                break
                
                if brace_count == 0 and json_str:
                    # Try strict parsing first, then clean up common LLM JSON issues
                    try:
                        config = json.loads(json_str)
                    except json.JSONDecodeError:
                        # Fix trailing commas before } or ] (common LLM output issue)
                        cleaned_json = re.sub(r',\s*([}\]])', r'\1', json_str)
                        config = json.loads(cleaned_json)

                    # Verify this is an ECharts config (not tool arguments)
                    # Tool arguments have "data", "chart_type" as top-level keys
                    # ECharts configs have "series", "xAxis", "yAxis", or nested "title" object
                    is_echarts_config = (
                        isinstance(config, dict) and
                        not ("data" in config and "chart_type" in config) and  # Not tool arguments
                        (
                            "series" in config or
                            "xAxis" in config or
                            "yAxis" in config or
                            ("title" in config and isinstance(config.get("title"), dict))
                        )
                    )

                    if is_echarts_config:
                        config_key = json.dumps(config, sort_keys=True)
                        if config_key not in found_configs:
                            found_configs.add(config_key)
                            viz_data = _process_echarts_config(config)
                            viz_data["raw_text"] = json_str
                            visualizations.append(viz_data)
            except (json.JSONDecodeError, ValueError, IndexError):
                continue
    
    return visualizations if visualizations else None

def _process_echarts_config(echarts_config: Dict[str, Any]) -> Dict[str, Any]:
    """Process an ECharts config dict to extract metadata."""
    # Extract title from config if available
    title = "Visualization"
    if isinstance(echarts_config, dict):
        if 'title' in echarts_config:
            if isinstance(echarts_config['title'], dict) and 'text' in echarts_config['title']:
                title = echarts_config['title']['text']
            elif isinstance(echarts_config['title'], str):
                title = echarts_config['title']
        
        # Determine chart type from series
        chart_type = "bar"  # default
        if 'series' in echarts_config and isinstance(echarts_config['series'], list) and len(echarts_config['series']) > 0:
            first_series = echarts_config['series'][0]
            if isinstance(first_series, dict) and 'type' in first_series:
                chart_type = first_series['type']
    
    return {
        "title": title,
        "chart_type": chart_type,
        "echarts_config": echarts_config  # Full ECharts option object
    }

def _strip_remaining_echarts_json(response: str) -> str:
    """Remove any remaining ECharts-like JSON blocks from response text.

    This is a safety net for cases where extract_visualizations couldn't parse the
    JSON (e.g. severely malformed) but we still don't want raw JSON shown to users.
    """
    echarts_pattern = r'\{\s*"(?:title|series|xAxis|yAxis|legend|tooltip)"\s*:'
    # Collect (start, end) ranges to remove, then process in reverse so positions stay valid
    ranges_to_remove = []
    for match in re.finditer(echarts_pattern, response):
        start_pos = match.start()
        brace_count = 0
        in_string = False
        escape_next = False
        end_pos = start_pos
        for i, char in enumerate(response[start_pos:], start_pos):
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i + 1
                        break
        if brace_count == 0 and end_pos > start_pos and (end_pos - start_pos) > 50:
            ranges_to_remove.append((start_pos, end_pos))
    # Remove in reverse order so earlier positions stay valid
    for start, end in reversed(ranges_to_remove):
        response = response[:start] + response[end:]
    # Clean up empty markdown code fences left behind
    response = re.sub(r'```(?:json|javascript)?\s*```', '', response)
    return response


def extract_clarification_questions(response: str) -> List[str]:
    """Extract numbered questions from structured clarification format."""
    questions = []
    
    # Look for numbered list pattern: "1. [question]" or "1) [question]"
    pattern = r'\d+[\.\)]\s*(.+?)(?=\n\d+[\.\)]|\n\n|$)'
    matches = re.findall(pattern, response, re.MULTILINE | re.DOTALL)
    
    if matches:
        questions = [match.strip() for match in matches if match.strip()]
    else:
        # Fallback: extract questions using question marks
        questions = extract_questions_from_text(response)
    
    return questions[:3]  # Limit to 3 questions

def extract_questions_from_text(text: str) -> List[str]:
    """Extract questions from text by finding sentences ending with '?'"""
    # Split by sentence endings
    sentences = re.split(r'[.!?]\s+', text)
    questions = [s.strip() + '?' for s in sentences if s.strip().endswith('?') or '?' in s]
    
    # Clean up questions
    cleaned_questions = []
    for q in questions:
        q = q.strip()
        if q and len(q) > 10:  # Filter out very short fragments
            cleaned_questions.append(q)
    
    return cleaned_questions[:3]  # Limit to 3 questions

def count_questions(text: str) -> int:
    """Count the number of questions in the text."""
    return text.count('?')

