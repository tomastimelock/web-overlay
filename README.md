# web-overlay

HTML / CSS / SVG → transparent overlay sequence — Playwright renders it, ffmpeg composites it.

The CineForge and MusicVideoCreator pipelines at Trollfabriken AITrix AB needed animated lower-thirds,
countdown timers, and Swedish-language title cards rendered as transparent overlays. Every existing option
was either `ffmpeg drawtext` (no CSS, no web fonts) or a commercial SaaS API charging per render.
`web-overlay` closes that gap: Playwright renders the HTML exactly as a browser would; ffmpeg composites
the result onto video. Renders 150 frames of animated HTML at 1920x1080 in under 60 seconds on a standard
CI runner — no external services, no per-render billing, runs entirely on your machine.

MIT licensed.

---

## What it solves

| Previous problem | Solution |
|---|---|
| ffmpeg's `drawtext` filter is the only Python option — no CSS, no web fonts, no animations | Render any HTML/CSS as a transparent overlay sequence |
| Commercial APIs (json2video, Shotstack, Creatomate) charge for this feature | Open-source library, runs locally |
| Hand-rolled Playwright + ffmpeg scripts are fragile | First-class `HtmlOverlay` and `SvgOverlay` classes |
| CSS animations render with non-deterministic timing | Deterministic capture by advancing `document.timeline.currentTime` |
| Web fonts cause first-few-frames fallback flicker | Wait for `document.fonts.ready` before frame 0 |
| Swedish / non-ASCII text shows as boxes in most overlay tools | Browser-grade text rendering with shaping |
| PNG sequences eat disk space | Optional VP9-alpha WebM encoding for reuse |

---

## Installation

```
pip install web-overlay
```

Then install the Playwright Chromium browser (one-time, per machine):

```
web-overlay setup
```

That command runs `playwright install chromium`. The browser is ~180 MB. It is stored under
`~/.cache/ms-playwright/` and does not require root.

With optional extras:

```
pip install "web-overlay[arrange]"   # video-arrange integration for timeline compositing
pip install "web-overlay[dev]"       # pytest, ruff, pillow — for contributors
```

**Runtime requirement:** ffmpeg must be on PATH.

- macOS: `brew install ffmpeg`
- Linux: `apt install ffmpeg`
- Windows: `winget install Gyan.FFmpeg`

---

## Quick start

```python
from web_overlay import HtmlOverlay, SvgOverlay, RenderConfig

# HTML overlay from an inline template — Jinja2 variables supported
overlay = HtmlOverlay(
    template="<html><body style='margin:0;background:transparent'>"
             "<h1 style='color:white;font-size:5vw'>{{ title }}</h1>"
             "</body></html>",
    data={"title": "Trollfabriken AITrix AB"},
    duration=5.0,
    fps=30,
)

# Render to a PNG sequence: overlays/frame_0000.png … overlays/frame_0149.png
cfg = RenderConfig(width=1920, height=1080, fps=30)
overlay.render_png_sequence("overlays/", config=cfg)

# Or render directly to a VP9-alpha WebM for reuse across projects
overlay.render_webm("title_card.webm", config=cfg)

# SVG overlay works identically — pass raw SVG markup or a file path
svg = SvgOverlay(
    template_path="assets/countdown.svg.j2",
    data={"seconds": 10},
    duration=10.0,
    fps=30,
)
svg.render_png_sequence("countdown_frames/", config=cfg)

# Composite the overlay onto a source video using ffmpeg directly
from web_overlay import composite

composite(
    base="interview.mp4",
    overlay_webm="title_card.webm",
    at=2.0,
    output="interview_titled.mp4",
)
```

---

## The pipeline

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │                           web-overlay                                │
  │                                                                      │
  │  ① HtmlOverlay / SvgOverlay — template + data + RenderConfig         │
  │              │                                                        │
  │              ▼                                                        │
  │  ② Jinja2 renders template → full HTML/SVG string                    │
  │              │                                                        │
  │              ▼                                                        │
  │  ③ Playwright Chromium opens page (transparent background)           │
  │    Waits for document.fonts.ready                                     │
  │    Advances document.timeline.currentTime per frame (deterministic)  │
  │    Screenshots each frame as RGBA PNG                                 │
  │              │                                                        │
  │              ▼                                                        │
  │  ④ PNG frames written to output directory                            │
  │              │                                                        │
  │              ▼                                                        │
  │  ⑤ ffmpeg encodes PNG sequence → VP9-alpha WebM  (optional)         │
  │    libvpx-vp9, pix_fmt yuva420p, one subprocess call                 │
  │              │                                                        │
  │              ▼                                                        │
  │  ⑥ output.webm (or PNG sequence) — ready to composite               │
  └──────────────────────────────────────────────────────────────────────┘
```

---

## Configuration

```python
from web_overlay import RenderConfig

cfg = RenderConfig(
    width=1920,           # canvas width — should match your video dimensions
    height=1080,          # canvas height
    fps=30,               # frames per second
    video_codec="libvpx-vp9",   # VP9 for alpha channel support
    pixel_format="yuva420p",    # yuva keeps the alpha plane
    crf=20,               # lower = higher quality; 18–28 typical for VP9
    ffmpeg_binary="ffmpeg",
    chromium_channel="chromium",  # passed to Playwright
    page_load_timeout=10_000,     # ms; increase for heavy web fonts
    extra_chromium_args=[],       # passed to browser.new_context()
    verbose_ffmpeg=False,
)
```

| Field | Default | Notes |
|---|---|---|
| `width` | `1920` | Canvas width in pixels |
| `height` | `1080` | Canvas height in pixels |
| `fps` | `30` | Output frame rate |
| `video_codec` | `"libvpx-vp9"` | VP9 is the only free codec with alpha |
| `pixel_format` | `"yuva420p"` | Preserves alpha; required for VP9 transparency |
| `crf` | `20` | Constant rate factor; lower = larger file |
| `ffmpeg_binary` | `"ffmpeg"` | Path to ffmpeg binary |
| `chromium_channel` | `"chromium"` | Playwright browser channel |
| `page_load_timeout` | `10000` | Page load timeout in milliseconds |
| `extra_chromium_args` | `[]` | Extra args forwarded to Playwright context |
| `verbose_ffmpeg` | `False` | Pass ffmpeg stderr through to stdout |

---

## Templates

HTML and SVG templates are processed with Jinja2 before being loaded into Playwright.

**Transparent background.** Always set:

```html
<html>
<head>
  <style>
    html, body {
      margin: 0;
      padding: 0;
      background: transparent;
    }
  </style>
</head>
<body>
  {{ content }}
</body>
</html>
```

Playwright is launched with `--default-background-color=00000000` so the page background is
transparent. Any element you do not paint remains transparent in the PNG output.

**Sizing.** Use `vw`/`vh` units so the template adapts to whatever `RenderConfig.width/height`
you pass. Or set explicit pixel sizes matching the config:

```css
.card {
  width: 960px;   /* half of a 1920-wide canvas */
  height: 200px;
}
```

**Jinja2 variables.** Pass a `data` dict to `HtmlOverlay` or `SvgOverlay`. Reference fields
with `{{ field_name }}` in the template:

```html
<p class="title">{{ title }}</p>
<p class="subtitle">{{ subtitle }}</p>
```

```python
HtmlOverlay(template_path="card.html.j2", data={"title": "Act I", "subtitle": "The Beginning"})
```

**CSS animations.** `web-overlay` advances `document.timeline.currentTime` by `1000 / fps`
milliseconds between each frame capture. CSS `animation-play-state: paused` and a manual
`currentTime` override give you deterministic, frame-accurate animation. Example:

```css
@keyframes fade-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}

.title {
  animation: fade-in 1s ease both;
  animation-play-state: paused;
}
```

The renderer sets `animationPlayState` and steps the clock. No timing jitter.

**Web fonts.** Load fonts via `<link>` or `@import`. The renderer calls
`await page.evaluate("document.fonts.ready")` before capturing frame 0. Fonts are guaranteed
loaded; no fallback-font flicker in the first frames.

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap" rel="stylesheet">
```

For offline rendering, embed fonts as base64 data URIs in a `<style>` block.

---

## CLI

```bash
# Install the Playwright Chromium browser (run once after pip install)
web-overlay setup

# Render an HTML template to a PNG sequence
web-overlay render card.html.j2 \
  --data '{"title": "Act I", "subtitle": "The Beginning"}' \
  --duration 5.0 --fps 30 --width 1920 --height 1080 \
  --out overlays/

# Render directly to VP9-alpha WebM
web-overlay render card.html.j2 \
  --data '{"title": "Act I"}' \
  --duration 5.0 --fps 30 \
  --webm title_card.webm

# Composite a WebM overlay onto a source video at timestamp 2s
web-overlay composite interview.mp4 title_card.webm \
  --at 2.0 --output interview_titled.mp4
```

---

## Package structure

```
src/web_overlay/
├── __init__.py          ← public re-exports: HtmlOverlay, SvgOverlay, RenderConfig, composite
├── cli.py               ← argparse CLI: setup / render / composite
├── config.py            ← RenderConfig pydantic model
├── exceptions.py        ← OverlayError, TemplateError, BrowserError
├── overlay.py           ← HtmlOverlay and SvgOverlay classes; render_png_sequence / render_webm
├── renderer.py          ← Playwright page lifecycle; frame-by-frame screenshot loop
├── compositor.py        ← composite() — ffmpeg overlay filter wrapping the WebM onto video
├── ffmpeg_runner.py     ← subprocess wrapper for ffmpeg (VP9 encoding and compositing)
└── templates/           ← bundled example templates (shipped in the wheel)
    ├── lower_third.html.j2
    ├── countdown.svg.j2
    └── title_card.html.j2
```

---

© Trollfabriken AITrix AB — MIT licensed
