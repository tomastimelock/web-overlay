"""
Benchmark: render 150 PNG frames of a simple HTML overlay.

Trollfabriken AITrix AB — web-overlay benchmark suite
Project: CineForge / MusicVideoCreator
Author:  Trollfabriken AITrix AB <dev@trollfabriken.se>
Licence: MIT

Usage
-----
    python benchmarks/render_150_frames.py

The script renders 5 seconds at 30 fps (150 frames) of a minimal animated
HTML overlay at 1920x1080 and reports wall time. The CI budget is 60 seconds.

Exit code 0 = within budget. Exit code 1 = over budget or render failure.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import time

# ---------------------------------------------------------------------------
# Inline HTML template — no file I/O, deterministic, no web fonts
# ---------------------------------------------------------------------------

TEMPLATE = """\
<html>
<head>
<style>
  html, body {
    margin: 0;
    padding: 0;
    background: transparent;
  }

  @keyframes fade-in {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  .card {
    position: absolute;
    bottom: 10vh;
    left: 4vw;
    border-left: 6px solid #e63946;
    padding: 1vh 2vw;
    animation: fade-in 0.5s ease-out both;
    animation-play-state: paused;
  }

  .title {
    color: white;
    font-family: sans-serif;
    font-size: 4vw;
    font-weight: 700;
    line-height: 1.1;
  }

  .sub {
    color: #ccc;
    font-family: sans-serif;
    font-size: 2.5vw;
  }
</style>
</head>
<body>
  <div class="card">
    <div class="title">{{ title }}</div>
    <div class="sub">{{ subtitle }}</div>
  </div>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Benchmark parameters
# ---------------------------------------------------------------------------

FPS = 30
DURATION_SECONDS = 5.0
EXPECTED_FRAMES = int(FPS * DURATION_SECONDS)  # 150
WIDTH = 1920
HEIGHT = 1080
CI_BUDGET_SECONDS = 60.0


def run() -> None:
    try:
        from web_overlay import HtmlOverlay, RenderConfig
    except ImportError as exc:
        print(f"ERROR: web_overlay is not installed — {exc}")
        sys.exit(1)

    cfg = RenderConfig(width=WIDTH, height=HEIGHT, fps=FPS)

    overlay = HtmlOverlay(
        template=TEMPLATE,
        data={"title": "Trollfabriken AITrix AB", "subtitle": "CineForge benchmark"},
        duration=DURATION_SECONDS,
        fps=FPS,
    )

    out_dir = tempfile.mkdtemp(prefix="web_overlay_bench_")
    try:
        print(
            f"Rendering {EXPECTED_FRAMES} frames ({DURATION_SECONDS}s @ {FPS} fps) "
            f"at {WIDTH}x{HEIGHT} …"
        )
        print(f"Output directory: {out_dir}")

        t0 = time.perf_counter()
        overlay.render_png_sequence(out_dir, config=cfg)
        elapsed = time.perf_counter() - t0

        # Verify frame count
        import pathlib

        frames = sorted(pathlib.Path(out_dir).glob("frame_*.png"))
        actual_frames = len(frames)

        print(f"\nFrames written : {actual_frames}")
        print(f"Wall time      : {elapsed:.2f}s")
        print(f"Per frame      : {elapsed / max(actual_frames, 1) * 1000:.1f} ms")
        print(f"CI budget      : {CI_BUDGET_SECONDS}s")

        if actual_frames != EXPECTED_FRAMES:
            print(f"\nFAIL: expected {EXPECTED_FRAMES} frames, got {actual_frames}")
            sys.exit(1)

        if elapsed > CI_BUDGET_SECONDS:
            print(f"\nFAIL: {elapsed:.2f}s exceeds {CI_BUDGET_SECONDS}s CI budget")
            sys.exit(1)

        print(f"\nPASS: {elapsed:.2f}s — within {CI_BUDGET_SECONDS}s budget")

    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


if __name__ == "__main__":
    run()
