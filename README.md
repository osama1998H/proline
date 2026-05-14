# image-annotator-mcp

An MCP server that draws annotation shapes onto images. Built for QA agents
that drive browsers with Playwright MCP or Claude-in-Chrome and need to mark
up the regions they verified for human reviewers.

The server exposes exactly one tool, `annotate_image`. It does **not** capture
screenshots, navigate, click, or read the DOM — that's Playwright MCP's job.

## Install

```bash
uvx image-annotator-mcp
```

Or, from this checkout:

```bash
uv venv
uv pip install -e .
uv run image-annotator-mcp
```

## Tool: `annotate_image`

Takes an image plus a list of shape commands, returns the annotated image both
as a file on disk and as an inline MCP `ImageContent` block.

```json
{
  "input_path": "/tmp/screenshots/employee-request.png",
  "coordinate_space": "css",
  "device_scale": 2.0,
  "annotations": [
    {"type": "rectangle", "x": 220, "y": 195, "width": 70,  "height": 30, "color": "green"},
    {"type": "arrow",     "x1": 600, "y1": 100, "x2": 728, "y2": 195, "color": "red"},
    {"type": "text",      "x": 600, "y": 90,   "text": "verified", "color": "red"}
  ]
}
```

### Shapes

| Type               | Required                         | Optional                                      |
|--------------------|----------------------------------|-----------------------------------------------|
| `rectangle`        | `x, y, width, height`            | `color`, `line_width`, `fill`, `radius`       |
| `circle`           | `x, y, radius`                   | `color`, `line_width`, `fill`                 |
| `arrow`            | `x1, y1, x2, y2`                 | `color`, `line_width`, `head_size`            |
| `line`             | `x1, y1, x2, y2`                 | `color`, `line_width`                         |
| `text`             | `x, y, text`                     | `color`, `font_size`, `background`, `padding` |
| `numbered_callout` | `x, y, number`                   | `color`, `radius`, `font_size`                |

### Colors

Hex (`"#22C55E"`, `"#22C55E80"` for alpha), named (`"red"`, `"green"`, `"blue"`,
`"yellow"`, `"orange"`, `"purple"`, `"black"`, `"white"`, `"cyan"`, `"magenta"`),
or RGB / RGBA tuples (`[34, 197, 94]`, `[34, 197, 94, 128]`).

### HiDPI screenshots from Playwright

Playwright's `Locator.boundingBox()` returns CSS pixels. Its `page.screenshot()`
returns an image at `cssPixels × deviceScaleFactor`. When passing boundingBox
coords into this MCP, set:

```json
{ "coordinate_space": "css", "device_scale": 2.0 }
```

…with `device_scale` equal to the active `deviceScaleFactor`. The MCP will
scale every coordinate, plus every size-like field: `line_width`, `radius`,
`font_size`, `head_size`, and `padding`. If your screenshot was taken
at 1× (or you've already converted to image-pixel coords), leave
`coordinate_space` at its default of `"image"`.

### Returns

```json
{
  "saved_path": "/tmp/screenshots/employee-request.annotated.png",
  "width": 1456,
  "height": 944,
  "image": { "type": "image", "data": "...", "mimeType": "image/png" }
}
```

The `image` block lets your agent visually verify the result without re-reading
the file.

## Image sizing notes

For inputs over ~1 MB, prefer `input_path` over `input_base64`. Base64 inflates
MCP payloads by ~33% and is slower for both directions.

## License

MIT for this server. Text rendering uses Pillow's internally bundled font via
`ImageFont.load_default(size=...)`, so no separate font asset needs to be vendored.
