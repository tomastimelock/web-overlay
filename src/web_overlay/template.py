# Filepath: src/web_overlay/template.py
# Condensed Description: Jinja2 substitution helpers for HTML/SVG templates.
# Architecture Layer: Domain / Template
# Environment: Local
# Script Hierarchy: web-overlay → src/web_overlay/template
# Dependencies: Internal: exceptions / External: jinja2>=3.1
# Exposes: render_template, extract_variables
# Configuration: N/A

from __future__ import annotations

# MIT License — Copyright 2026 Trollfabriken AITrix AB
import logging
from typing import Any

import jinja2
import jinja2.meta
from jinja2 import Environment, StrictUndefined, UndefinedError

from web_overlay.exceptions import TemplateRenderError

logger = logging.getLogger(__name__)


def render_template(source: str, data: dict[str, Any] | None = None) -> str:
    """Render a Jinja2 template string with the provided data context.

    Args:
        source: Raw Jinja2 template source (HTML or SVG string).
        data: Variable bindings for ``{{ var }}`` substitutions. ``None``
            is treated as an empty dict — any undeclared variable will raise.

    Returns:
        The fully rendered HTML or SVG string.

    Raises:
        TemplateRenderError: If any template variable is missing or the
            template is syntactically invalid.
    """
    context = data or {}
    env = Environment(undefined=StrictUndefined, autoescape=False)
    try:
        tmpl = env.from_string(source)
        rendered = tmpl.render(**context)
    except UndefinedError as exc:
        raise TemplateRenderError(
            f"Template variable not provided: {exc}. "
            f"Pass the missing variable via the `data` argument."
        ) from exc
    except jinja2.TemplateSyntaxError as exc:
        raise TemplateRenderError(
            f"Template syntax error at line {exc.lineno}: {exc.message}"
        ) from exc

    logger.debug(f"Rendered template ({len(source)} chars → {len(rendered)} chars)")
    return rendered


def extract_variables(source: str) -> list[str]:
    """Return the sorted, deduplicated list of undeclared Jinja2 variable names.

    Uses the Jinja2 AST walker to find all variable names referenced in the
    template that are not defined by a ``{% set %}`` or ``{% for %}`` block.

    Args:
        source: Raw Jinja2 template source (HTML or SVG string).

    Returns:
        Sorted list of variable name strings, e.g. ``["name", "title"]``.

    Raises:
        TemplateRenderError: If the template is syntactically invalid.
    """
    env = Environment()
    try:
        ast = env.parse(source)
    except jinja2.TemplateSyntaxError as exc:
        raise TemplateRenderError(
            f"Template syntax error at line {exc.lineno}: {exc.message}"
        ) from exc

    undeclared = jinja2.meta.find_undeclared_variables(ast)
    result = sorted(undeclared)
    logger.debug(f"Found {len(result)} undeclared variable(s): {result}")
    return result
