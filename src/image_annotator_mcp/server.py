from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Any, Literal, Optional

from mcp.server.fastmcp import FastMCP
from PIL import Image

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


@mcp.tool(
    name="annotate_image",
    description=(
        "Draw annotation shapes (rectangle, circle, arrow, line, text, numbered_callout) "
        "onto an image and return the annotated copy. Designed for QA agents that have "
        "captured a screenshot with Playwright MCP and want to mark up the regions they "
        "verified. Coordinates default to image-pixel space; pass coordinate_space='css' "
        "with device_scale=<deviceScaleFactor> when using Playwright boundingBox() coords."
    ),
)
def annotate_image(
    annotations: list[dict[str, Any]],
    input_path: Optional[str] = None,
    input_base64: Optional[str] = None,
    output_path: Optional[str] = None,
    output_format: Literal["png", "jpeg"] = "png",
    coordinate_space: Literal["image", "css"] = "image",
    device_scale: Optional[float] = None,
) -> dict[str, Any]:
    return annotate_image_tool(
        input_path=input_path,
        input_base64=input_base64,
        output_path=output_path,
        output_format=output_format,
        coordinate_space=coordinate_space,
        device_scale=device_scale,
        annotations=annotations,
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
