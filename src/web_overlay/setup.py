# Filepath: src/web_overlay/setup.py
# Condensed Description: Runs `playwright install chromium` to download the Chromium browser.
# Architecture Layer: Infrastructure / Setup
# Environment: Local
# Script Hierarchy: web-overlay → src/web_overlay/setup
# Dependencies: Internal: exceptions / External: none
# Exposes: install_chromium
# Configuration: N/A

from __future__ import annotations

# MIT License — Copyright 2026 Trollfabriken AITrix AB
import logging
import subprocess

from web_overlay.exceptions import ChromiumNotInstalledError

logger = logging.getLogger(__name__)


def install_chromium() -> None:
    """Run ``playwright install chromium`` to download the Chromium browser.

    Streams output directly to the terminal so the user can see download
    progress.  This function is called by the ``web-overlay setup`` CLI
    subcommand.

    Raises:
        ChromiumNotInstalledError: If the ``playwright install chromium``
            command exits with a non-zero return code.
    """
    logger.info("Running: playwright install chromium")
    result = subprocess.run(
        ["playwright", "install", "chromium"],
        capture_output=False,
    )
    if result.returncode != 0:
        raise ChromiumNotInstalledError(
            f"'playwright install chromium' failed with exit code {result.returncode}. "
            f"Try: pip install playwright && playwright install chromium"
        )
    logger.info("Chromium installed successfully.")
