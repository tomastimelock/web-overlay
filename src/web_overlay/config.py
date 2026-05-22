# Filepath: src/web_overlay/config.py
# Condensed Description: Pydantic v2 model holding all rendering and encoding parameters.
# Architecture Layer: Domain / Configuration
# Environment: Local
# Script Hierarchy: web-overlay → src/web_overlay/config
# Dependencies: Internal: none / External: pydantic>=2.5
# Exposes: RenderConfig
# Configuration: N/A

from __future__ import annotations

# MIT License — Copyright 2026 Trollfabriken AITrix AB
from pydantic import BaseModel, ConfigDict, Field


class RenderConfig(BaseModel):
    """All rendering and encoding parameters for a web-overlay run.

    Attributes:
        fps: Frames per second for the output sequence.
        width: Logical viewport width in CSS pixels.
        height: Logical viewport height in CSS pixels.
        device_scale_factor: Pixel ratio; set to 2.0 for HiDPI/Retina output.
        chromium_executable_path: Absolute path to a Chromium binary, or ``None``
            to use Playwright's downloaded build.
        chromium_args: Extra flags forwarded verbatim to ``chromium.launch()``.
        timeout_per_frame: Maximum seconds allowed for a single screenshot.
        parallel_workers: Number of concurrent browser contexts. Each context
            captures a contiguous range of frames; results are merged in order.
        cleanup_pngs: Delete the PNG sequence after a successful WebM encode.
        ffmpeg_binary: Name or absolute path of the ffmpeg executable.
        verbose: Pass ``-loglevel verbose`` to ffmpeg and emit DEBUG log records.
    """

    model_config = ConfigDict(frozen=False)

    fps: int = Field(default=30, gt=0, description="Frames per second.")
    width: int = Field(default=1920, gt=0, description="Viewport width in CSS pixels.")
    height: int = Field(default=1080, gt=0, description="Viewport height in CSS pixels.")
    device_scale_factor: float = Field(default=1.0, gt=0.0, description="Pixel ratio.")
    chromium_executable_path: str | None = Field(
        default=None,
        description="Absolute path to Chromium binary, or None to use Playwright default.",
    )
    chromium_args: list[str] = Field(
        default_factory=list,
        description="Extra flags forwarded to chromium.launch().",
    )
    timeout_per_frame: float = Field(
        default=5.0,
        gt=0.0,
        description="Maximum seconds allowed per screenshot.",
    )
    parallel_workers: int = Field(
        default=1,
        ge=1,
        description="Number of concurrent browser contexts for parallel capture.",
    )
    cleanup_pngs: bool = Field(
        default=True,
        description="Delete PNG sequence after WebM encode.",
    )
    ffmpeg_binary: str = Field(
        default="ffmpeg",
        description="Name or absolute path of the ffmpeg executable.",
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose ffmpeg and debug logging.",
    )
