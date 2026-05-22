# Filepath: web-overlay/tests/test_cli_smoke.py
# Condensed Description: CLI smoke tests — --help exits, render/inspect/setup subcommands behave correctly.
# Architecture Layer: tests
# Environment: test
# Script Hierarchy: test
# Dependencies: pytest, web_overlay
# Exposes: test_help_exits_zero, test_render_help, test_inspect_help, test_setup_help, test_render_html_produces_pngs, test_render_svg_produces_pngs, test_render_webm_flag_produces_webm
# Configuration: pytest.ini / pyproject.toml [tool.pytest.ini_options]

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the web-overlay CLI, falling back to python -m if the script is absent."""
    cmd = ["web-overlay", *args]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        pass
    # Fallback: invoke via the interpreter so tests work even without the script installed.
    fallback = [
        sys.executable,
        "-c",
        "import sys; from web_overlay.cli import main; sys.exit(main())",
        *args,
    ]
    return subprocess.run(fallback, capture_output=True, text=True, check=False)


# ---------------------------------------------------------------------------
# Pure-Python CLI tests (no Chromium / ffmpeg needed)
# ---------------------------------------------------------------------------


def test_help_exits_zero() -> None:
    """web-overlay --help exits with code 0."""
    r = run_cli("--help")
    assert r.returncode == 0


def test_help_output_mentions_usage() -> None:
    """web-overlay --help output contains 'usage' (case-insensitive)."""
    r = run_cli("--help")
    assert "usage" in r.stdout.lower()


def test_render_help() -> None:
    """web-overlay render --help exits with code 0."""
    r = run_cli("render", "--help")
    assert r.returncode == 0


def test_inspect_help() -> None:
    """web-overlay inspect --help exits with code 0."""
    r = run_cli("inspect", "--help")
    assert r.returncode == 0


def test_setup_help() -> None:
    """web-overlay setup --help exits with code 0."""
    r = run_cli("setup", "--help")
    assert r.returncode == 0


def test_version_flag() -> None:
    """web-overlay --version exits with code 0 and prints the version string."""
    r = run_cli("--version")
    assert r.returncode == 0
    assert "0.1.0" in r.stdout


def test_no_subcommand_exits_nonzero() -> None:
    """Invoking web-overlay without a subcommand exits with a non-zero code."""
    r = run_cli()
    assert r.returncode != 0


# ---------------------------------------------------------------------------
# Chromium-dependent CLI tests
# ---------------------------------------------------------------------------

_SIMPLE_HTML_CONTENT = (
    "<!DOCTYPE html><html><head><style>"
    "body{margin:0;background:transparent;}"
    "</style></head><body>"
    "<div style='width:40px;height:40px;background:rgba(0,200,100,0.9);'></div>"
    "</body></html>"
)

_SIMPLE_SVG_CONTENT = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="240">'
    '<rect x="10" y="10" width="80" height="80" fill="rgba(200,100,0,0.9)"/>'
    "</svg>"
)


@pytest.mark.chromium
def test_render_html_produces_pngs(tmp_path: Path) -> None:
    """CLI render --html ... --output DIR creates PNG files in the output directory."""
    out_dir = tmp_path / "html_out"
    out_dir.mkdir()
    r = run_cli(
        "render",
        "--html",
        _SIMPLE_HTML_CONTENT,
        "--duration",
        "0.3",
        "--fps",
        "10",
        "--width",
        "320",
        "--height",
        "240",
        "--output",
        str(out_dir),
    )
    assert r.returncode == 0, f"CLI exited {r.returncode}:\n{r.stderr}"
    pngs = list(out_dir.glob("*.png"))
    assert len(pngs) > 0, "No PNG files produced by CLI render"


@pytest.mark.chromium
def test_render_svg_produces_pngs(tmp_path: Path) -> None:
    """CLI render --svg FILE --output DIR creates PNG files for an SVG source."""
    svg_file = tmp_path / "test.svg"
    svg_file.write_text(_SIMPLE_SVG_CONTENT, encoding="utf-8")
    out_dir = tmp_path / "svg_out"
    out_dir.mkdir()
    r = run_cli(
        "render",
        "--svg",
        str(svg_file),
        "--duration",
        "0.3",
        "--fps",
        "10",
        "--width",
        "320",
        "--height",
        "240",
        "--output",
        str(out_dir),
    )
    assert r.returncode == 0, f"CLI exited {r.returncode}:\n{r.stderr}"
    pngs = list(out_dir.glob("*.png"))
    assert len(pngs) > 0, "No PNG files produced by CLI render for SVG source"


@pytest.mark.chromium
@pytest.mark.ffmpeg
def test_render_webm_flag_produces_webm(tmp_path: Path) -> None:
    """CLI render --html ... --webm PATH creates a .webm file."""
    webm_out = tmp_path / "out.webm"
    r = run_cli(
        "render",
        "--html",
        _SIMPLE_HTML_CONTENT,
        "--duration",
        "0.3",
        "--fps",
        "10",
        "--width",
        "320",
        "--height",
        "240",
        "--webm",
        str(webm_out),
    )
    assert r.returncode == 0, f"CLI exited {r.returncode}:\n{r.stderr}"
    assert webm_out.exists(), "WebM file not created by CLI --webm flag"
    assert webm_out.stat().st_size > 0, "WebM file is empty"
