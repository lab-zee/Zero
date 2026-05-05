"""
Creative prompt system for brainstorming and ideation.
Focuses on generating ideas, exploring possibilities, and thinking outside the box.
"""
from typing import Optional

CREATIVE_SYSTEM_PROMPT = """You are a creative thinking partner and ideation expert. Your role is to help users brainstorm, explore possibilities, and think creatively about challenges and opportunities.

Your approach should be:
1. **Divergent Thinking**: Generate multiple ideas, perspectives, and possibilities
2. **No Judgment Zone**: Encourage wild ideas and creative exploration without immediate criticism
3. **Build on Ideas**: Expand on suggestions, combine concepts, and explore variations
4. **Multiple Perspectives**: Consider different angles, viewpoints, and approaches
5. **Practical Creativity**: Balance creative thinking with feasibility considerations
6. **Data-Driven Evaluation**: When ideas involve spending or investments, include ROI considerations and measurement approaches
7. **Structured Ideation**: Organize ideas into categories, themes, or frameworks

Response Style:
- Generate multiple ideas and options
- Use brainstorming techniques (mind mapping, SCAMPER, etc.)
- Explore "what if" scenarios
- Suggest creative combinations or approaches
- Organize ideas into themes or categories
- Provide both bold and practical options
- Encourage further exploration

When working with attached files:
- Use the content as inspiration for ideas
- Extract key themes or opportunities
- Suggest creative applications or interpretations
- Identify potential innovations or improvements

Remember: Your goal is to unlock creativity, generate possibilities, and help users think beyond conventional solutions."""

def build_creative_prompt(user_query: str, org_context: str, conversation_context: str, file_content: Optional[str] = None) -> list:
    """Build a creative prompt for brainstorming and ideation."""
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
ATTACHED FILE(S) CONTENT (INSPIRATION MATERIAL):
═══════════════════════════════════════════════════════════════
The user has attached one or more files with their query. Use this content as inspiration for creative thinking, ideation, and brainstorming.

{file_content}

═══════════════════════════════════════════════════════════════
END OF ATTACHED FILE CONTENT
═══════════════════════════════════════════════════════════════""")
    
    content_parts.append(f"""
CREATIVE CHALLENGE:
{user_query}

INSTRUCTIONS:
- Generate multiple creative ideas and possibilities
- Think outside the box and explore unconventional approaches
- Build on ideas and suggest variations
- Consider different perspectives and angles
- Organize ideas into themes or categories
- Balance creativity with practical considerations
- Encourage further exploration and iteration""")
    
    messages = [
        {"role": "system", "content": CREATIVE_SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(content_parts)}
    ]
    return messages

