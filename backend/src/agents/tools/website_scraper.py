"""
Website Scraper Tool - Extracts company information from websites.

Uses LLM to intelligently parse HTML content and extract structured organization data.
"""

import json
import requests
from typing import Dict, Any
from bs4 import BeautifulSoup


def scrape_website(url: str) -> Dict[str, Any]:
    """
    Scrape a company website to extract organization information.

    Args:
        url: Website URL to scrape

    Returns:
        Dictionary with extracted company info:
        {
            "success": bool,
            "data": {
                "name": str,
                "description": str,
                "industry": str,
                "org_type": str,
                "purpose": str,
                "goals_missions": str,
                "website_url": str,
                "social_media_links": dict,
                "key_products_services": list,
                "target_market": str,
                "leadership_info": str
            },
            "confidence": float,  # 0.0-1.0
            "error": str (if failed)
        }
    """
    from ...llm_client import LLMClient

    # Validate URL
    if not url:
        return {
            "success": False,
            "error": "No URL provided",
            "data": None
        }

    # Add https:// if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    try:
        # Fetch website content
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove script and style elements
        for script in soup(['script', 'style', 'nav', 'footer', 'header']):
            script.decompose()

        # Get text content
        text_content = soup.get_text(separator=' ', strip=True)

        # Limit content length for LLM (to avoid token limits)
        max_chars = 8000
        if len(text_content) > max_chars:
            text_content = text_content[:max_chars] + "..."

        # Extract meta tags
        meta_description = soup.find('meta', attrs={'name': 'description'})
        meta_description = meta_description.get('content', '') if meta_description else ''

        title = soup.find('title')
        title_text = title.string if title else ''

        # Look for social media links
        social_links = {}
        social_patterns = {
            'linkedin': ['linkedin.com'],
            'twitter': ['twitter.com', 'x.com'],
            'facebook': ['facebook.com'],
            'instagram': ['instagram.com'],
            'youtube': ['youtube.com']
        }

        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            for platform, patterns in social_patterns.items():
                if any(pattern in href for pattern in patterns):
                    social_links[platform] = link['href']

        # Use LLM to extract structured information
        prompt = f"""You are a data extraction specialist. Analyze the following website content and extract structured company information.

WEBSITE URL: {url}
TITLE: {title_text}
META DESCRIPTION: {meta_description}

WEBSITE CONTENT:
{text_content}

Extract the following information in JSON format:

1. **name**: Company/organization name (from title, content, or branding)
2. **description**: Brief 1-2 sentence description of what the company does
3. **industry**: Industry sector (e.g., "Technology", "Healthcare", "Finance", "Retail")
4. **org_type**: Organization type - one of: "startup", "enterprise", "smb", "nonprofit", "government", "consulting"
5. **purpose**: Core purpose or mission statement
6. **goals_missions**: Key goals, objectives, or mission details (2-3 sentences)
7. **key_products_services**: List of main products or services (array of strings, 3-5 items)
8. **target_market**: Target customers/market (e.g., "B2B SaaS companies", "Healthcare providers", "Consumers")
9. **leadership_info**: Key leadership information if mentioned (CEO, founders, etc.)

IMPORTANT GUIDELINES:
- Be concise but informative
- If information is not available, use null or empty string
- Extract actual facts from the content, don't infer or make up information
- For org_type, choose the most appropriate from the allowed values
- Keep descriptions professional and factual

Respond in this EXACT JSON format:
{{
    "name": "Company Name",
    "description": "What they do",
    "industry": "Industry name",
    "org_type": "startup|enterprise|smb|nonprofit|government|consulting",
    "purpose": "Core purpose",
    "goals_missions": "Key goals and mission",
    "key_products_services": ["Product 1", "Product 2", "Product 3"],
    "target_market": "Target customers",
    "leadership_info": "CEO: Name, Founded by: Names, etc.",
    "confidence": 0.85
}}

The confidence score (0.0-1.0) should reflect how much clear information was available in the content.
"""

        # Use fast model for extraction
        client = LLMClient(provider="openai", model="gpt-4o-mini")
        response = client.chat_completions_create(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        # Extract content from response
        response_text = response.choices[0].message.content
        extracted_data = json.loads(response_text)

        # Add website URL and social links to extracted data
        extracted_data['website_url'] = url
        extracted_data['social_media_links'] = social_links

        # Validate confidence score
        confidence = extracted_data.get('confidence', 0.5)
        if not isinstance(confidence, (int, float)):
            confidence = 0.5
        confidence = max(0.0, min(1.0, float(confidence)))

        # Validate org_type
        valid_org_types = ["startup", "enterprise", "smb", "nonprofit", "government", "consulting"]
        if extracted_data.get('org_type') not in valid_org_types:
            # Default to smb if unknown
            extracted_data['org_type'] = 'smb'

        return {
            "success": True,
            "data": extracted_data,
            "confidence": confidence,
            "error": None
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "error": f"Failed to fetch website: {str(e)}",
            "data": None
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to parse extracted data: {str(e)}",
            "data": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Scraping error: {str(e)}",
            "data": None
        }


# Tool definition for agent registry
TOOL_DEFINITION = {
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
}
