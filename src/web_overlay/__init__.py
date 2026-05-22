# Filepath: src/web_overlay/__init__.py
# Condensed Description: Package entry point — version string and public API re-exports.
# Architecture Layer: Domain / Package
# Environment: Local
# Script Hierarchy: web-overlay → src/web_overlay/__init__
# Dependencies: Internal: overlay, renderer, config, models / External: none
# Exposes: __version__, HtmlOverlay, SvgOverlay, render_to_pngs, render_to_webm, RenderConfig, OverlayResult
# Configuration: N/A

from __future__ import annotations

# MIT License — Copyright 2026 Trollfabriken AITrix AB

__version__ = "0.1.5"

from web_overlay.config import RenderConfig
from web_overlay.models import OverlayResult
from web_overlay.overlay import HtmlOverlay, SvgOverlay
from web_overlay.renderer import render_to_pngs, render_to_webm

__all__ = [
    "HtmlOverlay",
    "OverlayResult",
    "RenderConfig",
    "SvgOverlay",
    "__version__",
    "render_to_pngs",
    "render_to_webm",
]
