# Filepath: web-overlay/tests/test_errors.py
# Condensed Description: Tests for the custom exception types — ChromiumNotInstalledError, WaitForTimeoutError, WebmEncodeError.
# Architecture Layer: tests
# Environment: test
# Script Hierarchy: test
# Dependencies: pytest, web_overlay
# Exposes: test_missing_chromium_raises_chromium_not_installed_error, test_missing_chromium_message_mentions_setup_command, test_bad_wait_for_selector_raises_wait_for_timeout_error, test_bad_selector_message_contains_selector_string, test_missing_ffmpeg_raises_webm_encode_error, test_missing_ffmpeg_message_contains_binary_name
# Configuration: pytest.ini / pyproject.toml [tool.pytest.ini_options]

from __future__ import annotations

from pathlib import Path

import pytest

from web_overlay.config import RenderConfig
from web_overlay.exceptions import (
    ChromiumNotInstalledError,
    WaitForTimeoutError,
    WebmEncodeError,
)
from web_overlay.overlay import HtmlOverlay

# ---------------------------------------------------------------------------
# ChromiumNotInstalledError
# ---------------------------------------------------------------------------

_SIMPLE_HTML = (
    "<!DOCTYPE html><html><head><style>body{margin:0;background:transparent;}</style></head>"
    "<body></body></html>"
)


def test_missing_chromium_raises_chromium_not_installed_error(tmp_path: Path) -> None:
    """Passing a nonexistent chromium_executable_path raises ChromiumNotInstalledError."""
    config = RenderConfig(
        fps=10,
        width=320,
        height=240,
        chromium_executable_path="/nonexistent/path/to/chromium-binary-xyz",
        cleanup_pngs=False,
    )
    overlay = HtmlOverlay(html=_SIMPLE_HTML, width=320, height=240, duration=0.1, fps=10)
    with pytest.raises(ChromiumNotInstalledError):
        overlay.render(tmp_path / "out", config=config)


def test_missing_chromium_message_mentions_setup_command(tmp_path: Path) -> None:
    """The ChromiumNotInstalledError message tells the user to run `web-overlay setup`."""
    config = RenderConfig(
        fps=10,
        width=320,
        height=240,
        chromium_executable_path="/nonexistent/path/to/chromium-binary-xyz",
        cleanup_pngs=False,
    )
    overlay = HtmlOverlay(html=_SIMPLE_HTML, width=320, height=240, duration=0.1, fps=10)
    with pytest.raises(ChromiumNotInstalledError) as exc_info:
        overlay.render(tmp_path / "out", config=config)
    assert "web-overlay setup" in str(exc_info.value)


# ---------------------------------------------------------------------------
# WaitForTimeoutError — requires real Chromium
# ---------------------------------------------------------------------------

_NONEXISTENT_SELECTOR = "#nonexistent-id-xyz-9999"


@pytest.mark.chromium
def test_bad_wait_for_selector_raises_wait_for_timeout_error() -> None:
    """inject_content raises WaitForTimeoutError when wait_for selector is absent.

    We call inject_content directly because HtmlOverlay.render() currently
    passes html through render_to_pngs without forwarding wait_for to the
    browser layer.  This test exercises the public exception contract.
    """
    import asyncio

    from web_overlay.browser import create_page, inject_content, launch_browser

    async def _run() -> None:
        config = RenderConfig(fps=10, width=320, height=240)
        pw, browser = await launch_browser(config)
        try:
            page = await create_page(browser, 320, 240)
            await inject_content(
                page,
                _SIMPLE_HTML,
                wait_for=_NONEXISTENT_SELECTOR,
                wait_for_timeout=0.5,
            )
        finally:
            await browser.close()
            await pw.stop()

    with pytest.raises(WaitForTimeoutError) as exc_info:
        asyncio.run(_run())
    assert exc_info.value.selector == _NONEXISTENT_SELECTOR


@pytest.mark.chromium
def test_bad_selector_message_contains_selector_string() -> None:
    """The WaitForTimeoutError message contains the offending selector string."""
    import asyncio

    from web_overlay.browser import create_page, inject_content, launch_browser

    async def _run() -> None:
        config = RenderConfig(fps=10, width=320, height=240)
        pw, browser = await launch_browser(config)
        try:
            page = await create_page(browser, 320, 240)
            await inject_content(
                page,
                _SIMPLE_HTML,
                wait_for=_NONEXISTENT_SELECTOR,
                wait_for_timeout=0.5,
            )
        finally:
            await browser.close()
            await pw.stop()

    with pytest.raises(WaitForTimeoutError) as exc_info:
        asyncio.run(_run())
    assert _NONEXISTENT_SELECTOR in str(exc_info.value)


# ---------------------------------------------------------------------------
# WebmEncodeError
# ---------------------------------------------------------------------------


def test_missing_ffmpeg_raises_webm_encode_error(tmp_path: Path) -> None:
    """encode_webm raises WebmEncodeError when ffmpeg_binary does not exist on PATH."""
    from web_overlay.models import OverlayResult
    from web_overlay.webm_encoder import encode_webm

    # Build a fake OverlayResult pointing at an empty directory.
    fake_dir = tmp_path / "frames"
    fake_dir.mkdir()
    result = OverlayResult(
        output_dir=fake_dir,
        frame_count=1,
        fps=10,
        width=320,
        height=240,
        duration=0.1,
        pattern="frame_%05d.png",
    )
    bad_config = RenderConfig(ffmpeg_binary="nonexistent-ffmpeg-xxx")

    with pytest.raises(WebmEncodeError):
        encode_webm(result, tmp_path / "out.webm", bad_config)


def test_missing_ffmpeg_message_contains_binary_name(tmp_path: Path) -> None:
    """The WebmEncodeError message contains the name of the missing ffmpeg binary."""
    from web_overlay.models import OverlayResult
    from web_overlay.webm_encoder import encode_webm

    fake_dir = tmp_path / "frames"
    fake_dir.mkdir()
    result = OverlayResult(
        output_dir=fake_dir,
        frame_count=1,
        fps=10,
        width=320,
        height=240,
        duration=0.1,
        pattern="frame_%05d.png",
    )
    bad_binary = "nonexistent-ffmpeg-xxx"
    bad_config = RenderConfig(ffmpeg_binary=bad_binary)

    with pytest.raises(WebmEncodeError) as exc_info:
        encode_webm(result, tmp_path / "out.webm", bad_config)
    assert bad_binary in str(exc_info.value)


# ---------------------------------------------------------------------------
# WaitForTimeoutError direct construction
# ---------------------------------------------------------------------------


def test_wait_for_timeout_error_stores_selector() -> None:
    """WaitForTimeoutError.selector attribute matches the selector passed to __init__."""
    exc = WaitForTimeoutError("#my-selector")
    assert exc.selector == "#my-selector"


def test_wait_for_timeout_error_message_includes_selector() -> None:
    """The string representation of WaitForTimeoutError contains the selector."""
    exc = WaitForTimeoutError("#my-selector")
    assert "#my-selector" in str(exc)


def test_chromium_not_installed_error_is_runtime_error() -> None:
    """ChromiumNotInstalledError inherits from RuntimeError."""
    assert issubclass(ChromiumNotInstalledError, RuntimeError)


def test_webm_encode_error_is_runtime_error() -> None:
    """WebmEncodeError inherits from RuntimeError."""
    assert issubclass(WebmEncodeError, RuntimeError)
