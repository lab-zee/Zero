"""
Information Validator Tool - Checks if sufficient context exists to answer a query.

This tool helps prevent hallucination by identifying when critical information is missing
and generating specific clarification questions.
"""

from typing import Dict, Any, List


def validate_information_sufficiency(
    query: str,
    available_context: str,
    question_count: int = 0
) -> Dict[str, Any]:
    """
    Validate if there is sufficient information to answer the query.

    Args:
        query: The user's question
        available_context: Summary of available context (org info, conversation history, etc.)
        question_count: Number of clarification questions already asked (for progressive limit)

    Returns:
        {
            "sufficient": bool,
            "confidence": str ("high" | "medium" | "low"),
            "missing_info": List[str],
            "clarification_questions": List[str],
            "can_proceed": bool,
            "reasoning": str
        }
    """
    from ...llm_client import LLMClient

    # Progressive clarification limits
    MAX_QUESTIONS = 3
    INITIAL_QUESTIONS = 1

    # Determine how many questions to ask based on iteration
    if question_count >= MAX_QUESTIONS:
        # Hit limit - must proceed anyway
        return {
            "sufficient": True,  # Force to True to proceed
            "confidence": "low",
            "missing_info": [],
            "clarification_questions": [],
            "can_proceed": True,
            "reasoning": f"Maximum clarification attempts ({MAX_QUESTIONS}) reached. Proceeding with available information."
        }

    # Determine question limit for this iteration
    if question_count == 0:
        question_limit = INITIAL_QUESTIONS
    elif question_count == 1:
        question_limit = 2
    else:
        question_limit = 3

    prompt = f"""You are an information sufficiency validator. Analyze whether there is enough context to provide a high-quality, accurate answer to the user's query.

USER QUERY:
{query}

AVAILABLE CONTEXT:
{available_context}

CLARIFICATION HISTORY:
- Questions already asked: {question_count}
- Maximum allowed: {MAX_QUESTIONS}
- Questions to ask this round (if needed): {question_limit}

Your task:
1. Determine if the available context is SUFFICIENT to answer the query accurately and comprehensively
2. Identify what critical information is MISSING (if any)
3. Generate specific, targeted clarification questions (if needed)

IMPORTANT GUIDELINES:
- Only mark as INSUFFICIENT if critical information is truly MISSING
- Don't ask for "nice to have" information - only essentials
- Each clarification question should be specific and actionable
- If query is general/exploratory, context is usually sufficient
- If specific data/facts are requested but not available, ask for them
- If ambiguous terms need clarification, ask
- Progressive questioning: Start with most critical question first

Examples of when to ask:
- "What's our market share?" → NEED: Which market? Which product?
- "Should we expand to Asia?" → NEED: Which country? What's the business/product?
- "Analyze our competitor" → NEED: Which competitor?

Examples when NOT to ask:
- "What are market trends in tech?" → SUFFICIENT (general, can research)
- "How do we improve customer retention?" → SUFFICIENT (general strategy question)
- "What's the best pricing model?" → SUFFICIENT (can provide frameworks)

Respond in this EXACT JSON format:
{{
    "sufficient": true/false,
    "confidence": "high" | "medium" | "low",
    "missing_info": ["specific missing item 1", "specific missing item 2"],
    "clarification_questions": ["specific question 1", "specific question 2"],
    "can_proceed": true/false,
    "reasoning": "brief explanation of your assessment"
}}

If sufficient=true, clarification_questions should be empty.
If sufficient=false, provide {question_limit} specific clarification question(s).
"""

    try:
        client = LLMClient(model="gpt-4o-mini")  # Use fast, cheap model for validation
        response = client.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        import json
        result = json.loads(response)

        # Ensure can_proceed is set correctly
        if question_count >= MAX_QUESTIONS:
            result["can_proceed"] = True
            result["sufficient"] = True
        else:
            result["can_proceed"] = result.get("sufficient", True)

        return result

    except Exception as e:
        # On error, default to proceeding
        return {
            "sufficient": True,
            "confidence": "medium",
            "missing_info": [],
            "clarification_questions": [],
            "can_proceed": True,
            "reasoning": f"Validation error: {str(e)}. Proceeding with available context."
        }


# Tool definition for agent registry
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "validate_information_sufficiency",
        "description": "Check if there is sufficient information to answer the user's query accurately. Use this BEFORE delegating to specialists to avoid hallucination. Returns clarification questions if critical information is missing.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The user's original query/question"
                },
                "available_context": {
                    "type": "string",
                    "description": "Summary of available context: organization info, conversation history, user preferences, etc. Be specific about what you know."
                },
                "question_count": {
                    "type": "integer",
                    "description": "Number of clarification questions already asked (0 for first check)",
                    "default": 0
                }
            },
            "required": ["query", "available_context"]
        }
    }
}
