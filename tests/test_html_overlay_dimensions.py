# Filepath: web-overlay/tests/test_html_overlay_dimensions.py
# Condensed Description: Tests that rendered PNG dimensions match RenderConfig logical and device-scale settings.
# Architecture Layer: tests
# Environment: test
# Script Hierarchy: test
# Dependencies: pytest, web_overlay, PIL
# Exposes: test_png_width_matches_config, test_png_height_matches_config, test_device_scale_factor_doubles_pixel_dimensions, test_overlay_result_reports_logical_dimensions
# Configuration: pytest.ini / pyproject.toml [tool.pytest.ini_options]

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from web_overlay.config import RenderConfig
from web_overlay.models import OverlayResult
from web_overlay.overlay import HtmlOverlay

pytestmark = pytest.mark.chromium

_LOGICAL_WIDTH = 320
_LOGICAL_HEIGHT = 240
_DURATION = 0.5  # half a second at 10 fps = 5 frames
_FPS = 10

_SIMPLE_HTML = (
    "<!DOCTYPE html><html><head><style>"
    "body { margin: 0; background: transparent; }"
    "</style></head><body></body></html>"
)


def _render_one_frame(output_dir: Path, device_scale_factor: float = 1.0) -> Path:
    """Render a single frame and return its path."""
    config = RenderConfig(
        fps=_FPS,
        width=_LOGICAL_WIDTH,
        height=_LOGICAL_HEIGHT,
        device_scale_factor=device_scale_factor,
        cleanup_pngs=False,
    )
    overlay = HtmlOverlay(
        html=_SIMPLE_HTML,
        width=_LOGICAL_WIDTH,
        height=_LOGICAL_HEIGHT,
        duration=0.1,  # minimum: 1 frame
        fps=_FPS,
        device_scale_factor=device_scale_factor,
    )
    result = overlay.render(output_dir, config=config)
    return sorted(result.output_dir.glob("*.png"))[0]


def test_png_width_matches_config(tmp_output_dir: Path) -> None:
    """The pixel width of a rendered frame equals config.width at device_scale_factor=1."""
    frame = _render_one_frame(tmp_output_dir, device_scale_factor=1.0)
    img = Image.open(frame)
    assert img.width == _LOGICAL_WIDTH


def test_png_height_matches_config(tmp_output_dir: Path) -> None:
    """The pixel height of a rendered frame equals config.height at device_scale_factor=1."""
    frame = _render_one_frame(tmp_output_dir, device_scale_factor=1.0)
    img = Image.open(frame)
    assert img.height == _LOGICAL_HEIGHT


def test_device_scale_factor_doubles_pixel_dimensions(tmp_path: Path) -> None:
    """device_scale_factor=2 produces PNG pixel dimensions that are 2x the logical size."""
    out_dir = tmp_path / "dsf2"
    out_dir.mkdir()
    frame = _render_one_frame(out_dir, device_scale_factor=2.0)
    img = Image.open(frame)
    assert img.width == _LOGICAL_WIDTH * 2
    assert img.height == _LOGICAL_HEIGHT * 2


def test_overlay_result_reports_logical_dimensions(tmp_output_dir: Path) -> None:
    """OverlayResult.width / height report logical (CSS pixel) dimensions, not physical pixels."""
    config = RenderConfig(
        fps=_FPS,
        width=_LOGICAL_WIDTH,
        height=_LOGICAL_HEIGHT,
        device_scale_factor=2.0,
        cleanup_pngs=False,
    )
    overlay = HtmlOverlay(
        html=_SIMPLE_HTML,
        width=_LOGICAL_WIDTH,
        height=_LOGICAL_HEIGHT,
        duration=0.1,
        fps=_FPS,
        device_scale_factor=2.0,
    )
    result: OverlayResult = overlay.render(tmp_output_dir, config=config)
    assert result.width == _LOGICAL_WIDTH
    assert result.height == _LOGICAL_HEIGHT
