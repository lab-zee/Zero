"""
Document search tool - searches uploaded documents.
"""

# This will be injected at runtime with access to the database
_document_search_func = None


def set_document_search_func(func):
    """Set the document search function (injected from main.py)."""
    global _document_search_func
    _document_search_func = func


def document_search(query: str, file_ids: list = None) -> str:
    """
    Search for information in uploaded documents.
    
    Args:
        query: What to search for
        file_ids: Optional list of specific file IDs to search
        
    Returns:
        Search results from documents
    """
    if _document_search_func is None:
        return "Error: Document search not available. No documents have been uploaded."
    
    try:
        return _document_search_func(query, file_ids)
    except Exception as e:
        return f"Error searching documents: {str(e)}"
