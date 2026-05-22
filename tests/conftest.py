# Filepath: web-overlay/tests/conftest.py
# Condensed Description: Shared pytest fixtures for all web-overlay tests.
# Architecture Layer: tests
# Environment: test
# Script Hierarchy: test
# Dependencies: pytest, web_overlay
# Exposes: tmp_output_dir, simple_html_template, animated_html_template, simple_svg_template, test_render_config, skip_without_chromium, skip_without_ffmpeg
# Configuration: pytest.ini / pyproject.toml [tool.pytest.ini_options]

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from web_overlay.config import RenderConfig

# ---------------------------------------------------------------------------
# Directory fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """A fresh temporary subdirectory for each test."""
    out = tmp_path / "output"
    out.mkdir()
    return out


# ---------------------------------------------------------------------------
# Template fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_html_template() -> str:
    """Minimal HTML string with a {{ title }} placeholder and transparent background."""
    return (
        "<!DOCTYPE html>"
        "<html><head><style>"
        "body { margin: 0; background: transparent; }"
        ".title { font: bold 48px sans-serif; color: white; padding: 20px; }"
        "</style></head>"
        "<body><div class='title'>{{ title }}</div></body></html>"
    )


@pytest.fixture
def animated_html_template() -> str:
    """HTML with a CSS keyframe animation — box slides across the viewport."""
    return """<!DOCTYPE html>
<html>
<head>
<style>
body { margin: 0; background: transparent; }
.box {
    width: 60px;
    height: 60px;
    background: rgba(255, 0, 0, 0.9);
    animation: slide 1s linear infinite;
}
@keyframes slide {
    from { transform: translateX(0); }
    to   { transform: translateX(260px); }
}
</style>
</head>
<body><div class="box"></div></body>
</html>"""


@pytest.fixture
def simple_svg_template() -> str:
    """Minimal SVG string with a {{ title }} placeholder."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="240">'
        '<text x="10" y="50" font-size="40" fill="white">{{ title }}</text>'
        "</svg>"
    )


# ---------------------------------------------------------------------------
# Config fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def test_render_config() -> RenderConfig:
    """Low-fps RenderConfig suitable for fast tests."""
    return RenderConfig(fps=10, width=320, height=240, cleanup_pngs=False)


# ---------------------------------------------------------------------------
# Skip markers / guards
# ---------------------------------------------------------------------------


def _chromium_is_available() -> bool:
    """Return True if Playwright Chromium binary can actually be launched."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        return False


def _ffmpeg_is_available() -> bool:
    """Return True if ffmpeg is on PATH."""
    return shutil.which("ffmpeg") is not None


@pytest.fixture
def skip_without_chromium() -> None:
    """Skip the test when Playwright Chromium is not installed."""
    if not _chromium_is_available():
        pytest.skip("Playwright Chromium not installed — run `web-overlay setup`")


@pytest.fixture
def skip_without_ffmpeg() -> None:
    """Skip the test when ffmpeg is not on PATH."""
    if not _ffmpeg_is_available():
        pytest.skip("ffmpeg not found on PATH")


# ---------------------------------------------------------------------------
# Hook: auto-skip tests marked with chromium / ffmpeg if binary unavailable
# ---------------------------------------------------------------------------


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    chromium_ok: bool | None = None
    ffmpeg_ok: bool | None = None

    for item in items:
        if item.get_closest_marker("chromium"):
            if chromium_ok is None:
                chromium_ok = _chromium_is_available()
            if not chromium_ok:
                item.add_marker(
                    pytest.mark.skip(
                        reason="Playwright Chromium not installed — run `web-overlay setup`"
                    )
                )

        if item.get_closest_marker("ffmpeg"):
            if ffmpeg_ok is None:
                ffmpeg_ok = _ffmpeg_is_available()
            if not ffmpeg_ok:
                item.add_marker(pytest.mark.skip(reason="ffmpeg not found on PATH"))


# ---------------------------------------------------------------------------
# Probe helpers (used by individual test modules via import)
# ---------------------------------------------------------------------------


def probe_duration(path: Path) -> float:
    """Return the duration in seconds of a media file via ffprobe."""
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(r.stdout.strip())
