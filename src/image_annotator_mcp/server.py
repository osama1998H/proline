from __future__ import annotations

import base64
import json
from io import BytesIO
from pathlib import Path
from typing import Annotated, Any, Literal, Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.types import Image as MCPImage
from mcp.types import TextContent
from PIL import Image
from pydantic import Field

from .annotate import annotate_image_bytes
from .models import AnnotateImageInput


mcp = FastMCP("image-annotator")


def _derive_output_path(input_path: str, output_format: str) -> str:
    p = Path(input_path)
    ext = ".png" if output_format == "png" else ".jpg"
    return str(p.with_suffix("")) + f".annotated{ext}"


def annotate_image_tool(
    *,
    input_path: Optional[str] = None,
    input_base64: Optional[str] = None,
    output_path: Optional[str] = None,
    output_format: Literal["png", "jpeg"] = "png",
    coordinate_space: Literal["image", "css"] = "image",
    device_scale: Optional[float] = None,
    annotations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Implementation of the annotate_image tool, callable from tests."""
    payload = AnnotateImageInput(
        input_path=input_path,
        input_base64=input_base64,
        output_path=output_path,
        output_format=output_format,
        coordinate_space=coordinate_space,
        device_scale=device_scale,
        annotations=annotations,
    )

    final_out = payload.output_path or _derive_output_path(payload.input_path, payload.output_format)  # type: ignore[arg-type]
    out_parent = Path(final_out).parent
    if not out_parent.exists():
        raise FileNotFoundError(f"output_path parent directory does not exist: {out_parent}")

    out_bytes = annotate_image_bytes(payload)
    Path(final_out).write_bytes(out_bytes)

    with Image.open(BytesIO(out_bytes)) as img:
        width, height = img.size

    return {
        "saved_path": final_out,
        "width": width,
        "height": height,
        "image": {
            "type": "image",
            "data": base64.b64encode(out_bytes).decode("ascii"),
            "mimeType": "image/png" if payload.output_format == "png" else "image/jpeg",
        },
    }


_TOOL_DESCRIPTION = """\
Draw annotation shapes onto a screenshot and return the annotated copy.

WORKFLOW — follow this exactly. DO NOT estimate coordinates by looking at the image.
1. Capture a screenshot with a browser tool (Playwright MCP, claude-in-chrome, etc.).
2. In the SAME browser context, query the bounding rect of every element you want
   to highlight:
     - Playwright:  `await locator.bounding_box()`  (or  `el.getBoundingClientRect()` via `page.evaluate`)
     - DOM in JS:    `element.getBoundingClientRect()`
   Both return `{x, y, width, height}` in CSS pixels.
3. Call this tool with `input_path=<screenshot path>` and one annotation per element,
   plugging the exact rect from step 2 into the annotation's coordinate fields.

Why this matters: the LLM cannot reliably read pixel coordinates off a rendered
image — visual estimates drift 10-50 px off the actual element. The page DOM is
the only source of truth for "where things are." The accuracy of every annotation
this tool produces is determined by the accuracy of the coordinates you pass in.

COORDINATE SPACE:
- `coordinate_space="image"` (default): annotations are in the screenshot's pixel space.
  Use this when device_scale_factor was 1 at capture time, or when you've already
  converted CSS coords to image coords.
- `coordinate_space="css"` + `device_scale=<n>`: annotations are in CSS pixels and
  the MCP scales them by `n` before drawing. Use this for HiDPI screenshots
  (e.g. Playwright defaults to deviceScaleFactor=2 on Retina; you keep CSS-pixel
  boxes and let the MCP scale).

SHAPES: each annotation is a dict with a `type` field and shape-specific fields:
- `rectangle`: `x, y, width, height` (+ optional `color`, `line_width`, `fill`, `radius`)
- `circle`: `x, y, radius` (+ optional `color`, `line_width`, `fill`)
- `arrow`: `x1, y1, x2, y2` — line with a triangular head at (x2, y2)
- `line`: `x1, y1, x2, y2`
- `text`: `x, y, text` (+ optional `color`, `font_size`, `background`, `padding`)
- `numbered_callout`: `x, y, number` — filled circle with the number centred inside

Annotations are applied in array order; later shapes overdraw earlier ones.
Colors accept hex (`"#22C55E"`), CSS names (`"red"`, `"green"`, ...), or RGB(A) tuples.
`line_width` is a preset keyword — one of `"thin"` (2 CSS px), `"regular"` (4),
or `"bold"` (7). Raw integers are rejected; pick a preset.

RETURNS: a TextContent block with `{saved_path, width, height}` JSON, plus an inline
ImageContent block of the annotated image. Set `include_image=false` for batch
workflows where the saved file is enough and inline previews add overhead.
"""


@mcp.tool(name="annotate_image", description=_TOOL_DESCRIPTION)
def annotate_image(
    annotations: Annotated[
        list[dict[str, Any]],
        Field(description=(
            "List of shape commands to draw on the image, applied in array order. "
            "Each item is a dict with a 'type' field (rectangle, circle, arrow, line, "
            "text, or numbered_callout) plus shape-specific coordinate and style fields. "
            "Coordinates must come from the page's DOM (e.g. getBoundingClientRect()), "
            "not from visual estimation of the screenshot."
        )),
    ],
    input_path: Annotated[
        Optional[str],
        Field(description=(
            "Absolute filesystem path to the input image (PNG or JPEG). Preferred over "
            "input_base64 for anything over ~1 MB. Exactly one of input_path or "
            "input_base64 must be supplied."
        )),
    ] = None,
    input_base64: Annotated[
        Optional[str],
        Field(description=(
            "Base64-encoded image bytes, used when the source never touched disk. "
            "Requires output_path. Inflates the request payload by ~33% vs input_path."
        )),
    ] = None,
    output_path: Annotated[
        Optional[str],
        Field(description=(
            "Absolute path where the annotated image will be written. When using "
            "input_path, this defaults to '<input stem>.annotated.<png|jpg>' next to "
            "the input. The parent directory must already exist — the MCP will not "
            "create intermediate directories."
        )),
    ] = None,
    output_format: Annotated[
        Literal["png", "jpeg"],
        Field(description=(
            "Output image format. PNG preserves transparency and is the safe default; "
            "JPEG rejects any annotation whose color uses alpha < 1.0."
        )),
    ] = "png",
    coordinate_space: Annotated[
        Literal["image", "css"],
        Field(description=(
            "Coordinate system for all annotation fields. 'image' means coordinates "
            "are already in the screenshot's pixel space. 'css' means coordinates are "
            "in CSS pixels and the MCP will multiply them by device_scale before "
            "drawing — use this when passing getBoundingClientRect() coords against a "
            "HiDPI screenshot."
        )),
    ] = "image",
    device_scale: Annotated[
        Optional[float],
        Field(description=(
            "Required when coordinate_space='css'. Set to the deviceScaleFactor that "
            "was active when the screenshot was captured (usually 1 or 2). Affects "
            "every coordinate AND every size-like field: radius, font_size, "
            "head_size, padding, and the resolved px value of the line_width preset."
        )),
    ] = None,
    include_image: Annotated[
        bool,
        Field(description=(
            "When true (default) the response includes the annotated image as a proper "
            "MCP ImageContent block so the agent can see it inline. Set false for batch "
            "annotation workflows that only need the saved file path — useful when "
            "calling the tool many times in a row."
        )),
    ] = True,
):
    # Route the image bytes through MCP's media channel (Image -> ImageContent),
    # NOT through structuredContent or a giant TextContent. See docs/superpowers/
    # plans -- v0.1.0 served the image as a base64 string inside a dict, which
    # FastMCP serialised as a single TextContent block (~315 KB for a 1568x1000
    # PNG) and overflowed the host's text-token limit.
    result = annotate_image_tool(
        input_path=input_path,
        input_base64=input_base64,
        output_path=output_path,
        output_format=output_format,
        coordinate_space=coordinate_space,
        device_scale=device_scale,
        annotations=annotations,
    )
    metadata = {
        "saved_path": result["saved_path"],
        "width": result["width"],
        "height": result["height"],
    }
    blocks: list = [TextContent(type="text", text=json.dumps(metadata))]
    if include_image:
        raw_bytes = base64.b64decode(result["image"]["data"])
        blocks.append(MCPImage(data=raw_bytes, format=output_format))
    return blocks


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
