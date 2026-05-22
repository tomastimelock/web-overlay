# Filepath: src/web_overlay/frame_capture.py
# Condensed Description: Async deterministic frame-capture loop that advances CSS animation timelines per frame.
# Architecture Layer: Infrastructure / Playwright
# Environment: Local
# Script Hierarchy: web-overlay → src/web_overlay/frame_capture
# Dependencies: Internal: config, exceptions / External: playwright>=1.40
# Exposes: capture_frames
# Configuration: RenderConfig

from __future__ import annotations

# MIT License — Copyright 2026 Trollfabriken AITrix AB
import logging
from pathlib import Path

from playwright.async_api import Page

from web_overlay.config import RenderConfig
from web_overlay.exceptions import FrameCaptureError

logger = logging.getLogger(__name__)

# JavaScript that pauses all CSS/Web Animations and seeks them to t_ms.
# Called once per frame before the screenshot.
_ADVANCE_TIMELINE_JS = """
(t) => {
    document.getAnimations().forEach(anim => {
        anim.currentTime = t;
        anim.pause();
    });
}
"""

# Waits for one rAF tick so the browser can flush layout after timeline advance.
_RAF_SETTLE_JS = "() => new Promise(r => requestAnimationFrame(r))"


async def capture_frames(
    page: Page,
    frame_count: int,
    fps: int,
    output_dir: Path,
    config: RenderConfig,
) -> list[Path]:
    """Capture ``frame_count`` frames deterministically into ``output_dir``.

    For each frame ``i`` at time ``t = i / fps`` seconds:

    1. Pause all CSS/Web Animations and seek them to ``t * 1000`` ms.
    2. Trigger a ``requestAnimationFrame`` and wait for it to settle.
    3. Screenshot with ``omitBackground=True`` → PNG with alpha channel.

    Args:
        page: An already-configured Playwright ``Page`` with content injected.
        frame_count: Total number of frames to capture.
        fps: Frames per second; used to compute each frame's timeline position.
        output_dir: Directory to write PNGs into (created if absent).
        config: Rendering configuration (timeout, verbose, etc.).

    Returns:
        Ordered list of ``Path`` objects for every PNG written.

    Raises:
        FrameCaptureError: If any screenshot call fails.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Minimum 5 digits; widen if frame_count exceeds 99 999.
    pad_width = max(5, len(str(frame_count)))
    fmt = f"frame_%0{pad_width}d.png"

    paths: list[Path] = []

    for i in range(frame_count):
        # Performance note: called once per output frame. Keep under 1 ms JS overhead.
        t_ms = (i / fps) * 1000.0
        await _advance_timeline(page, t_ms)

        path = output_dir / (fmt % i)
        try:
            await page.screenshot(
                path=str(path),
                omit_background=True,
                type="png",
                timeout=config.timeout_per_frame * 1000,
            )
        except Exception as exc:
            raise FrameCaptureError(
                f"Screenshot failed at frame {i} (t={t_ms:.1f} ms): {exc}"
            ) from exc

        paths.append(path)
        if i % 30 == 0:
            logger.debug(f"Captured frame {i}/{frame_count} (t={t_ms:.0f} ms).")

    logger.info(f"Captured {len(paths)} frames into {output_dir}.")
    return paths


async def _advance_timeline(page: Page, t_ms: float) -> None:
    """Pause all animations and seek to ``t_ms`` milliseconds.

    Args:
        page: The active Playwright page.
        t_ms: Target animation time in milliseconds.
    """
    await page.evaluate(_ADVANCE_TIMELINE_JS, t_ms)
    await page.evaluate(_RAF_SETTLE_JS)
