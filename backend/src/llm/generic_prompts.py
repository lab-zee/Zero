"""
Generic Q&A prompt system for general questions with organizational context.
Provides concise, helpful answers while maintaining guardrails.
"""
from typing import Optional

# Generic system prompt with guardrails
GENERIC_SYSTEM_PROMPT = """You are a helpful AI assistant that provides concise, accurate answers to questions. You have access to organizational context to provide relevant, personalized responses.

Guidelines:
1. **Be Concise**: Provide clear, direct answers without unnecessary elaboration
2. **Be Helpful**: Answer questions thoroughly but efficiently
3. **Data-Driven**: When discussing spending, investments, or resource allocation, include ROI analysis and measurement frameworks
4. **Stay On Topic**: Focus on the user's question and avoid tangents
5. **Use Context**: Reference organizational information when relevant to provide personalized answers
6. **Maintain Professionalism**: Keep responses professional and appropriate
7. **Ask for Clarification**: If a question is ambiguous, ask a brief clarifying question rather than guessing

Response Style:
- Provide direct answers to questions
- Use bullet points or numbered lists when helpful
- Keep responses focused and actionable
- Reference organizational context when it adds value
- If you don't know something, say so clearly

Remember: Your goal is to be helpful, accurate, and concise while leveraging organizational context when relevant."""

def build_generic_prompt(user_query: str, org_context: str, conversation_context: str, file_content: Optional[str] = None) -> list:
    """Build a generic Q&A prompt with organizational context."""
    content_parts = []
    
    # Include organization context (more concise than strategy mode)
    if org_context and org_context.strip():
        content_parts.append(f"""ORGANIZATION CONTEXT:
{org_context}""")
    
    # Include conversation history if available
    if conversation_context and conversation_context != "This is the start of a new conversation thread.":
        content_parts.append(f"""
CONVERSATION HISTORY:
{conversation_context}""")
    
    # Add file content if provided
    if file_content:
        if file_content.startswith("[Error:"):
            content_parts.append(f"""
NOTE: The user mentioned attached files, but there was an error extracting the content:
{file_content}

Please inform the user about this issue briefly.""")
        else:
            content_parts.append(f"""
ATTACHED FILE(S) CONTENT:
The user has attached file(s) with their query. Analyze the content below and use it to answer their question.

{file_content}""")
    
    # Build the user message
    content_parts.append(f"""
USER QUESTION:
{user_query}

Please provide a concise, helpful answer to the user's question. Use the organizational context and any attached files to provide relevant, personalized information.""")
    
    messages = [
        {"role": "system", "content": GENERIC_SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(content_parts)}
    ]
    return messages

