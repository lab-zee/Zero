"""
Data visualization generator tool that produces ECharts-compliant JSON.
"""
import json


def generate_visualization(data: str, chart_type: str, title: str = None) -> str:
    """
    Generate an ECharts-compliant JSON configuration from data.
    
    This tool should be used by the LLM to create visualizations. The LLM should
    parse the data and create a proper ECharts option object.
    
    Args:
        data: The data to visualize (can be structured data, numbers, or description)
        chart_type: Type of chart (bar, line, pie, table, scatter)
        title: Optional title for the visualization
        
    Returns:
        Instructions for the LLM to generate ECharts JSON, which should be wrapped
        in [VISUALIZATION_START] and [VISUALIZATION_END] markers with complete JSON between them
    """
    title_text = title or "Data Visualization"
    
    instruction = f"""Generate an ECharts-compliant JSON configuration for a {chart_type} chart.

Title: {title_text}
Chart Type: {chart_type}
Data to visualize: {data}

Create a complete, valid ECharts option object as JSON. The configuration should include:
- title: Chart title (as an object with "text" property, e.g., {{"text": "{title_text}"}})
- legend: Positioned at bottom ({{"bottom": 0, "orient": "horizontal"}})
- Appropriate axes (xAxis, yAxis) for the chart type
- series: Data series with the actual data values from the data argument

CRITICAL OUTPUT FORMAT:
You MUST wrap ONLY the COMPLETE JSON object in markers. The JSON must contain REAL data values, not placeholders:
[VISUALIZATION_START]
{{"title": {{"text": "Competitive Positioning in SaaS Market"}}, "series": [{{"data": [9.5, 8.5, 7.0, 7.5]}}]}}
[VISUALIZATION_END]

IMPORTANT RULES:
1. Parse the data argument (it may be a JSON string) and transform it into ECharts series data format
2. Do NOT include tool arguments (data, chart_type, title) in the ECharts config
3. Only include ECharts option properties (title, series, xAxis, yAxis, legend, tooltip, etc.)
4. The content between [VISUALIZATION_START] and [VISUALIZATION_END] must be ONLY valid JSON - no explanatory text, no markdown, no code blocks, no ellipsis, no placeholders
5. Use ACTUAL VALUES from the data argument - extract real numbers, real text, real arrays
6. The JSON must be complete and valid - it will be parsed by JSON.parse() so every string must be quoted, every array must be complete, every object must be closed
7. If the data argument contains JSON, parse it first, then transform it into ECharts format with all actual values filled in

Example format (with REAL data, not placeholders):
[VISUALIZATION_START]
{{"title": {{"text": "Competitive Positioning"}}, "series": [{{"data": [9.5, 8.5, 7.0, 7.5]}}]}}
[VISUALIZATION_END]"""
    
    return instruction
