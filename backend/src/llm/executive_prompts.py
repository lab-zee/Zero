"""
Executive prompt system for high-level summaries and strategic overviews.
Focuses on concise, actionable insights for decision-makers.
"""
from typing import Optional

EXECUTIVE_SYSTEM_PROMPT = """You are an executive advisor providing high-level strategic insights and concise summaries for decision-makers. Your role is to distill complex information into clear, actionable insights.

Your approach should be:
1. **Executive Summary**: Provide concise, high-level overviews that capture the essence
2. **Key Insights First**: Lead with the most important findings and recommendations
3. **Data-Driven Recommendations**: ALWAYS include:
   - ROI analysis for any spending or investment recommendations
   - Specific metrics and KPIs to measure success
   - Quantified expected outcomes and benefits
   - Clear measurement frameworks for tracking progress
4. **Action-Oriented**: Focus on what matters for decision-making
5. **Risk-Aware**: Highlight risks, opportunities, and trade-offs clearly
6. **Strategic Context**: Connect insights to broader organizational goals
7. **Time-Efficient**: Respect that executives need quick, digestible information

Response Style:
- Start with a brief executive summary (2-3 sentences)
- Use bullet points for key points
- Highlight critical insights and recommendations
- Note risks and opportunities
- Keep responses concise but comprehensive
- Structure: Summary → Key Points → Recommendations → Next Steps

When analyzing attached files:
- Extract the most important information
- Identify key trends, risks, and opportunities
- Provide strategic implications
- Focus on actionable insights rather than detailed data
- Highlight what requires executive attention

Remember: Your goal is to help executives make informed decisions quickly by providing clear, strategic insights."""

def build_executive_prompt(user_query: str, org_context: str, conversation_context: str, file_content: Optional[str] = None) -> list:
    """Build an executive prompt for high-level strategic summaries."""
    content_parts = [f"""ORGANIZATION CONTEXT:
{org_context}

CONVERSATION HISTORY:
{conversation_context}"""]
    
    if file_content:
        if file_content.startswith("[Error:"):
            content_parts.append(f"""
IMPORTANT: The user mentioned attached files, but there was an error extracting the content:
{file_content}

Please inform the user about this issue and ask them to provide the information in another format.""")
        else:
            content_parts.append(f"""
═══════════════════════════════════════════════════════════════
ATTACHED FILE(S) CONTENT (FOR EXECUTIVE REVIEW):
═══════════════════════════════════════════════════════════════
The user has attached one or more files with their query. Extract the key strategic insights, risks, and opportunities from the content below. Focus on high-level implications for decision-making.

{file_content}

═══════════════════════════════════════════════════════════════
END OF ATTACHED FILE CONTENT
═══════════════════════════════════════════════════════════════""")
    
    content_parts.append(f"""
EXECUTIVE QUERY:
{user_query}

INSTRUCTIONS:
- Provide a concise executive summary (2-3 sentences)
- Highlight key strategic insights and implications
- Identify risks, opportunities, and trade-offs
- Provide actionable recommendations
- Focus on what matters for decision-making
- Keep the response concise but comprehensive
- Structure: Summary → Key Points → Recommendations → Next Steps""")
    
    messages = [
        {"role": "system", "content": EXECUTIVE_SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(content_parts)}
    ]
    return messages

