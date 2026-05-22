# Filepath: src/web_overlay/webm_encoder.py
# Condensed Description: THE ONLY module that invokes ffmpeg; encodes a PNG sequence to VP9-alpha WebM.
# Architecture Layer: Infrastructure / FFmpeg
# Environment: Local
# Script Hierarchy: web-overlay → src/web_overlay/webm_encoder
# Dependencies: Internal: config, models, exceptions / External: none (ffmpeg on PATH)
# Exposes: encode_webm, detect_ffmpeg
# Configuration: RenderConfig

from __future__ import annotations

# MIT License — Copyright 2026 Trollfabriken AITrix AB
import logging
import shutil
import subprocess
from pathlib import Path

from web_overlay.config import RenderConfig
from web_overlay.exceptions import WebmEncodeError
from web_overlay.models import OverlayResult

logger = logging.getLogger(__name__)


def detect_ffmpeg(binary: str = "ffmpeg") -> bool:
    """Return ``True`` if ``binary`` is found on ``PATH`` or is an absolute path.

    Args:
        binary: Name or absolute path of the ffmpeg executable.

    Returns:
        ``True`` if the binary can be located, ``False`` otherwise.
    """
    return shutil.which(binary) is not None


def encode_webm(
    result: OverlayResult,
    output: Path,
    config: RenderConfig,
) -> Path:
    """Encode a PNG sequence to a VP9-alpha WebM file.

    Uses libvpx-vp9 with lossless compression and ``yuva420p`` pixel format so
    the alpha channel is preserved.  ``-auto-alt-ref 0`` is required; VP9
    alt-ref frames do not support alpha.

    Args:
        result: The ``OverlayResult`` from a prior ``render_to_pngs()`` call.
        output: Destination ``.webm`` path.
        config: Rendering configuration; ``ffmpeg_binary`` and ``verbose``
            are used.

    Returns:
        The resolved ``output`` path on success.

    Raises:
        WebmEncodeError: If ffmpeg is not found on PATH or exits with a
            non-zero return code (stderr is captured and included in the message).
    """
    if not detect_ffmpeg(config.ffmpeg_binary):
        raise WebmEncodeError(
            f"ffmpeg not found at {config.ffmpeg_binary!r}. "
            f"Install ffmpeg and make sure it is on PATH, or set "
            f"RenderConfig.ffmpeg_binary to the absolute path. "
            f"Download: https://ffmpeg.org/download.html"
        )

    output.parent.mkdir(parents=True, exist_ok=True)

    cmd: list[str] = [
        config.ffmpeg_binary,
        "-y",
        *result.as_ffmpeg_input(),
        "-c:v",
        "libvpx-vp9",
        "-pix_fmt",
        "yuva420p",
        "-auto-alt-ref",
        "0",
        "-lossless",
        "1",
        str(output),
    ]

    if not config.verbose:
        cmd = [cmd[0], "-loglevel", "error", *cmd[1:]]

    logger.debug(f"Running ffmpeg: {' '.join(cmd)}")

    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        stderr = proc.stderr.decode(errors="replace")
        raise WebmEncodeError(f"ffmpeg WebM encode failed (exit {proc.returncode}): {stderr}")

    logger.info(f"WebM encoded successfully: {output}")
    return output
