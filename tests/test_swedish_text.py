# Filepath: web-overlay/tests/test_swedish_text.py
# Condensed Description: Tests that non-ASCII Swedish characters render without errors and produce visible pixels.
# Architecture Layer: tests
# Environment: test
# Script Hierarchy: test
# Dependencies: pytest, web_overlay, PIL
# Exposes: test_swedish_template_renders_without_error, test_non_ascii_frame_is_not_blank, test_glyph_pixels_differ_from_background
# Configuration: pytest.ini / pyproject.toml [tool.pytest.ini_options]

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from web_overlay.config import RenderConfig
from web_overlay.models import OverlayResult
from web_overlay.overlay import HtmlOverlay

pytestmark = pytest.mark.chromium

_SWEDISH_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body  { margin: 0; background: transparent; }
.name { font: bold 48px sans-serif; color: rgba(255, 255, 255, 0.95); padding: 20px; }
</style>
</head>
<body><div class="name">Tomas Amlöv</div></body>
</html>"""

_FPS = 10
_WIDTH = 320
_HEIGHT = 240
_DURATION = 0.3  # 3 frames — enough to verify without slow render


@pytest.fixture
def swedish_result(tmp_output_dir: Path) -> OverlayResult:
    """Render the Swedish-text HTML once per test function."""
    config = RenderConfig(fps=_FPS, width=_WIDTH, height=_HEIGHT, cleanup_pngs=False)
    overlay = HtmlOverlay(
        html=_SWEDISH_HTML,
        width=_WIDTH,
        height=_HEIGHT,
        duration=_DURATION,
        fps=_FPS,
    )
    return overlay.render(tmp_output_dir, config=config)


def test_swedish_template_renders_without_error(swedish_result: OverlayResult) -> None:
    """Rendering a template containing 'Tomas Amlöv' does not raise any exception."""
    assert swedish_result.frame_count >= 1


def test_non_ascii_frame_is_not_blank(swedish_result: OverlayResult) -> None:
    """The first frame is not entirely transparent — text glyphs are present."""
    frame = sorted(swedish_result.output_dir.glob("*.png"))[0]
    img = Image.open(frame)
    pixels = list(img.getdata())
    # At least one pixel must be non-transparent (alpha > 0).
    assert any(p[3] > 0 for p in pixels), "Frame is entirely transparent; text was not rendered"


def test_glyph_pixels_differ_from_background(swedish_result: OverlayResult) -> None:
    """Some pixels have a different alpha than others, confirming glyph rendering."""
    frame = sorted(swedish_result.output_dir.glob("*.png"))[0]
    img = Image.open(frame)
    pixels = list(img.getdata())
    alpha_values = {p[3] for p in pixels}
    # Must have at least two distinct alpha values (glyph vs transparent background).
    assert len(alpha_values) > 1, (
        "All pixels share the same alpha value — glyph rendering did not produce variation"
    )
