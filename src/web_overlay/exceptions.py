# Filepath: src/web_overlay/exceptions.py
# Condensed Description: Custom exception hierarchy for all web-overlay failure modes.
# Architecture Layer: Domain / Exceptions
# Environment: Local
# Script Hierarchy: web-overlay → src/web_overlay/exceptions
# Dependencies: Internal: none / External: none
# Exposes: ChromiumNotInstalledError, TemplateRenderError, FrameCaptureError, WebmEncodeError, WaitForTimeoutError
# Configuration: N/A

from __future__ import annotations

# MIT License — Copyright 2026 Trollfabriken AITrix AB


class ChromiumNotInstalledError(RuntimeError):
    """Raised when Playwright's Chromium browser is not installed.

    Hints to the user that ``web-overlay setup`` will fix the problem.
    """


class TemplateRenderError(ValueError):
    """Raised when a Jinja2 template fails to render.

    Wraps the underlying ``jinja2.UndefinedError`` with a clearer message
    that names the missing variable.
    """


class FrameCaptureError(RuntimeError):
    """Raised when Playwright fails to capture a screenshot frame."""


class WebmEncodeError(RuntimeError):
    """Raised when the ffmpeg WebM encoding subprocess exits non-zero or is not found."""


class WaitForTimeoutError(TimeoutError):
    """Raised when ``wait_for`` selector or function does not become truthy in time.

    Args:
        selector: The CSS selector or JS function string that timed out.
    """

    def __init__(self, selector: str, *args: object) -> None:
        self.selector = selector
        message = (
            f"Timed out waiting for {selector!r}. Check that the element exists and is visible."
        )
        super().__init__(message, *args)
