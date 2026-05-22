# Filepath: web-overlay/tests/test_html_overlay_basic.py
# Condensed Description: Basic HtmlOverlay rendering tests — frame count, RGBA mode, transparency, result fields.
# Architecture Layer: tests
# Environment: test
# Script Hierarchy: test
# Dependencies: pytest, web_overlay, PIL
# Exposes: test_renders_correct_frame_count, test_each_png_is_rgba, test_each_png_has_transparent_pixel, test_overlay_result_fields_populated, test_frame_count_property
# Configuration: pytest.ini / pyproject.toml [tool.pytest.ini_options]

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from web_overlay.config import RenderConfig
from web_overlay.models import OverlayResult
from web_overlay.overlay import HtmlOverlay

pytestmark = pytest.mark.chromium

# 1 second at 10 fps = 10 frames; small fixture for speed.
_DURATION = 1.0
_FPS = 10
_WIDTH = 320
_HEIGHT = 240


@pytest.fixture
def rendered_result(tmp_output_dir: Path) -> OverlayResult:
    """Render a simple transparent HTML snippet once per test function."""
    html = (
        "<!DOCTYPE html><html><head><style>"
        "body { margin: 0; background: transparent; }"
        ".lbl { font: bold 30px sans-serif; color: rgba(255,255,255,0.9); padding: 10px; }"
        "</style></head><body><div class='lbl'>Test</div></body></html>"
    )
    overlay = HtmlOverlay(
        html=html,
        width=_WIDTH,
        height=_HEIGHT,
        duration=_DURATION,
        fps=_FPS,
    )
    config = RenderConfig(fps=_FPS, width=_WIDTH, height=_HEIGHT, cleanup_pngs=False)
    return overlay.render(tmp_output_dir, config=config)


def test_renders_correct_frame_count(rendered_result: OverlayResult) -> None:
    """1 second at 10 fps produces exactly 10 PNG files in the output directory."""
    png_files = list(rendered_result.output_dir.glob("*.png"))
    assert len(png_files) == _DURATION * _FPS


def test_each_png_is_rgba(rendered_result: OverlayResult) -> None:
    """Every captured frame has RGBA mode (four-channel with alpha)."""
    for png_path in sorted(rendered_result.output_dir.glob("*.png")):
        img = Image.open(png_path)
        assert img.mode == "RGBA", f"{png_path.name} has mode {img.mode!r}, expected RGBA"


def test_each_png_has_transparent_pixel(rendered_result: OverlayResult) -> None:
    """Every frame contains at least one fully transparent pixel (background is clear)."""
    for png_path in sorted(rendered_result.output_dir.glob("*.png")):
        img = Image.open(png_path)
        pixels = list(img.getdata())
        alpha_values = [p[3] for p in pixels]
        assert any(a == 0 for a in alpha_values), f"{png_path.name} has no fully transparent pixel"


def test_overlay_result_fields_populated(rendered_result: OverlayResult) -> None:
    """All OverlayResult scalar fields are populated with the expected values."""
    assert rendered_result.frame_count == int(_DURATION * _FPS)
    assert rendered_result.fps == _FPS
    assert rendered_result.width == _WIDTH
    assert rendered_result.height == _HEIGHT
    assert rendered_result.duration == pytest.approx(_DURATION, abs=0.05)


def test_frame_count_property() -> None:
    """HtmlOverlay.frame_count returns duration x fps before rendering."""
    overlay = HtmlOverlay(
        html="<html><body></body></html>",
        duration=2.0,
        fps=10,
    )
    assert overlay.frame_count == 20
