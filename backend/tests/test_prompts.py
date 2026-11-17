"""Regression test: prompt template contains literal JSON braces.

str.format() on the template raised KeyError('"invoice_number"') in production.
build_prompt() must substitute text without interpreting braces.
"""
from app.ai.prompts import INVOICE_EXTRACTION_PROMPT, build_prompt


def test_build_prompt_substitutes_text():
    prompt = build_prompt("INVOICE TOTAL 1150 USD")
    assert "INVOICE TOTAL 1150 USD" in prompt
    assert "{text}" not in prompt


def test_build_prompt_preserves_json_schema_braces():
    prompt = build_prompt("some doc text")
    # The literal schema braces must survive untouched
    assert '"invoice_number"' in prompt
    assert '"line_items"' in prompt


def test_build_prompt_truncates():
    prompt = build_prompt("x" * 100_000, max_chars=1000)
    assert "x" * 1000 in prompt
    assert "x" * 1001 not in prompt


def test_template_has_placeholder():
    assert "{text}" in INVOICE_EXTRACTION_PROMPT
