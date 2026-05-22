# Filepath: src/web_overlay/renderer.py
# Condensed Description: Sync/async boundary — render_to_pngs and render_to_webm drive the async capture engine via asyncio.run().
# Architecture Layer: Pipeline / Renderer
# Environment: Local
# Script Hierarchy: web-overlay → src/web_overlay/renderer
# Dependencies: Internal: browser, frame_capture, webm_encoder, config, models, exceptions / External: none
# Exposes: render_to_pngs, render_to_webm
# Configuration: RenderConfig

from __future__ import annotations

# MIT License — Copyright 2026 Trollfabriken AITrix AB
import asyncio
import logging
import tempfile
from pathlib import Path

from web_overlay.config import RenderConfig
from web_overlay.models import OverlayResult

logger = logging.getLogger(__name__)


def render_to_pngs(
    html: str,
    duration: float,
    config: RenderConfig | None = None,
    output_dir: str | Path | None = None,
) -> OverlayResult:
    """Render an HTML document to a PNG sequence.

    This is a synchronous wrapper over the async capture engine.  ``html``
    must be fully rendered (Jinja substitutions already applied).

    Args:
        html: Complete HTML document string.
        duration: Length of the overlay in seconds; determines frame count.
        config: Rendering configuration. Defaults to ``RenderConfig()``.
        output_dir: Directory to write PNGs into.  A temporary directory is
            created if ``None``.

    Returns:
        ``OverlayResult`` describing the written PNG sequence.
    """
    cfg = config or RenderConfig()
    out = Path(output_dir) if output_dir else Path(tempfile.mkdtemp(prefix="web_overlay_"))
    logger.info(
        f"render_to_pngs: duration={duration}s, fps={cfg.fps}, "
        f"{cfg.width}x{cfg.height}, output_dir={out}"
    )
    return asyncio.run(_render_async(html, duration, cfg, out))


def render_to_webm(
    html: str,
    duration: float,
    output: str | Path,
    config: RenderConfig | None = None,
) -> Path:
    """Render an HTML document to a VP9-alpha WebM file.

    Renders to a temporary PNG sequence first, then encodes with ffmpeg.
    Deletes the PNG sequence afterwards if ``config.cleanup_pngs`` is ``True``.

    Args:
        html: Complete HTML document string.
        duration: Length of the overlay in seconds.
        output: Destination ``.webm`` file path.
        config: Rendering configuration. Defaults to ``RenderConfig()``.

    Returns:
        Resolved ``Path`` to the encoded WebM file.
    """
    from web_overlay.webm_encoder import encode_webm

    cfg = config or RenderConfig()
    out = Path(output)

    result = render_to_pngs(html, duration, config=cfg)

    try:
        webm_path = encode_webm(result, out, cfg)
    finally:
        if cfg.cleanup_pngs:
            _delete_png_sequence(result)

    return webm_path


# ---------------------------------------------------------------------------
# Async internals
# ---------------------------------------------------------------------------


async def _render_async(
    html: str,
    duration: float,
    config: RenderConfig,
    output_dir: Path,
) -> OverlayResult:
    """Core async render pipeline: launch → inject → capture → close.

    Dispatches to parallel capture when ``config.parallel_workers > 1``.
    """
    from web_overlay.browser import create_page, inject_content, launch_browser
    from web_overlay.frame_capture import capture_frames

    frame_count = max(1, round(duration * config.fps))
    pad_width = max(5, len(str(frame_count)))
    pattern = f"frame_%0{pad_width}d.png"

    if config.parallel_workers > 1:
        paths = await _render_parallel(html, frame_count, config, output_dir)
    else:
        pw, browser = await launch_browser(config)
        try:
            page = await create_page(
                browser, config.width, config.height, config.device_scale_factor
            )
            await inject_content(page, html)
            paths = await capture_frames(page, frame_count, config.fps, output_dir, config)
        finally:
            await browser.close()
            await pw.stop()

    return OverlayResult(
        output_dir=output_dir,
        frame_count=len(paths),
        fps=config.fps,
        width=config.width,
        height=config.height,
        duration=len(paths) / config.fps,
        pattern=pattern,
    )


async def _render_parallel(
    html: str,
    frame_count: int,
    config: RenderConfig,
    output_dir: Path,
) -> list[Path]:
    """Capture frames in parallel across ``config.parallel_workers`` browser contexts.

    Splits ``range(frame_count)`` into N contiguous chunks and runs each in a
    separate browser context via ``asyncio.gather()``.  Results are merged in
    frame-index order.

    Args:
        html: Fully rendered HTML document.
        frame_count: Total number of frames to capture.
        config: Rendering configuration.
        output_dir: Directory for all PNG output.

    Returns:
        Ordered list of paths for all frames.
    """
    n = config.parallel_workers
    chunk_size = max(1, (frame_count + n - 1) // n)
    chunks = [
        list(range(i, min(i + chunk_size, frame_count))) for i in range(0, frame_count, chunk_size)
    ]

    tasks = [_capture_chunk(html, chunk, config, output_dir) for chunk in chunks if chunk]
    chunk_results: list[list[Path]] = await asyncio.gather(*tasks)

    # Merge frame lists in index order (each inner list is already sorted).
    combined: dict[int, Path] = {}
    for paths in chunk_results:
        for path in paths:
            # Extract zero-padded index from the filename.
            stem = path.stem  # e.g. "frame_00042"
            idx = int(stem.split("_")[-1])
            combined[idx] = path

    return [combined[i] for i in sorted(combined)]


async def _capture_chunk(
    html: str,
    frame_indices: list[int],
    config: RenderConfig,
    output_dir: Path,
) -> list[Path]:
    """Launch one browser context and capture the given frame indices.

    Args:
        html: Fully rendered HTML document.
        frame_indices: Frame indices to capture within this worker.
        config: Rendering configuration.
        output_dir: Shared output directory (all workers write here safely
            because each uses a distinct filename per frame index).

    Returns:
        Paths written by this worker, in ascending index order.
    """
    from web_overlay.browser import create_page, inject_content, launch_browser
    from web_overlay.exceptions import FrameCaptureError

    pad_width = max(5, len(str(max(frame_indices) + 1)))
    fmt = f"frame_%0{pad_width}d.png"

    pw, browser = await launch_browser(config)
    paths: list[Path] = []
    try:
        page = await create_page(browser, config.width, config.height, config.device_scale_factor)
        await inject_content(page, html)

        from web_overlay.frame_capture import _advance_timeline

        output_dir.mkdir(parents=True, exist_ok=True)
        for i in frame_indices:
            t_ms = (i / config.fps) * 1000.0
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
    finally:
        await browser.close()
        await pw.stop()

    return paths


def _delete_png_sequence(result: OverlayResult) -> None:
    """Delete all PNG files from the output directory.

    Args:
        result: The result whose PNG sequence should be removed.
    """
    for path in result.output_dir.glob("*.png"):
        try:
            path.unlink()
        except OSError as exc:
            logger.warning(f"Could not delete PNG {path}: {exc}")
    logger.debug(f"PNG sequence deleted from {result.output_dir}.")
