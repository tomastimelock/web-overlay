# Filepath: web-overlay/tests/test_template_substitution.py
# Condensed Description: Pure-Python tests for render_template and extract_variables.
# Architecture Layer: tests
# Environment: test
# Script Hierarchy: test
# Dependencies: pytest, web_overlay
# Exposes: test_single_var_replaced, test_multiple_vars_replaced, test_missing_var_raises_template_render_error, test_nested_conditional_rendered, test_extract_variables_from_html, test_extract_variables_from_svg
# Configuration: pytest.ini / pyproject.toml [tool.pytest.ini_options]

from __future__ import annotations

import pytest

from web_overlay.exceptions import TemplateRenderError
from web_overlay.template import extract_variables, render_template


def test_single_var_replaced() -> None:
    """A single {{ name }} placeholder is replaced with the given value."""
    result = render_template("Hello {{ name }}", {"name": "World"})
    assert result == "Hello World"


def test_multiple_vars_replaced() -> None:
    """Two distinct placeholders are both substituted correctly."""
    result = render_template("{{ greeting }}, {{ name }}!", {"greeting": "Hi", "name": "Tomas"})
    assert result == "Hi, Tomas!"


def test_missing_var_raises_template_render_error() -> None:
    """render_template raises TemplateRenderError when a variable is absent from data."""
    with pytest.raises(TemplateRenderError):
        render_template("{{ missing }}", {})


def test_nested_conditional_rendered() -> None:
    """A {% if %} block renders its content when the condition is True."""
    result = render_template("{% if show %}Yes{% endif %}", {"show": True})
    assert "Yes" in result


def test_conditional_suppressed_when_false() -> None:
    """A {% if %} block is absent when the condition is False."""
    result = render_template("{% if show %}Yes{% endif %}", {"show": False})
    assert "Yes" not in result


def test_extract_variables_from_html() -> None:
    """extract_variables returns the variable name found inside an HTML element."""
    variables = extract_variables("<p>{{ name }}</p>")
    assert variables == ["name"]


def test_extract_variables_from_svg() -> None:
    """extract_variables returns the variable name found inside an SVG element."""
    variables = extract_variables("<text>{{ title }}</text>")
    assert variables == ["title"]


def test_extract_variables_multiple_deduplicated() -> None:
    """Duplicate uses of the same variable appear only once in the result."""
    variables = extract_variables("{{ x }} and {{ x }} again")
    assert variables == ["x"]


def test_extract_variables_sorted() -> None:
    """extract_variables returns names in alphabetical order."""
    variables = extract_variables("{{ zebra }} {{ apple }}")
    assert variables == ["apple", "zebra"]


def test_extract_variables_no_variables() -> None:
    """extract_variables returns an empty list for a template with no placeholders."""
    variables = extract_variables("<p>plain text</p>")
    assert variables == []


def test_render_template_with_none_data() -> None:
    """render_template treats None data as an empty dict (no substitutions needed)."""
    result = render_template("static content", None)
    assert result == "static content"
