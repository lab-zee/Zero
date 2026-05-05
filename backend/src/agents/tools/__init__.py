"""
Tool definitions and execution for agents.
"""

from typing import Dict, Any, Callable
from .web_search import web_search
from .news_search import news_search
from .calculator import calculator
from .document import document_search
from .knowledge_base import knowledge_base_search
from .swot import generate_swot
from .visualizer import generate_visualization
from .citation import extract_citations, format_sources_for_response
from .citation_structured import extract_citations_structured
from .recommendations import generate_recommendations, suggest_related_topics
from .image_generator import generate_image
from .information_validator import validate_information_sufficiency
from .followup_generator import generate_followup_questions
from .website_scraper import scrape_website

# Tool implementations registry
TOOL_IMPLEMENTATIONS: Dict[str, Callable] = {
    "web_search": web_search,
    "news_search": news_search,
    "calculator": calculator,
    "document": document_search,
    "knowledge_base": knowledge_base_search,
    "swot": generate_swot,
    "visualizer": generate_visualization,
    "extract_citations": extract_citations,
    "extract_citations_structured": extract_citations_structured,
    "generate_recommendations": generate_recommendations,
    "image_generator": generate_image,
    "validate_information_sufficiency": validate_information_sufficiency,
    "generate_followup_questions": generate_followup_questions,
    "scrape_website": scrape_website,
}

# OpenAI function definitions for tools
TOOL_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "web_search": {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information using DuckDuckGo. Use this to find current information, market data, industry trends, or any publicly available information. IMPORTANT: When searching for current data, include the current year in your query (e.g., 'market trends 2025' not 'market trends 2023'). The system will provide you with the current date - use it to construct relevant search queries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query. Include the current year when searching for recent data (e.g., 'AI market size 2025', 'industry trends 2025')."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    "news_search": {
        "type": "function",
        "function": {
            "name": "news_search",
            "description": "Search for recent news articles using DuckDuckGo. Use this to find current events, breaking news, or recent developments relevant to business strategy. IMPORTANT: When searching for current news, include the current year in your query if relevant (e.g., 'tech industry news 2025'). The system will provide you with the current date - use it to construct relevant search queries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The news search query. Include the current year when searching for recent news (e.g., 'startup funding 2025', 'market news 2025')."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    "calculator": {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Perform financial calculations, projections, and mathematical operations. Supports basic math, financial ratios, and projections.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The mathematical expression or calculation to perform (e.g., '1000 * 1.15^5' for compound growth, '50000 / 12' for monthly breakdown)"
                    }
                },
                "required": ["expression"]
            }
        }
    },
    "document": {
        "type": "function",
        "function": {
            "name": "document",
            "description": "Search and extract information from uploaded documents. Use this to find specific information from files the user has attached.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for in the documents"
                    },
                    "file_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Optional list of specific file IDs to search. If not provided, searches all available documents."
                    }
                },
                "required": ["query"]
            }
        }
    },
    "knowledge_base": {
        "type": "function",
        "function": {
            "name": "knowledge_base",
            "description": "Semantic search across all organization's uploaded documents. Use this to find relevant information from the organization's knowledge base.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The semantic search query"
                    }
                },
                "required": ["query"]
            }
        }
    },
    "swot": {
        "type": "function",
        "function": {
            "name": "swot",
            "description": "Generate a structured SWOT (Strengths, Weaknesses, Opportunities, Threats) analysis based on provided information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "context": {
                        "type": "string",
                        "description": "The context or information to analyze for SWOT"
                    },
                    "focus_area": {
                        "type": "string",
                        "description": "Optional: Specific area to focus the SWOT analysis on (e.g., 'market entry', 'product launch', 'competitive positioning')"
                    }
                },
                "required": ["context"]
            }
        }
    },
    "visualizer": {
        "type": "function",
        "function": {
            "name": "visualizer",
            "description": "CRITICAL: Use this tool to create interactive data visualizations (charts, graphs, tables) for ANY quantitative data. This tool helps you generate ECharts-compliant JSON configurations. After calling this tool, you MUST output a complete, valid ECharts option object as JSON in your response. The ECharts config must include all required properties (title, xAxis, yAxis, series, legend, etc.) with actual data values, not placeholders. IMPORTANT: Always include a legend configuration with 'bottom: 0' and 'orient: \"horizontal\"' to position the legend at the bottom of the chart for consistency. Use this tool whenever you have: numbers, statistics, comparisons, trends, distributions, percentages, financial data, market data, customer segments, risk scores, or any quantitative information that can be visualized. The JSON object should be clearly identifiable as an ECharts configuration and must be valid JSON that can be directly rendered by the frontend.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "string",
                        "description": "The data to visualize. Can be structured data (JSON), numbers, lists, or a description. Parse this data to extract values, categories, and labels for the chart."
                    },
                    "chart_type": {
                        "type": "string",
                        "enum": ["bar", "line", "pie", "scatter"],
                        "description": "The type of chart to create: 'bar' for bar charts, 'line' for line charts, 'pie' for pie charts, 'scatter' for scatter plots"
                    },
                    "title": {
                        "type": "string",
                        "description": "Title for the visualization"
                    }
                },
                "required": ["data", "chart_type"]
            }
        }
    },
    "extract_citations": {
        "type": "function",
        "function": {
            "name": "extract_citations",
            "description": "Extract and format citations from content and sources. Use this to create properly formatted source citations for research and information used in responses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The content that may contain references or URLs"
                    },
                    "sources": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "url": {"type": "string"},
                                "title": {"type": "string"},
                                "author": {"type": "string"},
                                "date": {"type": "string"},
                                "source": {"type": "string"}
                            }
                        },
                        "description": "Optional list of source dictionaries with URL, title, author, date, etc."
                    }
                },
                "required": ["content"]
            }
        }
    },
    "extract_citations_structured": {
        "type": "function",
        "function": {
            "name": "extract_citations_structured",
            "description": "Extract citations as structured JSON objects (not formatted strings). Use this when you need to return citations in a structured format that can be parsed programmatically. Returns a JSON string of citation objects.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The content that may contain references or URLs"
                    },
                    "sources": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "url": {"type": "string"},
                                "title": {"type": "string"},
                                "author": {"type": "string"},
                                "date": {"type": "string"},
                                "source": {"type": "string"},
                                "description": {"type": "string"}
                            }
                        },
                        "description": "Optional list of source dictionaries with URL, title, author, date, etc."
                    }
                },
                "required": ["content"]
            }
        }
    },
    "generate_recommendations": {
        "type": "function",
        "function": {
            "name": "generate_recommendations",
            "description": "Generate recommended readings and resources based on the topic. Use this to suggest additional resources, articles, or research that would be valuable for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The main topic or subject"
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional context about what was discussed"
                    },
                    "sources_used": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Optional list of sources already used"
                    },
                    "max_recommendations": {
                        "type": "integer",
                        "description": "Maximum number of recommendations (default: 5)",
                        "default": 5
                    }
                },
                "required": ["topic"]
            }
        }
    },
    "image_generator": {
        "type": "function",
        "function": {
            "name": "image_generator",
            "description": "Generate high-quality images from text descriptions using AI. Use this to create flowcharts, diagrams, illustrations, charts, visualizations, concept art, or any visual content that would help communicate ideas. The tool can generate images in various aspect ratios for different use cases (square for social media, wide for presentations, tall for mobile, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Detailed text description of the image to generate. Be specific about style, composition, colors, and any text that should appear in the image."
                    },
                    "aspect_ratio": {
                        "type": "string",
                        "enum": ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
                        "description": "Aspect ratio for the image. Use '1:1' for square images, '16:9' for wide presentations, '9:16' for tall mobile formats, etc. Default is '1:1'.",
                        "default": "1:1"
                    }
                },
                "required": ["prompt"]
            }
        }
    },
    "validate_information_sufficiency": {
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
    },
    "generate_followup_questions": {
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
                    }
                },
                "required": ["original_question", "answer"]
            }
        }
    },
    "scrape_website": {
        "type": "function",
        "function": {
            "name": "scrape_website",
            "description": "Extract company information from a website URL. Analyzes HTML content to extract name, description, industry, products, target market, and other organizational details. Returns structured JSON data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The website URL to scrape (e.g., 'https://example.com' or 'example.com')"
                    }
                },
                "required": ["url"]
            }
        }
    },
}


def execute_tool(tool_name: str, arguments: Dict[str, Any], tool_registry: Dict[str, Callable] = None) -> str:
    """Execute a tool by name with given arguments."""
    from .cache import tool_cache

    # Check cache first
    cached = tool_cache.get(tool_name, arguments)
    if cached is not None:
        return cached

    # Use custom registry if provided, otherwise use default
    registry = tool_registry or TOOL_IMPLEMENTATIONS

    if tool_name not in registry:
        return f"Error: Tool '{tool_name}' not found. Available tools: {', '.join(registry.keys())}"

    try:
        tool_func = registry[tool_name]
        result = tool_func(**arguments)
        result_str = str(result)
        tool_cache.set(tool_name, arguments, result_str)
        return result_str
    except Exception as e:
        return f"Error executing tool '{tool_name}': {str(e)}"
