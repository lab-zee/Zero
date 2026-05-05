"""
Follow-up Question Generator Tool - Generates relevant follow-up questions based on the answer.

Generates two categories of follow-up questions:
- "related": Broader questions exploring adjacent topics or new angles
- "deep_dive": Questions that build on specific analysis findings and benefit from full parent context
"""

from typing import Dict, Any, List


def generate_followup_questions(
    original_question: str,
    answer: str,
    org_context: str = "",
    execution_summary: str = ""
) -> List[Dict[str, str]]:
    """
    Generate 3-5 relevant follow-up questions based on the answer.

    Args:
        original_question: The user's original query
        answer: The complete answer that was provided
        org_context: Organization context (industry, goals, etc.)
        execution_summary: Summary of agents/tools used and key findings from execution trace

    Returns:
        [
            {"question": str, "rationale": str, "type": "related" | "deep_dive"},
            ...
        ]
    """
    from ...llm_client import get_llm_client

    # Build the execution context section
    execution_section = ""
    if execution_summary:
        execution_section = f"""
ANALYSIS PROCESS (specialists and tools used to generate the answer):
{execution_summary}
"""

    prompt = f"""You are a domain expert generating follow-up questions for a strategic analysis platform. Based on the question asked, the answer provided, and the analysis process used to generate it, create 4-5 highly specific follow-up questions.

ORIGINAL QUESTION:
{original_question}

ANSWER PROVIDED:
{answer[:4000]}{"..." if len(answer) > 4000 else ""}

ORGANIZATION CONTEXT:
{org_context}
{execution_section}
Generate two categories of follow-up questions:

**RELATED QUESTIONS (2-3 questions, type "related"):**
Broader questions that explore adjacent topics, new angles, or complementary areas not covered in the answer. These are standalone questions that don't require knowledge of the analysis process.

**DEEP DIVE FOLLOW-UPS (2 questions, type "deep_dive"):**
Questions that specifically build on the analysis that was performed — referencing specific findings, data points, agent insights, or tool results from the analysis process. These questions would benefit from having the full analysis context when answered. If an analysis process summary is provided above, reference specific specialist findings or tool outputs.

CRITICAL REQUIREMENTS:
- Each question MUST reference SPECIFIC concepts, data points, frameworks, or findings from the answer — not generic advice
- Use terminology and concepts appropriate to the organization's domain and industry
- Avoid generic questions like "What are the next steps?" or "What challenges might we face?"
- Questions should be concise but information-dense (15-25 words)
- Deep dive questions should explicitly build on specific parts of the answer or analysis (e.g., "Given the competitive analysis found X, how should we...")
- Related questions should open new but relevant avenues of inquiry

Examples of POOR questions (too generic — avoid these):
- "What are the next steps to move forward with this?"
- "What challenges might we face implementing this?"
- "How does this align with our current priorities?"
- "Can you tell me more about this approach?"

Respond in this EXACT JSON format:
{{
    "followup_questions": [
        {{
            "question": "Specific question referencing concrete details from the answer",
            "rationale": "Why this question matters for decision-making",
            "type": "related"
        }},
        {{
            "question": "Deep dive question building on specific analysis findings",
            "rationale": "Why exploring this deeper is valuable",
            "type": "deep_dive"
        }}
    ]
}}

Generate 4-5 questions total: 2-3 related + 2 deep_dive. Each must be unique, domain-specific, and could NOT be asked without having seen this specific answer.
"""

    try:
        client = get_llm_client("gpt-4o-mini")
        response = client.chat_completions_create(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        import json
        result = json.loads(response.choices[0].message.content)

        questions = result.get("followup_questions", [])

        # Validate and ensure type field exists on each question
        for q in questions:
            if "type" not in q or q["type"] not in ("related", "deep_dive"):
                q["type"] = "related"

        if len(questions) < 3:
            return _get_fallback_questions(org_context)

        return questions[:5]

    except Exception as e:
        return _get_fallback_questions(org_context)


def _get_fallback_questions(org_context: str = "") -> List[Dict[str, str]]:
    """Return domain-aware fallback questions when generation fails."""
    # Try to extract industry/domain from org_context for slightly better fallbacks
    context_lower = org_context.lower() if org_context else ""

    # Default fallbacks that are still useful
    return [
        {
            "question": "What specific metrics should we track to measure the impact of this approach on our key objectives?",
            "rationale": "Quantifiable metrics enable data-driven iteration and course correction",
            "type": "related"
        },
        {
            "question": "How should we phase the implementation to minimize risk while capturing early wins?",
            "rationale": "Phased rollout reduces execution risk and builds organizational confidence",
            "type": "related"
        },
        {
            "question": "Which findings from this analysis should we stress-test with additional data before committing resources?",
            "rationale": "Validating key assumptions prevents costly missteps",
            "type": "deep_dive"
        }
    ]


# Tool definition for agent registry
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "generate_followup_questions",
        "description": "Generate relevant follow-up questions based on the answer provided. Use this after completing an answer to help guide the user's next inquiry.",
        "parameters": {
            "type": "object",
            "properties": {
                "original_question": {
                    "type": "string",
                    "description": "The user's original query/question"
                },
                "answer": {
                    "type": "string",
                    "description": "The complete answer that was provided to the user"
                },
                "org_context": {
                    "type": "string",
                    "description": "Organization context (industry, goals, challenges, etc.)",
                    "default": ""
                },
                "execution_summary": {
                    "type": "string",
                    "description": "Summary of the analysis process (agents consulted, tools used, key findings)",
                    "default": ""
                }
            },
            "required": ["original_question", "answer"]
        }
    }
}
