"""
Knowledge base search - semantic search across organization documents.
"""

# This will be injected at runtime
_knowledge_base_search_func = None


def set_knowledge_base_search_func(func):
    """Set the knowledge base search function (injected from main.py)."""
    global _knowledge_base_search_func
    _knowledge_base_search_func = func


def knowledge_base_search(query: str) -> str:
    """
    Perform semantic search across all organization documents.
    
    Args:
        query: Semantic search query
        
    Returns:
        Relevant information from the knowledge base
    """
    if _knowledge_base_search_func is None:
        return "Error: Knowledge base search not available. No documents in organization knowledge base."
    
    try:
        return _knowledge_base_search_func(query)
    except Exception as e:
        return f"Error searching knowledge base: {str(e)}"
