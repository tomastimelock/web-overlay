# Filepath: src/web_overlay/overlay.py
# Condensed Description: HtmlOverlay and SvgOverlay public classes that hold rendering parameters and delegate to renderer.py.
# Architecture Layer: Domain / Overlay
# Environment: Local
# Script Hierarchy: web-overlay → src/web_overlay/overlay
# Dependencies: Internal: renderer, template, config, models, exceptions / External: none
# Exposes: HtmlOverlay, SvgOverlay
# Configuration: RenderConfig

from __future__ import annotations

# MIT License — Copyright 2026 Trollfabriken AITrix AB
import logging
import re
from pathlib import Path
from typing import Any, Literal

from web_overlay.config import RenderConfig
from web_overlay.models import OverlayResult
from web_overlay.template import render_template

logger = logging.getLogger(__name__)

_SVG_HTML_SHELL = """\
<!DOCTYPE html>
<html>
<head>
<style>
* {{ margin: 0; padding: 0; }}
body {{ background: transparent; overflow: hidden; }}
svg {{ display: block; }}
</style>
</head>
<body>{svg_content}</body>
</html>"""


def _inject_css(html: str, css_content: str) -> str:
    """Inject ``<style>css_content</style>`` into the ``<head>`` of ``html``.

    If the document has no ``<head>``, the style tag is prepended before
    ``<body>`` or prepended to the document start as a fallback.

    Args:
        html: HTML document string.
        css_content: Raw CSS to inject.

    Returns:
        Modified HTML string with the style block inserted.
    """
    style_tag = f"<style>\n{css_content}\n</style>"
    if re.search(r"</head>", html, re.IGNORECASE):
        return re.sub(r"(</head>)", f"{style_tag}\n\\1", html, count=1, flags=re.IGNORECASE)
    if re.search(r"<body", html, re.IGNORECASE):
        return re.sub(r"(<body)", f"{style_tag}\n\\1", html, count=1, flags=re.IGNORECASE)
    return style_tag + "\n" + html


class HtmlOverlay:
    """Render an HTML document over a transparent background.

    Output is a sequence of PNGs (one per frame) or a VP9-alpha WebM.

    Args:
        template: Path to an HTML file, or a Jinja2 HTML string.  Mutually
            exclusive with ``html``.
        html: Inline HTML string.  Mutually exclusive with ``template``.
        data: Jinja2 context for ``{{ var }}`` substitution.
        css: Extra CSS to inject — either a ``Path`` to a ``.css`` file or a
            raw CSS string.
        width: Logical viewport width in CSS pixels.
        height: Logical viewport height in CSS pixels.
        duration: Overlay duration in seconds.
        fps: Frames per second.
        device_scale_factor: Pixel ratio for HiDPI rendering.
        wait_for: CSS selector that must be present before frame 0.
        wait_for_function: JS expression that must be truthy before frame 0.
        wait_for_timeout: Maximum seconds to wait for ``wait_for``/
            ``wait_for_function``.
        animations: ``"preserve"`` (default) uses the deterministic timeline
            advance path; ``"wait"`` is an alias for the same path in v0.1.

    Raises:
        ValueError: If both or neither of ``template``/``html`` are provided.
        TemplateRenderError: If Jinja2 rendering fails.
    """

    def __init__(
        self,
        template: str | Path | None = None,
        html: str | None = None,
        data: dict[str, Any] | None = None,
        css: str | Path | None = None,
        width: int = 1920,
        height: int = 1080,
        duration: float = 5.0,
        fps: int = 30,
        device_scale_factor: float = 1.0,
        wait_for: str | None = None,
        wait_for_function: str | None = None,
        wait_for_timeout: float = 10.0,
        animations: Literal["preserve", "wait"] = "preserve",
    ) -> None:
        if template is None and html is None:
            raise ValueError(
                "Provide either `template` (a file path or HTML string) or `html` (an inline string)."
            )
        if template is not None and html is not None:
            raise ValueError("`template` and `html` are mutually exclusive. Provide only one.")

        if template is not None:
            source = (
                Path(template).read_text(encoding="utf-8")
                if Path(str(template)).exists()
                else str(template)
            )
        else:
            source = str(html)

        self._html: str = render_template(source, data)

        if css is not None:
            css_path = Path(str(css))
            css_content = css_path.read_text(encoding="utf-8") if css_path.exists() else str(css)
            self._html = _inject_css(self._html, css_content)

        self._duration = float(duration)
        self._fps = fps
        self._width = width
        self._height = height
        self._device_scale_factor = device_scale_factor
        self._wait_for = wait_for
        self._wait_for_function = wait_for_function
        self._wait_for_timeout = wait_for_timeout
        self._animations = animations

    @property
    def duration(self) -> float:
        """Total overlay duration in seconds."""
        return self._duration

    @property
    def frame_count(self) -> int:
        """Total number of frames that will be captured."""
        return max(1, round(self._duration * self._fps))

    def render(
        self,
        output_dir: str | Path,
        config: RenderConfig | None = None,
    ) -> OverlayResult:
        """Render the overlay to a PNG sequence.

        Args:
            output_dir: Directory to write PNGs into (created if absent).
            config: Rendering configuration overrides.

        Returns:
            ``OverlayResult`` describing the written PNG sequence.
        """
        from web_overlay.renderer import render_to_pngs

        cfg = self._merge_config(config)
        logger.info(
            f"HtmlOverlay.render: {self._width}x{self._height}, "
            f"duration={self._duration}s, fps={cfg.fps}"
        )
        return render_to_pngs(
            self._html,
            self._duration,
            config=cfg,
            output_dir=output_dir,
        )

    def render_webm(
        self,
        output: str | Path,
        config: RenderConfig | None = None,
    ) -> Path:
        """Render the overlay to a VP9-alpha WebM file.

        Args:
            output: Destination ``.webm`` file path.
            config: Rendering configuration overrides.

        Returns:
            Resolved ``Path`` to the encoded WebM file.
        """
        from web_overlay.renderer import render_to_webm

        cfg = self._merge_config(config)
        logger.info(f"HtmlOverlay.render_webm: output={output}")
        return render_to_webm(self._html, self._duration, output=output, config=cfg)

    def _merge_config(self, config: RenderConfig | None) -> RenderConfig:
        """Return a ``RenderConfig`` with overlay-level defaults applied.

        The caller-supplied ``config`` takes precedence over the constructor
        arguments so programmatic overrides always win.
        """
        if config is not None:
            return config
        return RenderConfig(
            width=self._width,
            height=self._height,
            fps=self._fps,
            device_scale_factor=self._device_scale_factor,
        )


class SvgOverlay:
    """Render an SVG (with optional CSS or SMIL animations) as an overlay sequence.

    Wraps the SVG in a minimal HTML5 shell so Playwright can render it, then
    delegates to the same render pipeline as ``HtmlOverlay``.

    Args:
        svg: Path to a ``.svg`` file, or an inline SVG string.
        data: Jinja2 context for ``{{ var }}`` substitution.
        width: Logical viewport width in CSS pixels.
        height: Logical viewport height in CSS pixels.
        duration: Overlay duration in seconds.
        fps: Frames per second.
        animations: Animation mode hint. ``"css"`` and ``"smil"`` both use
            the same deterministic timeline advance in v0.1; ``"none"`` renders
            a static first frame (duration frames will be identical).

    Raises:
        TemplateRenderError: If Jinja2 rendering of the SVG fails.
    """

    def __init__(
        self,
        svg: str | Path,
        data: dict[str, Any] | None = None,
        width: int = 1920,
        height: int = 1080,
        duration: float = 5.0,
        fps: int = 30,
        animations: Literal["smil", "css", "none"] = "css",
    ) -> None:
        svg_path = Path(str(svg))
        svg_source = svg_path.read_text(encoding="utf-8") if svg_path.exists() else str(svg)

        rendered_svg = render_template(svg_source, data)
        self._html = _SVG_HTML_SHELL.format(svg_content=rendered_svg)

        self._duration = float(duration)
        self._fps = fps
        self._width = width
        self._height = height
        self._animations = animations

    @property
    def duration(self) -> float:
        """Total overlay duration in seconds."""
        return self._duration

    @property
    def frame_count(self) -> int:
        """Total number of frames that will be captured."""
        return max(1, round(self._duration * self._fps))

    def render(
        self,
        output_dir: str | Path,
        config: RenderConfig | None = None,
    ) -> OverlayResult:
        """Render the SVG overlay to a PNG sequence.

        Args:
            output_dir: Directory to write PNGs into (created if absent).
            config: Rendering configuration overrides.

        Returns:
            ``OverlayResult`` describing the written PNG sequence.
        """
        from web_overlay.renderer import render_to_pngs

        cfg = self._merge_config(config)
        logger.info(
            f"SvgOverlay.render: {self._width}x{self._height}, "
            f"duration={self._duration}s, fps={cfg.fps}"
        )
        return render_to_pngs(
            self._html,
            self._duration,
            config=cfg,
            output_dir=output_dir,
        )

    def render_webm(
        self,
        output: str | Path,
        config: RenderConfig | None = None,
    ) -> Path:
        """Render the SVG overlay to a VP9-alpha WebM file.

        Args:
            output: Destination ``.webm`` file path.
            config: Rendering configuration overrides.

        Returns:
            Resolved ``Path`` to the encoded WebM file.
        """
        from web_overlay.renderer import render_to_webm

        cfg = self._merge_config(config)
        logger.info(f"SvgOverlay.render_webm: output={output}")
        return render_to_webm(self._html, self._duration, output=output, config=cfg)

    def _merge_config(self, config: RenderConfig | None) -> RenderConfig:
        """Return a ``RenderConfig`` with overlay-level defaults applied."""
        if config is not None:
            return config
        return RenderConfig(
            width=self._width,
            height=self._height,
            fps=self._fps,
        )
