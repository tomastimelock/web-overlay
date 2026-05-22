# Filepath: web-overlay/tests/test_inspect_template.py
# Condensed Description: Tests for the web-overlay inspect subcommand — variable listing behaviour.
# Architecture Layer: tests
# Environment: test
# Script Hierarchy: test
# Dependencies: pytest, web_overlay
# Exposes: test_inspect_lists_all_variables, test_inspect_no_variables_outputs_empty, test_inspect_nested_variables_found, test_inspect_cli_exit_zero
# Configuration: pytest.ini / pyproject.toml [tool.pytest.ini_options]

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the web-overlay CLI, falling back to python -c if the script is absent."""
    cmd = ["web-overlay", *args]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        pass
    fallback = [
        sys.executable,
        "-c",
        "import sys; from web_overlay.cli import main; sys.exit(main())",
        *args,
    ]
    return subprocess.run(fallback, capture_output=True, text=True, check=False)


def test_inspect_lists_all_variables(tmp_path: Path) -> None:
    """inspect outputs both {{ name }} and {{ title }} when both appear in the template."""
    template = tmp_path / "tmpl.html"
    template.write_text(
        "<p>{{ name }}</p><p>{{ title }}</p>",
        encoding="utf-8",
    )
    r = run_cli("inspect", str(template))
    assert r.returncode == 0, f"inspect exited {r.returncode}:\n{r.stderr}"
    output_lines = r.stdout.strip().splitlines()
    assert "name" in output_lines
    assert "title" in output_lines


def test_inspect_no_variables_outputs_empty(tmp_path: Path) -> None:
    """inspect outputs the 'no variables' message for a template with no placeholders."""
    template = tmp_path / "static.html"
    template.write_text("<p>plain content</p>", encoding="utf-8")
    r = run_cli("inspect", str(template))
    assert r.returncode == 0
    # The CLI prints "(no Jinja2 variables found)" when the list is empty.
    assert "no" in r.stdout.lower() or r.stdout.strip() == ""


def test_inspect_nested_variables_found(tmp_path: Path) -> None:
    """Variables inside a {% for %} loop body are included in the inspect output."""
    template = tmp_path / "loop.html"
    # In Jinja2, `items` is undeclared (passed from outside); `x` is the loop var (declared).
    template.write_text(
        "{% for x in items %}<p>{{ x }}</p>{% endfor %}",
        encoding="utf-8",
    )
    r = run_cli("inspect", str(template))
    assert r.returncode == 0
    # `items` must appear; `x` is declared by the for-loop, so it may or may not appear.
    assert "items" in r.stdout


def test_inspect_cli_exit_zero(tmp_path: Path) -> None:
    """web-overlay inspect <template> exits 0 for a valid template file."""
    template = tmp_path / "valid.html"
    template.write_text("{{ greeting }}, world!", encoding="utf-8")
    r = run_cli("inspect", str(template))
    assert r.returncode == 0


def test_inspect_missing_file_exits_nonzero(tmp_path: Path) -> None:
    """web-overlay inspect reports an error and exits non-zero for a missing file."""
    missing = tmp_path / "does_not_exist.html"
    r = run_cli("inspect", str(missing))
    assert r.returncode != 0
    assert "error" in r.stderr.lower() or "not found" in r.stderr.lower()


def test_inspect_single_variable_listed(tmp_path: Path) -> None:
    """A template with one {{ x }} placeholder produces exactly one variable name in output."""
    template = tmp_path / "single.html"
    template.write_text("{{ x }}", encoding="utf-8")
    r = run_cli("inspect", str(template))
    assert r.returncode == 0
    output_lines = [line.strip() for line in r.stdout.strip().splitlines() if line.strip()]
    assert output_lines == ["x"]
