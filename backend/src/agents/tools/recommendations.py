"""
Recommendation engine for suggested readings and resources.
"""

from typing import List, Dict, Any, Optional


def generate_recommendations(
    topic: str,
    context: str = None,
    sources_used: List[Dict[str, Any]] = None,
    max_recommendations: int = 5
) -> str:
    """
    Generate recommended readings and resources based on the topic and context.
    
    Args:
        topic: The main topic or subject
        context: Optional context about what was discussed
        sources_used: Optional list of sources already used
        max_recommendations: Maximum number of recommendations to generate
        
    Returns:
        Formatted recommendations string
    """
    recommendations = []
    
    # Build recommendation suggestions based on topic
    base_recommendations = [
        {
            "type": "academic",
            "title": f"Academic research papers on {topic}",
            "suggestion": f"Search Google Scholar for recent peer-reviewed papers on '{topic}'",
            "url": f"https://scholar.google.com/scholar?q={topic.replace(' ', '+')}"
        },
        {
            "type": "industry",
            "title": f"Industry reports on {topic}",
            "suggestion": f"Look for industry reports from McKinsey, Deloitte, or Gartner on '{topic}'",
            "url": None
        },
        {
            "type": "news",
            "title": f"Recent news and developments",
            "suggestion": f"Follow news from industry publications and news sources for latest developments",
            "url": None
        }
    ]
    
    # Add specific recommendations based on context
    if context:
        if "financial" in context.lower() or "financial" in topic.lower():
            recommendations.append({
                "type": "financial",
                "title": "Financial Analysis Resources",
                "suggestion": "Review SEC filings, financial statements, and analyst reports",
                "url": None
            })
        
        if "market" in context.lower() or "market" in topic.lower():
            recommendations.append({
                "type": "market",
                "title": "Market Research Resources",
                "suggestion": "Explore market research from IBISWorld, Statista, or industry associations",
                "url": None
            })
        
        if "strategy" in context.lower() or "strategy" in topic.lower():
            recommendations.append({
                "type": "strategy",
                "title": "Strategic Planning Resources",
                "suggestion": "Read Harvard Business Review articles and case studies on strategic planning",
                "url": "https://hbr.org/topic/strategy"
            })
    
    # Combine base and context-specific recommendations
    all_recommendations = base_recommendations + recommendations
    
    # Limit to max_recommendations
    all_recommendations = all_recommendations[:max_recommendations]
    
    if not all_recommendations:
        return ""
    
    # Format recommendations as markdown links
    formatted = ["\n\n### Suggested Readings & Resources\n"]
    for i, rec in enumerate(all_recommendations, 1):
        if rec.get("url"):
            # Format as clickable markdown link
            formatted.append(f"{i}. [{rec['title']}]({rec['url']})\n")
            formatted.append(f"   {rec['suggestion']}\n\n")
        else:
            # No URL, just text
            formatted.append(f"{i}. **{rec['title']}**\n")
            formatted.append(f"   {rec['suggestion']}\n\n")
    
    return "".join(formatted)


def suggest_related_topics(topic: str, context: str = None) -> List[str]:
    """
    Suggest related topics for further exploration.
    
    Args:
        topic: The main topic
        context: Optional context
        
    Returns:
        List of related topic suggestions
    """
    related = []
    
    # Basic related topics based on common business domains
    if "market" in topic.lower():
        related.extend(["competitive analysis", "customer segmentation", "pricing strategy"])
    
    if "financial" in topic.lower():
        related.extend(["financial modeling", "investment analysis", "risk assessment"])
    
    if "strategy" in topic.lower():
        related.extend(["strategic planning", "business model", "competitive advantage"])
    
    if "customer" in topic.lower():
        related.extend(["customer journey", "user experience", "customer retention"])
    
    # Default suggestions
    if not related:
        related = [
            "market analysis",
            "competitive positioning",
            "strategic planning"
        ]
    
    return related[:5]  # Limit to 5 suggestions

