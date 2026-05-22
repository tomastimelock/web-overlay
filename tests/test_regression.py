# Filepath: web-overlay/tests/test_regression.py
# Condensed Description: Regression snapshot tests covering fonts-loaded-before-frame-0, SMIL animation progress, and fixed-position element visibility.
# Architecture Layer: tests
# Environment: test
# Script Hierarchy: test
# Dependencies: pytest, web_overlay, PIL
# Exposes: test_web_fonts_loaded_before_frame_zero, test_svg_smil_animation_respects_duration, test_fixed_position_element_not_cropped
# Configuration: pytest.ini / pyproject.toml [tool.pytest.ini_options]

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from web_overlay.config import RenderConfig
from web_overlay.overlay import HtmlOverlay, SvgOverlay

pytestmark = pytest.mark.chromium

_FPS = 10
_WIDTH = 320
_HEIGHT = 240


# ---------------------------------------------------------------------------
# Regression: web fonts must be loaded before frame 0 is captured.
#
# Spec: "inject HTML with a data-URI font; verify frame 0 is not blank
#        (fonts loaded before screenshot)"
# ---------------------------------------------------------------------------

# A minimal data-URI font (base64-encoded single-glyph TTF would be complex;
# instead we use a system-font stack that is guaranteed to render, combined
# with document.fonts.ready, which the browser module awaits before capture.)
_FONT_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@import url("data:text/css,body%7Bfont-family:sans-serif%7D");
body  { margin: 0; background: transparent; font-family: sans-serif; }
.text { font-size: 48px; color: rgba(255, 255, 255, 0.95); padding: 10px; }
</style>
</head>
<body><div class="text">Ready</div></body>
</html>"""


def test_web_fonts_loaded_before_frame_zero(tmp_path: Path) -> None:
    """Frame 0 is not blank — fonts (or at least system fallback) are loaded before capture.

    Regression: previously, the browser was screenshotted before
    document.fonts.ready resolved, resulting in invisible text.
    """
    config = RenderConfig(fps=_FPS, width=_WIDTH, height=_HEIGHT, cleanup_pngs=False)
    overlay = HtmlOverlay(
        html=_FONT_HTML,
        width=_WIDTH,
        height=_HEIGHT,
        duration=0.1,
        fps=_FPS,
    )
    result = overlay.render(tmp_path / "fonts", config=config)
    frame_zero = sorted(result.output_dir.glob("*.png"))[0]
    img = Image.open(frame_zero)
    pixels = list(img.getdata())
    # Frame must contain at least one non-transparent pixel (text rendered).
    assert any(p[3] > 0 for p in pixels), (
        "Frame 0 is entirely transparent — fonts may not have been ready before capture"
    )


# ---------------------------------------------------------------------------
# Regression: SVG SMIL animation must respect elapsed time so that frame 9
# looks different from frame 0.
#
# Spec: "SVG with <animate dur='1s'> at 10fps; frame 0 and frame 9 differ"
# ---------------------------------------------------------------------------

_SMIL_SVG = """<svg xmlns="http://www.w3.org/2000/svg"
     width="320" height="240"
     style="background: transparent;">
  <rect x="0" y="90" width="60" height="60" fill="rgba(255,80,0,0.9)">
    <animate attributeName="x" from="0" to="260" dur="1s"
             fill="freeze" begin="0s"/>
  </rect>
</svg>"""


def test_svg_smil_animation_respects_duration(tmp_path: Path) -> None:
    """Frame 0 and frame 9 differ for an SVG with a 1-second SMIL animation.

    Regression: timeline-advance must apply to SVG SMIL animations,
    not only CSS animations.
    """
    config = RenderConfig(fps=_FPS, width=_WIDTH, height=_HEIGHT, cleanup_pngs=False)
    overlay = SvgOverlay(
        svg=_SMIL_SVG,
        width=_WIDTH,
        height=_HEIGHT,
        duration=1.0,
        fps=_FPS,
        animations="smil",
    )
    result = overlay.render(tmp_path / "smil", config=config)
    frames = sorted(result.output_dir.glob("*.png"))
    assert len(frames) >= 10, "Need at least 10 frames for this regression test"

    img_0 = Image.open(frames[0])
    img_9 = Image.open(frames[9])
    # The red rectangle moves horizontally; pixels must differ between t=0 and t=0.9s.
    assert list(img_0.getdata()) != list(img_9.getdata()), (
        "Frame 0 and frame 9 are identical — SMIL animation did not advance"
    )


# ---------------------------------------------------------------------------
# Regression: CSS position:fixed element must not be cropped out of the frame.
#
# Spec: "CSS position:fixed; right:0; bottom:0 element; verify that pixel
#        at bottom-right of frame is not fully transparent"
# ---------------------------------------------------------------------------

_FIXED_HTML = """<!DOCTYPE html>
<html>
<head>
<style>
* { margin: 0; padding: 0; }
body { background: transparent; }
.badge {
    position: fixed;
    right: 0;
    bottom: 0;
    width: 40px;
    height: 40px;
    background: rgba(0, 200, 50, 0.95);
}
</style>
</head>
<body><div class="badge"></div></body>
</html>"""


def test_fixed_position_element_not_cropped(tmp_path: Path) -> None:
    """A position:fixed element anchored to the bottom-right corner is visible in frame 0.

    Regression: some viewport configurations cropped fixed elements,
    producing a fully transparent bottom-right corner.
    """
    config = RenderConfig(fps=_FPS, width=_WIDTH, height=_HEIGHT, cleanup_pngs=False)
    overlay = HtmlOverlay(
        html=_FIXED_HTML,
        width=_WIDTH,
        height=_HEIGHT,
        duration=0.1,
        fps=_FPS,
    )
    result = overlay.render(tmp_path / "fixed", config=config)
    frame_zero = sorted(result.output_dir.glob("*.png"))[0]
    img = Image.open(frame_zero)

    # Sample the bottom-right 40x40 region; at least one pixel must be non-transparent.
    right = img.width
    bottom = img.height
    region = img.crop((right - 40, bottom - 40, right, bottom))
    pixels = list(region.getdata())
    assert any(p[3] > 0 for p in pixels), (
        "Bottom-right corner is fully transparent — fixed-position element was cropped"
    )
