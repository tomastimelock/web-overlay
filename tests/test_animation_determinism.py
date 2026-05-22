# Filepath: web-overlay/tests/test_animation_determinism.py
# Condensed Description: Tests that the deterministic timeline-advance mechanism produces identical frames across renders.
# Architecture Layer: tests
# Environment: test
# Script Hierarchy: test
# Dependencies: pytest, web_overlay, PIL
# Exposes: test_same_overlay_renders_identical_frames, test_different_timestamps_differ, test_determinism_survives_second_process_invocation
# Configuration: pytest.ini / pyproject.toml [tool.pytest.ini_options]

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from web_overlay.config import RenderConfig
from web_overlay.overlay import HtmlOverlay

pytestmark = pytest.mark.chromium

_FPS = 10
_WIDTH = 320
_HEIGHT = 240
_DURATION = 1.0  # 10 frames

_ANIMATED_HTML = """<!DOCTYPE html>
<html>
<head>
<style>
body { margin: 0; background: transparent; }
.box {
    width: 60px;
    height: 60px;
    background: rgba(255, 80, 80, 0.95);
    animation: slide 1s linear infinite;
}
@keyframes slide {
    from { transform: translateX(0); }
    to   { transform: translateX(260px); }
}
</style>
</head>
<body><div class="box"></div></body>
</html>"""


def _render_frames(output_dir: Path) -> list[Path]:
    config = RenderConfig(fps=_FPS, width=_WIDTH, height=_HEIGHT, cleanup_pngs=False)
    overlay = HtmlOverlay(
        html=_ANIMATED_HTML,
        width=_WIDTH,
        height=_HEIGHT,
        duration=_DURATION,
        fps=_FPS,
    )
    result = overlay.render(output_dir, config=config)
    return sorted(result.output_dir.glob("*.png"))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_same_overlay_renders_identical_frames(tmp_path: Path) -> None:
    """Rendering the same HTML twice produces byte-identical PNG files for every frame."""
    dir_a = tmp_path / "run_a"
    dir_b = tmp_path / "run_b"
    dir_a.mkdir()
    dir_b.mkdir()

    frames_a = _render_frames(dir_a)
    frames_b = _render_frames(dir_b)

    assert len(frames_a) == len(frames_b)
    for fa, fb in zip(frames_a, frames_b, strict=True):
        assert _sha256_file(fa) == _sha256_file(fb), (
            f"Frame {fa.name} differs between run A and run B"
        )


def test_different_timestamps_differ(tmp_path: Path) -> None:
    """Frame 0 and frame 5 differ for an animated overlay (animation has progressed)."""
    out_dir = tmp_path / "anim"
    out_dir.mkdir()
    frames = _render_frames(out_dir)

    assert len(frames) >= 6, "Need at least 6 frames for this test"
    frame_0 = Image.open(frames[0])
    frame_5 = Image.open(frames[5])
    # At least one pixel should differ between time 0 and time 0.5 s.
    assert list(frame_0.getdata()) != list(frame_5.getdata()), (
        "Frame 0 and frame 5 are identical — animation did not advance"
    )


def test_determinism_survives_second_process_invocation(tmp_path: Path) -> None:
    """Frame 0 sha256 matches when the render is performed in a fresh subprocess."""
    # First render in-process.
    dir_in = tmp_path / "inproc"
    dir_in.mkdir()
    frames_in = _render_frames(dir_in)
    hash_in = _sha256_file(frames_in[0])

    # Second render in a subprocess so there is no shared state.
    script = (
        "from pathlib import Path; "
        "from web_overlay.config import RenderConfig; "
        "from web_overlay.overlay import HtmlOverlay; "
        f"html = {_ANIMATED_HTML!r}; "
        f"out = Path({str(tmp_path / 'subprocess')!r}); "
        "out.mkdir(exist_ok=True); "
        f"cfg = RenderConfig(fps={_FPS}, width={_WIDTH}, height={_HEIGHT}, cleanup_pngs=False); "
        f"ov = HtmlOverlay(html=html, width={_WIDTH}, height={_HEIGHT}, duration={_DURATION}, fps={_FPS}); "
        "result = ov.render(out, config=cfg); "
        "frames = sorted(result.output_dir.glob('*.png')); "
        "print(frames[0])"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )
    frame_path = Path(proc.stdout.strip())
    hash_sub = _sha256_file(frame_path)

    assert hash_in == hash_sub, "Frame 0 sha256 differs between in-process and subprocess render"
