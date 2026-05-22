# Filepath: web-overlay/tests/test_parallel_workers.py
# Condensed Description: Tests that parallel_workers=2 produces the same frame count and pixel content as workers=1.
# Architecture Layer: tests
# Environment: test
# Script Hierarchy: test
# Dependencies: pytest, web_overlay, PIL
# Exposes: test_parallel_output_matches_serial_frame_count, test_parallel_frames_pixel_equal_to_serial, test_parallel_result_fields_match_serial
# Configuration: pytest.ini / pyproject.toml [tool.pytest.ini_options]

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from PIL import Image

from web_overlay.config import RenderConfig
from web_overlay.models import OverlayResult
from web_overlay.overlay import HtmlOverlay

pytestmark = pytest.mark.chromium

_FPS = 10
_WIDTH = 320
_HEIGHT = 240
_DURATION = 1.0  # 10 frames

_STATIC_HTML = """<!DOCTYPE html>
<html>
<head>
<style>
body { margin: 0; background: transparent; }
.box { width: 80px; height: 80px; background: rgba(200, 50, 50, 0.9); }
</style>
</head>
<body><div class="box"></div></body>
</html>"""


def _render(output_dir: Path, workers: int) -> OverlayResult:
    config = RenderConfig(
        fps=_FPS,
        width=_WIDTH,
        height=_HEIGHT,
        parallel_workers=workers,
        cleanup_pngs=False,
    )
    overlay = HtmlOverlay(
        html=_STATIC_HTML,
        width=_WIDTH,
        height=_HEIGHT,
        duration=_DURATION,
        fps=_FPS,
    )
    return overlay.render(output_dir, config=config)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def serial_result(tmp_path_factory: pytest.TempPathFactory) -> OverlayResult:
    out = tmp_path_factory.mktemp("serial")
    return _render(out, workers=1)


@pytest.fixture(scope="module")
def parallel_result(tmp_path_factory: pytest.TempPathFactory) -> OverlayResult:
    out = tmp_path_factory.mktemp("parallel")
    return _render(out, workers=2)


def test_parallel_output_matches_serial_frame_count(
    serial_result: OverlayResult,
    parallel_result: OverlayResult,
) -> None:
    """parallel_workers=2 produces the same number of frames as workers=1."""
    assert parallel_result.frame_count == serial_result.frame_count


def test_parallel_frames_pixel_equal_to_serial(
    serial_result: OverlayResult,
    parallel_result: OverlayResult,
) -> None:
    """Every frame file is byte-identical between serial and parallel renders."""
    serial_frames = sorted(serial_result.output_dir.glob("*.png"))
    parallel_frames = sorted(parallel_result.output_dir.glob("*.png"))

    assert len(serial_frames) == len(parallel_frames)

    for sf, pf in zip(serial_frames, parallel_frames, strict=True):
        img_s = Image.open(sf)
        img_p = Image.open(pf)
        assert list(img_s.getdata()) == list(img_p.getdata()), (
            f"Pixel content differs: serial {sf.name} vs parallel {pf.name}"
        )


def test_parallel_result_fields_match_serial(
    serial_result: OverlayResult,
    parallel_result: OverlayResult,
) -> None:
    """OverlayResult metadata is identical for serial and parallel renders."""
    assert parallel_result.frame_count == serial_result.frame_count
    assert parallel_result.fps == serial_result.fps
    assert parallel_result.width == serial_result.width
    assert parallel_result.height == serial_result.height
