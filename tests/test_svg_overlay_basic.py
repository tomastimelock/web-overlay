# Filepath: web-overlay/tests/test_svg_overlay_basic.py
# Condensed Description: Basic SvgOverlay rendering tests — frame count, RGBA mode, transparency, result fields.
# Architecture Layer: tests
# Environment: test
# Script Hierarchy: test
# Dependencies: pytest, web_overlay, PIL
# Exposes: test_svg_renders_correct_frame_count, test_svg_png_is_rgba, test_svg_has_transparent_pixel, test_svg_overlay_result_fields
# Configuration: pytest.ini / pyproject.toml [tool.pytest.ini_options]

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from web_overlay.config import RenderConfig
from web_overlay.models import OverlayResult
from web_overlay.overlay import SvgOverlay

pytestmark = pytest.mark.chromium

_DURATION = 1.0
_FPS = 10
_WIDTH = 320
_HEIGHT = 240

_SIMPLE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" '
    'width="320" height="240" style="background: transparent;">'
    '<text x="10" y="50" font-size="40" fill="white">Hello</text>'
    "</svg>"
)


@pytest.fixture
def svg_result(tmp_output_dir: Path) -> OverlayResult:
    """Render a simple SVG overlay once per test function."""
    config = RenderConfig(fps=_FPS, width=_WIDTH, height=_HEIGHT, cleanup_pngs=False)
    overlay = SvgOverlay(
        svg=_SIMPLE_SVG,
        width=_WIDTH,
        height=_HEIGHT,
        duration=_DURATION,
        fps=_FPS,
    )
    return overlay.render(tmp_output_dir, config=config)


def test_svg_renders_correct_frame_count(svg_result: OverlayResult) -> None:
    """1 second at 10 fps produces exactly 10 PNG files in the output directory."""
    png_files = list(svg_result.output_dir.glob("*.png"))
    assert len(png_files) == int(_DURATION * _FPS)


def test_svg_png_is_rgba(svg_result: OverlayResult) -> None:
    """Every SVG frame is saved with RGBA mode (four channels including alpha)."""
    for png_path in sorted(svg_result.output_dir.glob("*.png")):
        img = Image.open(png_path)
        assert img.mode == "RGBA", f"{png_path.name} has mode {img.mode!r}, expected RGBA"


def test_svg_has_transparent_pixel(svg_result: OverlayResult) -> None:
    """Every SVG frame contains at least one fully transparent pixel."""
    for png_path in sorted(svg_result.output_dir.glob("*.png")):
        img = Image.open(png_path)
        pixels = list(img.getdata())
        assert any(p[3] == 0 for p in pixels), f"{png_path.name} has no fully transparent pixel"


def test_svg_overlay_result_fields(svg_result: OverlayResult) -> None:
    """OverlayResult fields are populated with the values supplied to SvgOverlay."""
    assert svg_result.frame_count == int(_DURATION * _FPS)
    assert svg_result.fps == _FPS
    assert svg_result.width == _WIDTH
    assert svg_result.height == _HEIGHT
    assert svg_result.duration == pytest.approx(_DURATION, abs=0.05)
