"""
Strategy-focused prompt system for organizational strategy assistance.
This acts as "cursor for strategy" - powerful prompt instructions on top of a foundational model.
"""
from typing import Optional

# Base strategy system prompt
STRATEGY_SYSTEM_PROMPT = """You are an expert strategic advisor helping organizations achieve their goals. Your role is to act as a "cursor for strategy" - providing powerful, actionable strategic guidance.

Your approach should be:
1. **Question First, Answer Second**: When you have doubts or gaps in understanding, ask clarifying questions rather than making assumptions. It's better to ask 3 good questions than to guess incorrectly.

2. **Context-Aware**: You have access to the organization's:
   - Purpose and goals
   - Current limitations
   - Available resources
   - Industry and organizational type
   - Previous conversation context

3. **Data-Driven Approach**: ALWAYS prioritize data-driven recommendations:
   - Base all recommendations on measurable data, metrics, and evidence
   - When discussing spending, investments, or resource allocation, ALWAYS include ROI (Return on Investment) analysis
   - Provide specific metrics, KPIs, and measurement frameworks for every recommendation
   - Quantify expected outcomes, costs, and benefits wherever possible
   - Use benchmarks, industry standards, and comparative data to support recommendations
   - If data is missing, explicitly state what metrics need to be tracked and how to measure success

4. **Strategic Thinking**: Help the user think strategically by:
   - Breaking down complex goals into actionable steps
   - Identifying dependencies and prerequisites
   - Considering resource constraints
   - Anticipating potential obstacles
   - Suggesting measurable milestones with clear success metrics

4. **Clarification Protocol**: Before providing strategic recommendations, ensure you understand:
   - The specific goal or challenge
   - Current state vs. desired state
   - Available resources and constraints
   - Timeline and priorities
   - Success criteria

5. **Response Format**: 
   - If you need clarification, ask 1-3 specific questions
   - If you have sufficient context, provide strategic guidance
   - Always reference relevant organization context when applicable
   - Structure your response clearly with actionable steps

6. **Structured Clarification Format**: When asking clarifying questions, use this format:
   ```
   [CLARIFICATION NEEDED]
   
   To provide the best strategic guidance, I need to understand:
   1. [First question]
   2. [Second question] (if needed)
   3. [Third question] (if needed)
   
   [Optional: Brief explanation of why these questions matter]
   ```

7. **Structured Strategic Response Format**: When providing strategic guidance, use this format:
   ```
   [STRATEGIC GUIDANCE]
   
   Based on your organization's context, here's my strategic recommendation:
   
   **Goal/Challenge**: [Summary]
   **Current State**: [What you understand]
   **Recommended Approach**: 
   1. [First actionable step]
   2. [Second actionable step]
   3. [Third actionable step]
   
   **Considerations**: [Important factors to keep in mind]
   **Next Steps**: [What to do next]
   ```

Remember: Your goal is to help the organization achieve their objectives through thoughtful, strategic guidance. When in doubt, ask questions."""

# Function to build organization context
def build_organization_context(org, org_metadata=None):
    """Build a comprehensive context string about the organization."""
    context_parts = []
    
    context_parts.append(f"Organization: {org.name}")
    if org.description:
        context_parts.append(f"Description: {org.description}")
    
    if org_metadata:
        if org_metadata.get('industry_name'):
            context_parts.append(f"Industry: {org_metadata.get('industry_name')}")
        if org_metadata.get('org_type'):
            context_parts.append(f"Organization Type: {org_metadata.get('org_type')}")
        if org_metadata.get('purpose'):
            context_parts.append(f"Purpose: {org_metadata.get('purpose')}")
        if org_metadata.get('goals_missions'):
            context_parts.append(f"Goals & Missions: {org_metadata.get('goals_missions')}")
        if org_metadata.get('current_limitations'):
            context_parts.append(f"Current Limitations: {org_metadata.get('current_limitations')}")
        if org_metadata.get('resources_available'):
            context_parts.append(f"Resources Available: {org_metadata.get('resources_available')}")
    
    return "\n".join(context_parts)

# Function to build conversation context
def build_conversation_context(previous_queries):
    """Build context from previous messages in the thread."""
    if not previous_queries:
        return "This is the start of a new conversation thread."
    
    context_parts = ["Previous conversation:"]
    for query in previous_queries[-10:]:  # Last 10 messages for context
        context_parts.append(f"User: {query.message}")
        if query.response:
            context_parts.append(f"Assistant: {query.response}")
    
    return "\n".join(context_parts)

# Function to build the full prompt
def build_strategy_prompt(user_query: str, org_context: str, conversation_context: str, file_content: Optional[str] = None) -> list:
    """Build the complete prompt for the LLM."""
    content_parts = [f"""ORGANIZATION CONTEXT:
{org_context}

CONVERSATION HISTORY:
{conversation_context}"""]
    
    # Add file content if provided - make it very explicit
    if file_content:
        # Check if file_content is an error message
        if file_content.startswith("[Error:"):
            content_parts.append(f"""
IMPORTANT: The user mentioned attached files, but there was an error extracting the content:
{file_content}

Please inform the user about this issue and ask them to provide the information in another format.""")
        else:
            content_parts.append(f"""
═══════════════════════════════════════════════════════════════
ATTACHED FILE(S) CONTENT (EXTRACTED TEXT):
═══════════════════════════════════════════════════════════════
The user has attached one or more files with their query. The extracted text content from these files is provided below. You MUST analyze this content and use it to answer their question.

{file_content}

═══════════════════════════════════════════════════════════════
END OF ATTACHED FILE CONTENT
═══════════════════════════════════════════════════════════════""")
    
    content_parts.append(f"""
CURRENT QUERY:
{user_query}

INSTRUCTIONS:
- The user's query is above. {'**IMPORTANT: The user has attached file(s) with this query. The file content has been extracted and provided above. You MUST analyze the attached file content and use it to answer their question.**' if file_content and not file_content.startswith('[Error:') else ''}
- Provide strategic guidance based on the organization context, conversation history, {'and the attached file content' if file_content and not file_content.startswith('[Error:') else ''}.
- If you have sufficient context, provide actionable strategic recommendations.
- If you need clarification, ask specific questions.""")
    
    messages = [
        {"role": "system", "content": STRATEGY_SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(content_parts)}
    ]
    return messages

