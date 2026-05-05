"""
SWOT analysis generator tool.
"""


def generate_swot(context: str, focus_area: str = None) -> str:
    """
    Generate a structured SWOT analysis.
    
    Args:
        context: The context or information to analyze
        focus_area: Optional specific area to focus on
        
    Returns:
        Structured SWOT analysis
    """
    focus_text = f" for {focus_area}" if focus_area else ""
    
    swot_template = f"""SWOT Analysis{focus_text}:

STRENGTHS:
- [Analyze internal positive attributes, resources, capabilities]

WEAKNESSES:
- [Analyze internal limitations, gaps, areas for improvement]

OPPORTUNITIES:
- [Analyze external positive factors, market trends, potential growth areas]

THREATS:
- [Analyze external challenges, competition, market risks]

Based on the provided context:
{context[:500]}{'...' if len(context) > 500 else ''}

Note: This is a template. The actual SWOT should be filled in based on detailed analysis of the context provided."""
    
    return swot_template
