# Filepath: src/web_overlay/models.py
# Condensed Description: OverlayResult pydantic v2 model returned by every render call.
# Architecture Layer: Domain / Models
# Environment: Local
# Script Hierarchy: web-overlay → src/web_overlay/models
# Dependencies: Internal: none / External: pydantic>=2.5
# Exposes: OverlayResult
# Configuration: N/A

from __future__ import annotations

# MIT License — Copyright 2026 Trollfabriken AITrix AB
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class OverlayResult(BaseModel):
    """Result returned by every render call.

    Attributes:
        output_dir: Directory that holds the PNG sequence.
        frame_count: Number of PNGs written.
        fps: Frames per second used for capture.
        width: Logical viewport width in CSS pixels.
        height: Logical viewport height in CSS pixels.
        duration: Total duration in seconds (``frame_count / fps``).
        pattern: Zero-padded filename pattern, e.g. ``"frame_%05d.png"``.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    output_dir: Path = Field(description="Directory containing the PNG sequence.")
    frame_count: int = Field(description="Number of frames written.")
    fps: int = Field(description="Frames per second.")
    width: int = Field(description="Logical viewport width in CSS pixels.")
    height: int = Field(description="Logical viewport height in CSS pixels.")
    duration: float = Field(description="Duration in seconds.")
    pattern: str = Field(description="Zero-padded filename pattern, e.g. frame_%05d.png.")

    def as_ffmpeg_input(self) -> list[str]:
        """Return ffmpeg input arguments to consume this PNG sequence.

        Returns:
            A list of argument strings suitable for inserting before ``-c:v``
            in an ffmpeg command, e.g.
            ``["-framerate", "30", "-i", "/tmp/.../frame_%05d.png"]``.
        """
        return [
            "-framerate",
            str(self.fps),
            "-i",
            str(self.output_dir / self.pattern),
        ]
