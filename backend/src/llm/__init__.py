from .strategy_prompts import build_strategy_prompt, build_organization_context, build_conversation_context, STRATEGY_SYSTEM_PROMPT
from .generic_prompts import build_generic_prompt, GENERIC_SYSTEM_PROMPT
from .analytical_prompts import build_analytical_prompt, ANALYTICAL_SYSTEM_PROMPT
from .creative_prompts import build_creative_prompt, CREATIVE_SYSTEM_PROMPT
from .executive_prompts import build_executive_prompt, EXECUTIVE_SYSTEM_PROMPT
from .response_parser import parse_response

__all__ = [
    "build_strategy_prompt",
    "build_generic_prompt",
    "build_analytical_prompt",
    "build_creative_prompt",
    "build_executive_prompt",
    "build_organization_context",
    "build_conversation_context",
    "parse_response",
]

# Agent registry for admin viewing
AGENT_REGISTRY = {
    "strategy": {
        "name": "Strategy Advisor",
        "description": "Provides detailed strategic guidance with actionable recommendations. Asks clarifying questions when needed.",
        "use_cases": ["Strategic planning", "Goal setting", "Resource allocation", "Long-term planning"],
        "style": "Detailed, structured, question-first approach",
        "system_prompt": STRATEGY_SYSTEM_PROMPT
    },
    "generic": {
        "name": "General Assistant",
        "description": "Provides concise, direct answers to questions. Quick and efficient for general queries.",
        "use_cases": ["Quick questions", "General information", "Simple queries", "Fact-finding"],
        "style": "Concise, direct, efficient",
        "system_prompt": GENERIC_SYSTEM_PROMPT
    },
    "analytical": {
        "name": "Data Analyst",
        "description": "Performs deep analysis, identifies patterns, and provides data-driven insights. Excellent for complex data review.",
        "use_cases": ["Data analysis", "Pattern recognition", "Research deep-dives", "Complex information breakdown"],
        "style": "Thorough, evidence-based, structured analysis",
        "system_prompt": ANALYTICAL_SYSTEM_PROMPT
    },
    "creative": {
        "name": "Creative Ideator",
        "description": "Generates ideas, explores possibilities, and thinks outside the box. Great for brainstorming sessions.",
        "use_cases": ["Brainstorming", "Idea generation", "Creative problem-solving", "Exploring possibilities"],
        "style": "Divergent thinking, multiple perspectives, innovative",
        "system_prompt": CREATIVE_SYSTEM_PROMPT
    },
    "executive": {
        "name": "Executive Advisor",
        "description": "Provides high-level strategic summaries and actionable insights for decision-makers. Concise and strategic.",
        "use_cases": ["Executive summaries", "Strategic overviews", "Decision support", "High-level insights"],
        "style": "Concise, strategic, action-oriented",
        "system_prompt": EXECUTIVE_SYSTEM_PROMPT
    }
}

