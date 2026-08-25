"""Behavioral tests for deterministic tools that shape agent responses."""

from __future__ import annotations

from datetime import timedelta

from jose import jwt

from src import auth
from src.agents.tools.calculator import calculator
from src.agents.tools.citation import extract_citations, format_sources_for_response
from src.agents.tools.recommendations import (
    generate_recommendations,
    suggest_related_topics,
)


def test_calculator_supports_safe_math_and_formats_results():
    assert calculator(" 2 ^ 3 ") == "8"
    assert calculator("1,000 / 4") == "250"
    assert calculator("1 / 3") == "0.33"
    assert calculator("round(math.sqrt(81))") == "9"


def test_calculator_rejects_code_and_reports_math_errors():
    assert "potentially dangerous" in calculator("__import__('os')")
    assert calculator("1 / 0") == "Error: Division by zero"
    assert calculator("unknown(1)").startswith("Error calculating expression:")


def test_citations_deduplicate_urls_and_format_complete_metadata():
    content = "Read https://example.com/report and https://example.com/report"
    sources = [
        {
            "url": "https://example.com/report",
            "title": "Duplicate",
        },
        {
            "url": "https://example.org/news",
            "title": "Evidence",
            "author": "Analyst",
            "source": "Newswire",
            "date": "2026-01-01",
        },
        "not-a-dictionary",
    ]

    result = extract_citations(content, sources)

    assert result.count("https://example.com/report") == 1
    assert "**Evidence** by Analyst (Newswire) - 2026-01-01" in result
    assert "https://example.org/news" in result
    assert extract_citations("No links here") == "No citations found in the provided content."


def test_sources_format_handles_empty_and_partial_entries():
    assert format_sources_for_response([]) == ""
    result = format_sources_for_response(
        [
            {"title": "Report", "url": "https://example.com", "date": "2026"},
            {"title": "Untimed"},
        ]
    )
    assert "### Sources" in result
    assert "Report - https://example.com (2026)" in result
    assert "Untimed" in result


def test_recommendations_include_context_specific_resources_and_limits():
    result = generate_recommendations(
        "financial strategy",
        context="market analysis and financial planning",
        max_recommendations=6,
    )
    assert "Suggested Readings & Resources" in result
    assert "Google Scholar" in result
    assert "Financial Analysis Resources" in result
    assert "Market Research Resources" in result
    assert "Strategic Planning Resources" in result
    assert generate_recommendations("topic", max_recommendations=0) == ""


def test_related_topics_cover_domains_and_default():
    topics = suggest_related_topics("market financial strategy customer")
    assert topics == [
        "competitive analysis",
        "customer segmentation",
        "pricing strategy",
        "financial modeling",
        "investment analysis",
    ]
    assert suggest_related_topics("unmapped") == [
        "market analysis",
        "competitive positioning",
        "strategic planning",
    ]


def test_password_hashing_and_access_token_expiry():
    hashed = auth.hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert auth.verify_password("correct horse battery staple", hashed)
    assert not auth.verify_password("wrong", hashed)

    token = auth.create_access_token({"sub": "7"}, expires_delta=timedelta(minutes=5))
    payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    assert payload["sub"] == "7"
    assert "exp" in payload
    default_token = auth.create_access_token({"sub": "8"})
    assert jwt.decode(default_token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])["sub"] == "8"
