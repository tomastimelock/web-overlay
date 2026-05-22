# Filepath: src/web_overlay/browser.py
# Condensed Description: Async Playwright helpers for launching browser, creating pages, and injecting content.
# Architecture Layer: Infrastructure / Playwright
# Environment: Local
# Script Hierarchy: web-overlay → src/web_overlay/browser
# Dependencies: Internal: config, exceptions / External: playwright>=1.40
# Exposes: launch_browser, create_page, inject_content
# Configuration: RenderConfig

from __future__ import annotations

# MIT License — Copyright 2026 Trollfabriken AITrix AB
import logging

from playwright.async_api import (
    Browser,
    Page,
    Playwright,
    async_playwright,
)

from web_overlay.config import RenderConfig
from web_overlay.exceptions import ChromiumNotInstalledError, WaitForTimeoutError

logger = logging.getLogger(__name__)

_CHROMIUM_NOT_INSTALLED_PHRASES = (
    "Executable doesn't exist",
    "executable doesn't exist",
    "playwright install",
)


async def launch_browser(config: RenderConfig) -> tuple[Playwright, Browser]:
    """Launch a headless Chromium browser instance.

    Args:
        config: Rendering configuration; ``chromium_executable_path`` and
            ``chromium_args`` are forwarded to Playwright.

    Returns:
        A ``(playwright_instance, browser)`` tuple. Both must be closed by
        the caller (``await browser.close()`` then ``await playwright_instance.stop()``).

    Raises:
        ChromiumNotInstalledError: When Playwright cannot find the Chromium
            binary. Run ``web-overlay setup`` to install it.
    """
    pw = await async_playwright().start()
    launch_kwargs: dict = {
        "headless": True,
        "args": list(config.chromium_args),
    }
    if config.chromium_executable_path:
        launch_kwargs["executable_path"] = config.chromium_executable_path

    try:
        browser = await pw.chromium.launch(**launch_kwargs)
    except Exception as exc:
        await pw.stop()
        msg = str(exc)
        if any(phrase in msg for phrase in _CHROMIUM_NOT_INSTALLED_PHRASES):
            raise ChromiumNotInstalledError(
                f"Playwright Chromium is not installed. "
                f"Run `web-overlay setup` or `playwright install chromium` to download it. "
                f"Original error: {msg}"
            ) from exc
        raise

    logger.debug("Chromium browser launched successfully.")
    return pw, browser


async def create_page(
    browser: Browser,
    width: int,
    height: int,
    device_scale_factor: float = 1.0,
) -> Page:
    """Create a new browser page with the given viewport dimensions.

    Args:
        browser: An already-launched Playwright ``Browser`` instance.
        width: Logical viewport width in CSS pixels.
        height: Logical viewport height in CSS pixels.
        device_scale_factor: Pixel ratio. ``2.0`` doubles the physical pixel
            resolution for HiDPI output.

    Returns:
        A configured ``Page`` ready for ``inject_content()``.
    """
    page = await browser.new_page(
        viewport={"width": width, "height": height},
        device_scale_factor=device_scale_factor,
    )
    logger.debug(f"Page created: {width}x{height} @ {device_scale_factor}x device pixel ratio.")
    return page


async def inject_content(
    page: Page,
    html: str,
    wait_for: str | None = None,
    wait_for_function: str | None = None,
    wait_for_timeout: float = 10.0,
) -> None:
    """Set page HTML content and wait for fonts, optional selector, and optional JS function.

    Args:
        page: The Playwright ``Page`` to inject content into.
        html: Full HTML document string.
        wait_for: CSS selector that must be visible before frame capture begins.
        wait_for_function: JavaScript expression (returning a truthy value) that
            must evaluate to ``true`` before frame capture begins.
        wait_for_timeout: Maximum seconds to wait for ``wait_for`` / ``wait_for_function``.

    Raises:
        WaitForTimeoutError: If ``wait_for`` or ``wait_for_function`` does not
            become truthy within ``wait_for_timeout`` seconds. The timed-out
            selector/expression string is stored on the exception.
    """
    await page.set_content(html, wait_until="load")
    await page.evaluate("() => document.fonts.ready")
    logger.debug("Page content set and web fonts loaded.")

    if wait_for:
        try:
            await page.wait_for_selector(wait_for, timeout=wait_for_timeout * 1000)
            logger.debug(f"wait_for selector {wait_for!r} found.")
        except Exception as exc:
            raise WaitForTimeoutError(wait_for) from exc

    if wait_for_function:
        try:
            await page.wait_for_function(wait_for_function, timeout=wait_for_timeout * 1000)
            logger.debug("wait_for_function resolved successfully.")
        except Exception as exc:
            raise WaitForTimeoutError(wait_for_function) from exc
