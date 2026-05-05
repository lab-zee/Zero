"""
Slash command parser for direct tool execution.
Bypasses the agentic crew when users explicitly request a tool via /toolname.
"""

import re
from typing import Optional, Dict, Any, Tuple


# Map tool names to their primary parameter name
TOOL_PRIMARY_PARAMS = {
    "web_search": "query",
    "news_search": "query",
    "calculator": "expression",
    "document": "query",
    "knowledge_base": "query",
    "swot": "data",
    "visualizer": "data",
    "extract_citations": "text",
    "extract_citations_structured": "text",
    "generate_recommendations": "context",
    "image_generator": "prompt",
    "validate_information_sufficiency": "query",
    "generate_followup_questions": "context",
    "scrape_website": "url",
}


def parse_slash_command(message: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Parse a slash command from a message.

    Format: /toolname arguments...
    Example: /web_search what is AI?

    Args:
        message: The message to parse

    Returns:
        Tuple of (tool_name, arguments) if valid slash command, None otherwise

    Example:
        >>> parse_slash_command("/web_search what is AI?")
        ("web_search", {"query": "what is AI?"})

        >>> parse_slash_command("/calculator 5 + 3 * 2")
        ("calculator", {"expression": "5 + 3 * 2"})

        >>> parse_slash_command("regular message")
        None
    """
    # Check if message starts with /
    if not message.strip().startswith('/'):
        return None

    # Extract tool name and arguments
    # Pattern: /toolname followed by optional whitespace and arguments
    match = re.match(r'^/(\w+)\s*(.*?)$', message.strip(), re.DOTALL)

    if not match:
        return None

    tool_name = match.group(1)
    args_text = match.group(2).strip()

    # Check if this is a known tool
    if tool_name not in TOOL_PRIMARY_PARAMS:
        return None

    # Get the primary parameter name for this tool
    primary_param = TOOL_PRIMARY_PARAMS[tool_name]

    # Build arguments dict
    arguments = {}

    # If there are arguments, add them to the primary parameter
    if args_text:
        arguments[primary_param] = args_text
    else:
        # Some tools might work without arguments, but most need them
        # Return empty dict and let the tool handle validation
        arguments[primary_param] = ""

    return tool_name, arguments


def is_slash_command(message: str) -> bool:
    """
    Check if a message is a valid slash command.

    Args:
        message: The message to check

    Returns:
        True if message is a valid slash command, False otherwise
    """
    return parse_slash_command(message) is not None
