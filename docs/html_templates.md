# Authoring HTML and SVG templates for web-overlay

Templates are Jinja2 files processed before being loaded into Playwright Chromium.
This guide covers everything you need to produce correct, deterministic overlay sequences.

---

## Transparent background

Every template must declare a transparent background. Playwright is launched with
`--default-background-color=00000000`, which sets the page background to transparent.
You must also clear any default browser margin:

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
  <!-- overlay content here -->
</body>
</html>
```

Any pixel you do not paint remains fully transparent (alpha = 0) in the PNG output.
Do not set `background: white` or any opaque colour unless you want a solid rectangle
in your composite.

---

## Sizing: vw/vh units vs. explicit pixels

`RenderConfig.width` and `RenderConfig.height` control the Playwright viewport. Size
your overlay elements to match.

**Recommended — use viewport-relative units** so the same template works at different
resolutions:

```css
.title {
  font-size: 5vw;     /* 96px at 1920-wide; 54px at 1080-wide */
  padding: 2vh 4vw;
}
```

**Alternative — explicit pixels** when you need pixel-perfect positioning:

```css
.lower-third {
  position: absolute;
  left: 0;
  bottom: 80px;
  width: 960px;
  height: 180px;
}
```

Match the explicit pixel values to whatever `width`/`height` you pass to `RenderConfig`.
Mismatches produce clipped or off-centre content.

---

## Jinja2 variable substitution

Pass a `data` dict when constructing `HtmlOverlay` or `SvgOverlay`. All keys are
available as Jinja2 variables inside the template.

```python
from web_overlay import HtmlOverlay, RenderConfig

overlay = HtmlOverlay(
    template_path="lower_third.html.j2",
    data={
        "name": "Anna Svensson",
        "title": "Regissör",
        "accent_color": "#e63946",
    },
    duration=6.0,
    fps=30,
)
```

Template (`lower_third.html.j2`):

```html
<html>
<head>
  <style>
    html, body { margin: 0; background: transparent; }
    .bar {
      position: absolute;
      bottom: 10vh;
      left: 4vw;
      border-left: 6px solid {{ accent_color }};
      padding-left: 1.5vw;
    }
    .name  { color: white; font-size: 3.5vw; font-weight: 700; }
    .title { color: #ccc;  font-size: 2vw; }
  </style>
</head>
<body>
  <div class="bar">
    <div class="name">{{ name }}</div>
    <div class="title">{{ title }}</div>
  </div>
</body>
</html>
```

Jinja2 filters work normally: `{{ name | upper }}`, `{{ seconds | int }}`, etc.
Use `{% if %}` blocks for conditional sections:

```html
{% if show_logo %}
<img class="logo" src="data:image/svg+xml;base64,{{ logo_b64 }}" />
{% endif %}
```

---

## CSS animation authoring and timing

`web-overlay` drives animation by advancing `document.timeline.currentTime` one frame
at a time rather than letting the browser run animations in real time. This gives
deterministic, frame-accurate output with no timing jitter.

**Step 1 — Declare the animation as paused.**

```css
@keyframes slide-in {
  from { transform: translateX(-100%); opacity: 0; }
  to   { transform: translateX(0);     opacity: 1; }
}

.lower-third {
  animation: slide-in 0.5s ease-out both;
  animation-play-state: paused;
}
```

Setting `animation-play-state: paused` prevents the browser from auto-playing the
animation. `web-overlay` steps the clock instead.

**Step 2 — The renderer advances the clock.**

For a 30 fps render, the renderer calls:

```javascript
document.timeline.currentTime += 1000 / 30;  // ≈ 33.33 ms per frame
```

before each `page.screenshot()` call. CSS animations respond to the timeline
progressing, so a 0.5 s animation completes at frame 15 of a 30 fps sequence.

**Step 3 — Stagger multiple animations with `animation-delay`.**

```css
.name  { animation: slide-in 0.4s ease-out 0.0s both; animation-play-state: paused; }
.title { animation: slide-in 0.4s ease-out 0.2s both; animation-play-state: paused; }
```

Both will play deterministically: `name` starts at frame 0; `title` starts at frame 6
(0.2 s × 30 fps).

**Transforms and opacity.** Use standard CSS transforms. The Chromium renderer handles
sub-pixel antialiasing identically to a display browser, so text and edges look correct.

---

## Web font loading

Load fonts via `<link>` from Google Fonts or any CDN:

```html
<head>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap"
    rel="stylesheet"
  >
  <style>
    body { font-family: 'Inter', sans-serif; }
  </style>
</head>
```

`web-overlay` calls `await page.evaluate("document.fonts.ready")` before capturing
frame 0. The font is guaranteed loaded. There is no first-few-frames fallback-font
flicker.

**Offline / air-gapped environments.** Embed fonts as base64 data URIs so no network
request is needed at render time:

```html
<style>
@font-face {
  font-family: 'Inter';
  src: url('data:font/woff2;base64,AAAA...') format('woff2');
  font-weight: 400;
}
</style>
```

Convert a font file to base64 with:

```python
import base64, pathlib
b64 = base64.b64encode(pathlib.Path("Inter-Regular.woff2").read_bytes()).decode()
print(f"data:font/woff2;base64,{b64}")
```

---

## SVG templates

`SvgOverlay` accepts a raw SVG document (not wrapped in HTML). The SVG is loaded as a
standalone page with a transparent background. All the same rules apply: transparent
fill, Jinja2 variables, `document.fonts.ready`, and the clock-step animation model.

```xml
<!-- countdown.svg.j2 -->
<svg xmlns="http://www.w3.org/2000/svg"
     width="{{ width }}" height="{{ height }}"
     viewBox="0 0 {{ width }} {{ height }}">
  <style>
    text { font-family: 'Inter', sans-serif; fill: white; }
    circle { fill: none; stroke: white; stroke-width: 4; }
  </style>
  <circle cx="{{ width // 2 }}" cy="{{ height // 2 }}" r="80"/>
  <text x="{{ width // 2 }}" y="{{ height // 2 + 20 }}"
        text-anchor="middle" font-size="96">
    {{ seconds }}
  </text>
</svg>
```

Sizing hint: set `width` and `height` attributes on the root `<svg>` element to match
`RenderConfig.width` and `RenderConfig.height`. Pass them in the `data` dict:

```python
from web_overlay import SvgOverlay, RenderConfig

cfg = RenderConfig(width=1920, height=1080, fps=30)
svg = SvgOverlay(
    template_path="countdown.svg.j2",
    data={"seconds": 10, "width": cfg.width, "height": cfg.height},
    duration=10.0,
    fps=cfg.fps,
)
svg.render_png_sequence("countdown_frames/", config=cfg)
```

---

## Checklist before rendering

- [ ] `html, body { background: transparent; }` is set
- [ ] All animated elements have `animation-play-state: paused`
- [ ] Web fonts are either from a reachable URL or embedded as base64
- [ ] Template sizes match `RenderConfig.width` / `RenderConfig.height`
- [ ] All Jinja2 `{{ variable }}` references have a corresponding key in `data`
- [ ] SVG root element has explicit `width` and `height` attributes
