# Filepath: web-overlay/tests/test_webm_encoding.py
# Condensed Description: End-to-end WebM encoding tests — file creation, VP9 codec, alpha stream, duration.
# Architecture Layer: tests
# Environment: test
# Script Hierarchy: test
# Dependencies: pytest, web_overlay
# Exposes: test_webm_file_created, test_ffprobe_reports_vp9_codec, test_webm_has_alpha_stream, test_webm_duration_within_tolerance
# Configuration: pytest.ini / pyproject.toml [tool.pytest.ini_options]

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from web_overlay.config import RenderConfig
from web_overlay.overlay import HtmlOverlay

pytestmark = [pytest.mark.chromium, pytest.mark.ffmpeg]

_FPS = 10
_WIDTH = 320
_HEIGHT = 240
_DURATION = 1.0  # 10 frames; fast but long enough for a valid WebM

_SIMPLE_HTML = """<!DOCTYPE html>
<html>
<head>
<style>
body { margin: 0; background: transparent; }
.box { width: 80px; height: 80px; background: rgba(0, 200, 100, 0.9); }
</style>
</head>
<body><div class="box"></div></body>
</html>"""


@pytest.fixture(scope="module")
def webm_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Render to WebM once per module — shared by all tests in this file."""
    out_dir = tmp_path_factory.mktemp("webm")
    output = out_dir / "overlay.webm"
    config = RenderConfig(
        fps=_FPS,
        width=_WIDTH,
        height=_HEIGHT,
        cleanup_pngs=False,
    )
    overlay = HtmlOverlay(
        html=_SIMPLE_HTML,
        width=_WIDTH,
        height=_HEIGHT,
        duration=_DURATION,
        fps=_FPS,
    )
    overlay.render_webm(output, config=config)
    return output


def _ffprobe_streams(path: Path) -> list[dict]:
    """Return ffprobe stream entries for a media file."""
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_streams",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(r.stdout).get("streams", [])


def _ffprobe_duration(path: Path) -> float:
    """Return duration in seconds via ffprobe."""
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(r.stdout.strip())


def test_webm_file_created(webm_path: Path) -> None:
    """The render_webm call creates a non-empty .webm file at the specified path."""
    assert webm_path.exists()
    assert webm_path.stat().st_size > 0


def test_ffprobe_reports_vp9_codec(webm_path: Path) -> None:
    """ffprobe reports codec_name 'vp9' for the video stream."""
    streams = _ffprobe_streams(webm_path)
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    assert video_streams, "No video stream found in WebM"
    codec = video_streams[0].get("codec_name", "")
    assert "vp9" in codec.lower(), f"Expected VP9 codec, got {codec!r}"


def test_webm_has_alpha_stream(webm_path: Path) -> None:
    """The WebM file was encoded with VP9 alpha (alpha_mode tag = '1').

    libvpx-vp9 lossless with -pix_fmt yuva420p stores the alpha plane as a
    separate bitstream.  ffprobe surfaces this via the stream tag alpha_mode=1
    rather than via pix_fmt, because the main stream descriptor reports the
    luma/chroma planes only.
    """
    streams = _ffprobe_streams(webm_path)
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    assert video_streams, "No video stream found in WebM"
    stream = video_streams[0]
    # VP9 alpha is indicated by the 'alpha_mode' tag value of '1'.
    alpha_mode = stream.get("tags", {}).get("alpha_mode", "0")
    pix_fmt = stream.get("pix_fmt", "")
    has_alpha = alpha_mode == "1" or "yuva" in pix_fmt
    assert has_alpha, (
        f"Expected alpha-capable stream; got alpha_mode={alpha_mode!r}, pix_fmt={pix_fmt!r}"
    )


def test_webm_duration_within_tolerance(webm_path: Path) -> None:
    """The encoded WebM duration is within ±0.2 seconds of the requested overlay duration."""
    duration = _ffprobe_duration(webm_path)
    assert duration == pytest.approx(_DURATION, abs=0.2)
