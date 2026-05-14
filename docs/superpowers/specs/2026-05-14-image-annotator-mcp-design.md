# image-annotator-mcp — Design Spec

Date: 2026-05-14
Status: Approved (brainstorming phase). Implementation plan to follow via `writing-plans`.

## Purpose

A single-purpose MCP server that takes an input image plus a list of shape commands and returns the same image with those shapes drawn on top. It exists to serve QA agents that drive browsers with Playwright MCP or Claude-in-Chrome, capture screenshots, and need to mark up what was verified — column headers, table cells, page titles, the cursor position, etc. — for human reviewers.

The reference visual style is the set of hand-annotated screenshots in `samples/` of this repository: bright green or red hollow rectangles, roughly 4 px line width, drawn around specific UI regions on the Proline application.

## Scope

### In scope
- Accepting an image (file path or base64) plus a JSON array of shape commands.
- Rendering shapes: `rectangle`, `circle`, `arrow`, `line`, `text`, `numbered_callout`.
- Returning the annotated image as a file on disk **and** as an inline MCP `ImageContent` block.
- Translating coordinates between CSS-pixel space (Playwright's `boundingBox()` semantics) and image-pixel space when the screenshot was taken on a HiDPI display.

### Out of scope
- Screenshot capture, navigation, clicking, typing, network mocking, selectors, accessibility-tree access — Playwright MCP already owns these and the agent already has them.
- OCR, layout detection, semantic understanding of the screenshot.
- Cropping, blurring, rotating, resizing, brightness/contrast — Playwright captures support `clip` for cropping; everything else is YAGNI.
- Selector-based annotation (`{"selector": "button.primary"}`). Re-couples to Playwright. v1 is pixel coordinates only.
- A stateful image session (`load_image` → `image_id` → `annotate` → `save`). The agent already has the image; one round-trip is enough.

## Tool surface

Exactly one tool is exposed.

```
annotate_image(
  input_path?:       string,        # absolute path to a PNG or JPEG
  input_base64?:     string,        # base64-encoded image, used when input_path is absent
  output_path?:      string,        # if omitted, defaults to "<input_path stem>.annotated.png"
                                    # required when only input_base64 is provided
  output_format?:    "png" | "jpeg",  # default: "png"
  coordinate_space?: "image" | "css", # default: "image"
  device_scale?:     number,        # required when coordinate_space="css", e.g. 2.0
  annotations:       Annotation[],  # one or more shape commands, applied in order
) -> {
  saved_path: string,               # absolute path of the written file
  width:      integer,              # output image width in pixels
  height:     integer,              # output image height in pixels
  image:      ImageContent,         # { type: "image", data: <base64>, mimeType: "image/png" }
}
```

### Input rules

- Exactly one of `input_path` or `input_base64` must be supplied. Both supplied or neither → tool error.
- When only `input_base64` is supplied, `output_path` is required (we have nowhere to derive a default from).
- `input_path` must exist and be readable. The MCP does **not** create intermediate directories for the input.
- `output_path`'s parent directory must exist. The MCP does not create intermediate directories for the output either; it errors instead. (This avoids accidental writes outside the user's intended location.)
- `output_format="jpeg"` rejects transparent fills with a clear error; PNG is the safe default.

### Output rules

- Always writes to disk, always returns the saved path.
- Always returns an `ImageContent` block so the agent can visually verify the result without re-reading the file.
- Returns `width` and `height` of the output so the agent can sanity-check coordinate math.

## Annotation primitives

The `annotations` array contains objects discriminated by the `type` field. The MCP applies them in array order, so later shapes draw on top of earlier ones.

| `type`             | Required                              | Optional                                                  |
|--------------------|---------------------------------------|-----------------------------------------------------------|
| `rectangle`        | `x, y, width, height`                 | `color`, `line_width`, `fill`, `radius` (rounded corners) |
| `circle`           | `x, y, radius`                        | `color`, `line_width`, `fill`                             |
| `arrow`            | `x1, y1, x2, y2`                      | `color`, `line_width`, `head_size`                        |
| `line`             | `x1, y1, x2, y2`                      | `color`, `line_width`                                     |
| `text`             | `x, y, text`                          | `color`, `font_size`, `background`, `padding`             |
| `numbered_callout` | `x, y, number`                        | `color`, `radius`, `font_size`                            |

### Field semantics

- All coordinates are integers, top-left origin.
- `rectangle.x, y` is the top-left corner; `width, height` are positive.
- `circle.x, y` is the centre; `radius` is positive.
- `arrow` draws from `(x1, y1)` to `(x2, y2)` with a triangular head at the end.
- `text.x, y` is the top-left corner of the text's bounding box (Pillow's default `anchor="la"` equivalent); rendering uses a bundled DejaVu Sans font so the server has no dependency on the host's installed fonts.
- `numbered_callout` is a filled circle with `number` centred inside in white text — useful for "step 1, step 2, step 3" overlays on a single screenshot.

### Defaults (chosen to match the sample images)

- `color`: `"#22C55E"` (the same green used in `9e8515ab` and `fbe109b0`)
- `line_width`: 4
- `fill`: omitted (hollow shape)
- `arrow.head_size`: 12
- `text.font_size`: 14
- `text.background`: omitted (transparent)
- `numbered_callout.radius`: 14, `font_size`: 16

### Color resolution

Accepts:
- Hex strings: `"#22C55E"`, `"#FF0000"`, `"#22C55E80"` (with alpha).
- CSS-style named colors: `"red"`, `"green"`, `"blue"`, `"yellow"`, `"orange"`, `"purple"`, `"black"`, `"white"`, `"cyan"`, `"magenta"`. The full set is whatever Pillow's `ImageColor` resolves, but the README will list the recommended ten.
- RGB tuples: `[r, g, b]` with each channel in 0–255, or `[r, g, b, a]` for transparency.

Invalid color → tool error with the offending value echoed back.

## The DPR / coordinate-space contract

This is the single subtle thing the agent must get right.

Playwright's `Locator.boundingBox()` returns coordinates in **CSS pixels**. Playwright's `page.screenshot()` returns an image whose intrinsic size equals CSS-pixel-width × `deviceScaleFactor`. On a Retina display (`deviceScaleFactor = 2`), a 1280×800 viewport produces a 2560×1600 PNG. Bounding-box coords from such a page need to be doubled before they line up with the screenshot.

The MCP handles this explicitly:

- `coordinate_space: "image"` (default): annotation coordinates are already in image-pixel space. Nothing is scaled. This is what the agent should use when it has manually computed image-relative coords, or when the screenshot was taken at `deviceScaleFactor = 1`.
- `coordinate_space: "css"` with `device_scale: <n>`: the MCP multiplies every coordinate, every `line_width`, every `radius`, every `font_size`, and every `head_size` by `<n>` before drawing. `<n>` must match the `deviceScaleFactor` that was active when the screenshot was captured. Fractional scales (e.g. `1.5`) are handled by scaling the rectangle's right and bottom edges (`x + width`, `y + height`) separately from its origin and rounding each with Python's `round` (banker's rounding), then deriving the rendered width/height from the rounded edges. This keeps right and bottom edges stable rather than letting independent rounding of the width drift them by a pixel.

If `coordinate_space="css"` is set without `device_scale`, the tool errors. The error message states this constraint explicitly so the agent learns to pair the two.

## I/O modes

| Mode                                   | Use case                                          |
|----------------------------------------|---------------------------------------------------|
| `input_path` → auto `output_path`      | Default. Screenshot saved to disk; annotated copy lands next to it. |
| `input_path` → explicit `output_path`  | Agent wants the output in a specific QA-report folder. |
| `input_base64` → explicit `output_path`| Image was captured in-memory and never written.   |
| any input → returned `ImageContent`    | Always returned — the agent verifies visually.    |

The server is **stateless**. Every call carries the full image and the full annotation set; nothing is cached between calls.

## Error handling

Errors are returned as MCP tool errors with a short human-readable message. The tool never silently succeeds with a partial result. Cases:

- Both `input_path` and `input_base64` supplied, or neither.
- `input_path` does not exist, is not readable, or is not a PNG/JPEG.
- `input_base64` is not valid base64 or not a decodable image.
- `output_path` parent directory does not exist or is not writable.
- `coordinate_space="css"` without `device_scale`.
- `device_scale` ≤ 0.
- `output_format="jpeg"` combined with any annotation whose `color` has alpha < 1.0.
- An annotation has an invalid `type`, missing required field, negative dimension, or unresolvable `color`.
- An annotation lands fully outside the image bounds. (Partial overlap is allowed and clipped silently — that matches what a human annotator would expect.)

## Technology stack

- **Python 3.11+**.
- **Pillow** for image loading, drawing, and saving — mature, well-known shape and text rendering.
- **FastMCP** (the official `mcp` Python SDK) for the server transport and tool registration.
- **Pydantic v2** for the `Annotation` discriminated union and tool-input validation.
- **DejaVu Sans** bundled with the package so text rendering works without the host's font directory.
- Distributed as a Python package, runnable via `uvx image-annotator-mcp` — the same one-line install pattern Playwright MCP uses with `npx`.

## Project layout

```
proline/
  pyproject.toml
  README.md
  src/image_annotator_mcp/
    __init__.py
    server.py          # FastMCP wiring; declares the single tool
    annotate.py        # Pure Pillow drawing functions, one per shape type
    models.py          # Pydantic Annotation union; input/output models
    colors.py          # Hex / name / rgb-tuple resolution
    scaling.py         # coordinate_space + device_scale translation
    fonts/
      DejaVuSans.ttf
  tests/
    test_annotate.py   # Per-shape golden-image tests
    test_models.py     # Pydantic validation, error messages
    test_scaling.py    # CSS-space coord translation, including device_scale != 2
    test_server.py     # Tool I/O contract, both input modes, error paths
    fixtures/
      blank_800x600.png
      sample_screen.png
      golden/
        rectangle_default.png
        rectangle_red_filled.png
        circle_default.png
        arrow_red.png
        line_blue.png
        text_with_background.png
        numbered_callout.png
        batch_three_rectangles.png
        css_space_2x_scale.png
```

## Testing strategy

Test-Driven Development. For each shape type:

1. Load a checked-in fixture image (`blank_800x600.png` or `sample_screen.png`).
2. Apply exactly one annotation with known parameters.
3. Compare the resulting bytes byte-for-byte (or `ImageChops.difference == 0`) against a checked-in golden image.

Plus integration tests for:

- Batch ordering — later shapes overdraw earlier ones in the correct visual order.
- `coordinate_space="css"` with `device_scale=2.0` — output matches a 2× pre-scaled golden.
- `coordinate_space="css"` with `device_scale=1.5` — fractional scales round to the nearest pixel consistently.
- Both input modes — `input_path` and `input_base64` produce identical output for the same image.
- All error paths listed in the *Error handling* section — each returns the expected error message.
- `ImageContent` round-trip — re-decoding the returned `data` produces the same bytes as the file on disk.

Golden images are regenerated only when a shape's rendering is intentionally changed, never as a way to make tests pass.

## Example call

```json
{
  "input_path": "/tmp/screenshots/employee-request-2466.png",
  "coordinate_space": "css",
  "device_scale": 2.0,
  "annotations": [
    {"type": "rectangle", "x": 220, "y": 195, "width": 70,  "height": 30, "color": "green"},
    {"type": "rectangle", "x": 398, "y": 195, "width": 95,  "height": 30, "color": "green"},
    {"type": "rectangle", "x": 728, "y": 184, "width": 70,  "height": 50, "color": "green"},
    {"type": "arrow",     "x1": 600, "y1": 100, "x2": 728, "y2": 195, "color": "red"},
    {"type": "text",      "x": 600, "y": 90,   "text": "verified", "color": "red", "font_size": 14}
  ]
}
```

This reproduces the markup style of `samples/9e8515ab-ad8f-41af-b8ea-4cd31a525418 (1).jpeg` and `samples/d0c91612-9140-4cd0-aa28-2c49cebd3f8e.jpeg`.

## Seams with the rest of the QA agent

```
┌─────────────────────────┐    page.screenshot()    ┌────────────────────────┐
│ Playwright MCP /        │ ──────────────────────► │ screenshot.png on disk │
│ Claude-in-Chrome        │    boundingBox() coords │                        │
└─────────────────────────┘ ──┐                     └────────────────────────┘
                              │                                  │
                              │ list of {x, y, w, h}             │ input_path
                              ▼                                  ▼
                       ┌──────────────────────────────────────────────┐
                       │ image-annotator-mcp                          │
                       │   annotate_image(...)                        │
                       └──────────────────────────────────────────────┘
                                            │
                                            ▼
                              ┌──────────────────────────────┐
                              │ screenshot.annotated.png     │
                              │ + ImageContent for the agent │
                              └──────────────────────────────┘
```

The annotation MCP never talks to the browser. The browser MCP never draws on images. The QA agent is the only thing that knows both.

## Out-of-band concerns flagged for the implementation plan

- Font licensing: DejaVu Sans is permissively licensed; the LICENSE file from upstream must ship with the package.
- Pillow font size handling differs between `truetype` and default bitmap fonts — the spec assumes truetype only.
- Large images: a 4K screenshot at 2× scale is ~33 megapixels and ~130 MB decoded. The implementation should stream the file rather than load twice. Worth a memory-bound test in CI.
- Base64 in / base64 out is large in MCP payloads. The plan should call out that `input_path` is preferred for anything over ~1 MB and the README should say so.
