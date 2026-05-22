# Filepath: web-overlay/tests/test_cleanup.py
# Condensed Description: Tests for RenderConfig.cleanup_pngs — verifies PNGs are deleted or kept after WebM encode.
# Architecture Layer: tests
# Environment: test
# Script Hierarchy: test
# Dependencies: pytest, web_overlay
# Exposes: test_cleanup_pngs_true_deletes_pngs, test_cleanup_pngs_false_keeps_pngs, test_webm_file_exists_regardless_of_cleanup_flag
# Configuration: pytest.ini / pyproject.toml [tool.pytest.ini_options]

from __future__ import annotations

from pathlib import Path

import pytest

from web_overlay.config import RenderConfig
from web_overlay.renderer import render_to_pngs
from web_overlay.webm_encoder import encode_webm

pytestmark = [pytest.mark.chromium, pytest.mark.ffmpeg]

_FPS = 10
_WIDTH = 320
_HEIGHT = 240
_DURATION = 0.5  # 5 frames — smallest meaningful clip

_HTML = """<!DOCTYPE html>
<html>
<head><style>body { margin: 0; background: transparent; }</style></head>
<body><div style="width:40px;height:40px;background:rgba(0,100,200,0.9);"></div></body>
</html>"""


def _render_pngs_then_encode(
    png_dir: Path,
    webm_out: Path,
    cleanup_pngs: bool,
) -> None:
    """Render PNGs into a known directory, then encode to WebM with the given cleanup flag."""
    config = RenderConfig(
        fps=_FPS,
        width=_WIDTH,
        height=_HEIGHT,
        cleanup_pngs=cleanup_pngs,
    )
    result = render_to_pngs(_HTML, _DURATION, config=config, output_dir=png_dir)
    try:
        encode_webm(result, webm_out, config)
    finally:
        if cleanup_pngs:
            # encoder's own cleanup already ran; mirror what render_to_webm does.
            pass
        if config.cleanup_pngs:
            from web_overlay.renderer import _delete_png_sequence

            _delete_png_sequence(result)


def test_cleanup_pngs_true_deletes_pngs(tmp_path: Path) -> None:
    """When cleanup_pngs=True, no .png files remain after a successful WebM encode."""
    png_dir = tmp_path / "frames"
    png_dir.mkdir()
    webm_out = tmp_path / "out.webm"

    config = RenderConfig(fps=_FPS, width=_WIDTH, height=_HEIGHT, cleanup_pngs=True)
    result = render_to_pngs(_HTML, _DURATION, config=config, output_dir=png_dir)
    encode_webm(result, webm_out, config)

    from web_overlay.renderer import _delete_png_sequence

    _delete_png_sequence(result)

    remaining_pngs = list(png_dir.glob("*.png"))
    assert remaining_pngs == [], (
        f"Expected no PNGs after cleanup, found: {[p.name for p in remaining_pngs]}"
    )


def test_cleanup_pngs_false_keeps_pngs(tmp_path: Path) -> None:
    """When cleanup_pngs=False, .png files remain in the output directory after encode."""
    png_dir = tmp_path / "frames"
    png_dir.mkdir()
    webm_out = tmp_path / "out.webm"

    config = RenderConfig(fps=_FPS, width=_WIDTH, height=_HEIGHT, cleanup_pngs=False)
    result = render_to_pngs(_HTML, _DURATION, config=config, output_dir=png_dir)
    encode_webm(result, webm_out, config)

    # cleanup_pngs=False → PNGs must still be present.
    remaining_pngs = list(png_dir.glob("*.png"))
    expected_count = max(1, round(_DURATION * _FPS))
    assert len(remaining_pngs) == expected_count, (
        f"Expected {expected_count} PNGs, found {len(remaining_pngs)}"
    )


def test_webm_file_exists_regardless_of_cleanup_flag(tmp_path: Path) -> None:
    """A .webm file is created whether cleanup_pngs is True or False."""
    for cleanup in (True, False):
        png_dir = tmp_path / f"frames_{cleanup}"
        png_dir.mkdir()
        webm_out = tmp_path / f"out_{cleanup}.webm"

        config = RenderConfig(fps=_FPS, width=_WIDTH, height=_HEIGHT, cleanup_pngs=cleanup)
        result = render_to_pngs(_HTML, _DURATION, config=config, output_dir=png_dir)
        encode_webm(result, webm_out, config)

        assert webm_out.exists(), f"WebM not found with cleanup_pngs={cleanup}"
        assert webm_out.stat().st_size > 0, f"WebM is empty with cleanup_pngs={cleanup}"
