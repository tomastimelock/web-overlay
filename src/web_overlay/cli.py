# Filepath: src/web_overlay/cli.py
# Condensed Description: argparse CLI with render, inspect, and setup subcommands.
# Architecture Layer: CLI
# Environment: Local
# Script Hierarchy: web-overlay → src/web_overlay/cli
# Dependencies: Internal: overlay, template, config, setup, exceptions / External: none
# Exposes: main
# Configuration: RenderConfig

from __future__ import annotations

# MIT License — Copyright 2026 Trollfabriken AITrix AB
import argparse
import logging
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="web-overlay",
        description="Render HTML/SVG templates to transparent PNG or WebM overlays.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version and exit.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging and ffmpeg output.",
    )

    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # ------------------------------------------------------------------ render
    p_render = sub.add_parser("render", help="Render an overlay to PNG sequence or WebM.")
    src_group = p_render.add_mutually_exclusive_group()
    src_group.add_argument("--template", metavar="PATH", help="Path to an HTML template file.")
    src_group.add_argument("--svg", metavar="PATH", help="Path to an SVG file.")
    src_group.add_argument("--html", metavar="STRING", help="Inline HTML string.")
    p_render.add_argument(
        "--data",
        metavar="KEY=VALUE",
        action="append",
        dest="data",
        default=[],
        help="Jinja2 variable binding (repeatable, e.g. --data name=Tomas).",
    )
    p_render.add_argument(
        "--duration",
        type=float,
        default=5.0,
        metavar="SECONDS",
        help="Overlay duration in seconds (default: 5.0).",
    )
    p_render.add_argument(
        "--fps",
        type=int,
        default=30,
        metavar="INT",
        help="Frames per second (default: 30).",
    )
    p_render.add_argument(
        "--width",
        type=int,
        default=1920,
        metavar="INT",
        help="Viewport width in pixels (default: 1920).",
    )
    p_render.add_argument(
        "--height",
        type=int,
        default=1080,
        metavar="INT",
        help="Viewport height in pixels (default: 1080).",
    )
    output_group = p_render.add_mutually_exclusive_group()
    output_group.add_argument(
        "--output",
        metavar="DIR",
        help="Output directory for PNG sequence.",
    )
    output_group.add_argument(
        "--webm",
        metavar="PATH",
        help="Encode to VP9-alpha WebM instead of PNG sequence.",
    )

    # ---------------------------------------------------------------- inspect
    p_inspect = sub.add_parser(
        "inspect",
        help="List Jinja2 variables in a template file.",
    )
    p_inspect.add_argument(
        "template",
        metavar="TEMPLATE",
        help="Path to the HTML or SVG template file.",
    )

    # ------------------------------------------------------------------ setup
    sub.add_parser(
        "setup",
        help="Install Playwright Chromium (required once before rendering).",
    )

    return parser


def _parse_data(pairs: list[str]) -> dict[str, str]:
    """Parse ``KEY=VALUE`` strings into a dict.

    Args:
        pairs: List of ``"key=value"`` strings from ``--data`` arguments.

    Returns:
        Dict mapping each key to its value string.

    Raises:
        SystemExit: If any pair does not contain ``=``.
    """
    result: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            print(
                f"error: --data argument must be KEY=VALUE, got {pair!r}",
                file=sys.stderr,
            )
            sys.exit(2)
        key, _, value = pair.partition("=")
        result[key.strip()] = value
    return result


def cmd_render(args: argparse.Namespace) -> int:
    """Execute the ``render`` subcommand.

    Args:
        args: Parsed argument namespace.

    Returns:
        Exit code (0 on success, non-zero on error).
    """
    from web_overlay.config import RenderConfig
    from web_overlay.exceptions import (
        ChromiumNotInstalledError,
        FrameCaptureError,
        TemplateRenderError,
        WebmEncodeError,
    )
    from web_overlay.overlay import HtmlOverlay, SvgOverlay

    if args.template is None and args.svg is None and args.html is None:
        print(
            "error: one of --template, --svg, or --html is required.",
            file=sys.stderr,
        )
        return 2

    if args.webm is None and args.output is None:
        print(
            "error: one of --output (PNG dir) or --webm (WebM path) is required.",
            file=sys.stderr,
        )
        return 2

    data = _parse_data(args.data)
    config = RenderConfig(
        fps=args.fps,
        width=args.width,
        height=args.height,
        verbose=args.verbose,
    )

    try:
        if args.svg:
            overlay: HtmlOverlay | SvgOverlay = SvgOverlay(
                svg=args.svg,
                data=data or None,
                width=args.width,
                height=args.height,
                duration=args.duration,
                fps=args.fps,
            )
        else:
            overlay = HtmlOverlay(
                template=args.template,
                html=args.html,
                data=data or None,
                width=args.width,
                height=args.height,
                duration=args.duration,
                fps=args.fps,
            )

        if args.webm:
            out_path = overlay.render_webm(args.webm, config=config)
            print(str(out_path))
        else:
            result = overlay.render(args.output, config=config)
            print(str(result.output_dir))

    except TemplateRenderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except ChromiumNotInstalledError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (FrameCaptureError, WebmEncodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    """Execute the ``inspect`` subcommand.

    Args:
        args: Parsed argument namespace.

    Returns:
        Exit code (0 on success, non-zero on error).
    """
    from web_overlay.exceptions import TemplateRenderError
    from web_overlay.template import extract_variables

    template_path = Path(args.template)
    if not template_path.exists():
        print(f"error: template file not found: {template_path}", file=sys.stderr)
        return 1

    try:
        source = template_path.read_text(encoding="utf-8")
        variables = extract_variables(source)
    except TemplateRenderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if variables:
        for var in variables:
            print(var)
    else:
        print("(no Jinja2 variables found)")

    return 0


def cmd_setup(args: argparse.Namespace) -> int:
    """Execute the ``setup`` subcommand.

    Args:
        args: Parsed argument namespace (unused).

    Returns:
        Exit code (0 on success, non-zero on error).
    """
    from web_overlay.exceptions import ChromiumNotInstalledError
    from web_overlay.setup import install_chromium

    try:
        install_chromium()
    except ChromiumNotInstalledError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``web-overlay`` CLI.

    Args:
        argv: Argument list; defaults to ``sys.argv[1:]`` when ``None``.

    Returns:
        Exit code suitable for ``sys.exit()``.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s", stream=sys.stderr)

    if args.version:
        from web_overlay import __version__

        print(__version__)
        return 0

    if args.command is None:
        parser.print_help(sys.stderr)
        return 2

    dispatch = {
        "render": cmd_render,
        "inspect": cmd_inspect,
        "setup": cmd_setup,
    }

    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
