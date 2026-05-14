# conductor_annotated.png — Iteration 2 Notes

Date: 2026-05-14
Target URL: https://github.com/osama1998H/conductor (public)
Output: `samples/conductor_annotated.png` — 1568 × 1000 PNG

## What changed vs the AAU run

- Switched to a **public** repo so authentication isn't needed.
- Invoked the MCP **through the JSON-RPC transport** this time (`mcp__image-annotator__annotate_image`) — the registered server is callable from this fresh Claude Code session.
- Solved the **accuracy problem** by sourcing every coordinate from the DOM, not from eyeballing the screenshot.

## The accuracy fix: DOM-derived coordinates

The previous run's annotations on `aau_annotated.png` were visibly shifted by 10–50 pixels because I was reading pixel positions off the rendered screenshot. That's a non-starter — the LLM can see *that* a button is roughly there but can't *measure* its top-left corner to the pixel.

The fix is to bypass the visual step entirely:

1. Take the screenshot with Playwright at a known viewport (`1568 × 1000`, `device_scale_factor=1`).
2. In the same browser context, run JavaScript via `locator.bounding_box()` on stable CSS selectors. That returns CSS-pixel coordinates with sub-pixel precision.
3. Because the screenshot was taken at `device_scale_factor=1`, **CSS pixels and image pixels are identical**. The boxes drop straight into `annotate_image` with `coordinate_space="image"`.

Concretely, the capture script harvests selectors like these:

| Section         | Selector tried                                                | Box returned (x, y, w, h)         |
|-----------------|---------------------------------------------------------------|-----------------------------------|
| page_header     | `header[role="banner"]`                                       | (0, 0, 1568, 72)                  |
| repo_header     | `#repository-container-header`                                | (0, 72, 1568, 110)                |
| repo_nav        | `nav[aria-label="Repository"]`                                | (0, 134, 1568, 48)                |
| code_button     | `button:has-text("Code"):below(nav[aria-label="Repository"])` | (971, 206, 109, 32)               |
| branch_picker   | `button[data-testid="anchor-button"]`                         | (176, 206, 105.5, 32)             |
| file_list       | `table[aria-labelledby="folders-and-files"]`                  | (176, 254, 904, 751)              |
| search_box      | `button[data-target="qbsearch-input.inputButton"]`            | (1006.7, 21, 318, 30)             |
| about_section   | (no candidate matched modern GitHub)                          | —                                 |
| star_button     | (no candidate matched)                                        | —                                 |

These coordinates land **on the actual element**, not "in the visual neighborhood of the actual element."

### Recommended pattern for an agent

The QA agent's workflow becomes:

1. Drive the browser (Playwright MCP, claude-in-chrome, anything).
2. Before screenshotting, walk the elements you care about with `getBoundingClientRect()` (or its Playwright equivalent). Save the boxes alongside the screenshot.
3. Hand the screenshot path + the box list to `annotate_image`. Don't ask the LLM to estimate coordinates from the image.

For HiDPI captures (e.g. `page.screenshot()` on a 2× Retina viewport) keep the boxes in CSS pixels and pass `coordinate_space="css"` + `device_scale=<deviceScaleFactor>`. The MCP scales for you.

For elements that aren't pickable by selector (an icon, a region of a chart) fall back to the LLM's visual estimate — but constrain that to small adjustments (e.g. radius around a logo), never large rectangles where pixel error is visually obvious.

## Annotations applied (14 total)

| # | Shape              | DOM section / location  | Colour            |
|---|--------------------|-------------------------|-------------------|
| 1 | rectangle          | page_header             | `#22C55E` green   |
| 2 | rectangle          | repo_header             | `#06B6D4` cyan    |
| 3 | rectangle, `radius=6` | Code button          | `#EF4444` red     |
| 4 | rectangle          | file_list               | `#A855F7` purple  |
| 5 | circle             | branch_picker           | `#EC4899` magenta |
| 6 | arrow              | label → branch_picker   | `#F97316` orange  |
| 7 | line               | y=72 separator          | `#FACC15` yellow  |
| 8 | text               | "DOM-derived"           | white on black    |
| 9 | text               | "branch picker"         | white on orange   |
| 10 | numbered_callout  | "1" near page_header    | green             |
| 11 | numbered_callout  | "2" near repo_header    | cyan              |
| 12 | numbered_callout  | "3" near Code button    | red               |
| 13 | numbered_callout  | "4" near file_list      | purple            |
| 14 | numbered_callout  | "5" near branch_picker  | magenta           |

All six shape types are exercised: rectangle, circle, arrow, line, text, numbered_callout.

## Constraints encountered in this iteration

### 1. Oversized `ImageContent` response overflows the host's tool-result limit

The MCP returned a 315 KB JSON payload because it embeds the annotated PNG as a base64 string inside the `image` field. The host (Claude Code) rejected the inline response and spilled it to a tool-result file:

```
Error: result (315,226 characters) exceeds maximum allowed tokens.
Output has been saved to .../tool-results/mcp-image-annotator-annotate_image-...txt
```

The file was saved to disk correctly — the failure is purely the host's response size guard, not the MCP. I still extracted `saved_path`, `width`, `height` via `jq`.

**Fix paths (for the next MCP iteration):**
- Add an `include_image_content` boolean parameter (default `true` for compatibility, set `false` when the client only needs the file path). This is a one-field, zero-behaviour-change addition.
- Add a `thumbnail_max_dim` parameter that downscales the `ImageContent` to e.g. 800 px on the longer edge so the inline preview stays small while the saved file keeps full resolution. Same intent as `mcp__claude_ai_Figma__get_screenshot`'s `maxDimension`.
- Document the recommendation: callers handling large screenshots should set the parameter, or read the file via `saved_path` after the call.

This is the cleanest single follow-up improvement to `image-annotator-mcp`. Worth a v0.1.1 patch.

### 2. Modern GitHub doesn't expose selectors for every section

The candidate selectors for `about_section` and `star_button` all missed. GitHub's React-rendered chrome uses opaque generated class names. The capture script intentionally tries multiple candidates and logs `(no match)` rather than crashing, so the rest of the run completed cleanly.

**Fix paths:**
- Maintain a per-site selector registry, refreshed when GitHub changes its DOM. Treat selector lists as data, not code.
- Or, fall back to text-anchored locators (`page.get_by_text("About").locator("..")`) which are more resilient to CSS-name churn.
- Or, render the page in headed mode once, use the dev tools to find a stable attribute (`[data-testid=...]` when available), and pin to that.

### 3. README sits below the captured viewport

The README's bounding box was `(209, 1102, 838, 5364)` — above the visible 1000-px viewport. Annotating it directly would put the rectangle entirely off-canvas; the MCP's bounds check correctly rejects fully-off-canvas annotations, so we'd get a clean ValueError. Workarounds: capture `full_page=True` (yields a very tall image, 5× the viewport here) and annotate the whole-page screenshot, or scroll to the README before screenshotting.

## What worked cleanly

- The `claude mcp add` registration from the previous session survived; this fresh session loaded `mcp__image-annotator__annotate_image` automatically.
- 14 annotations across all six shape types in one round trip, rendered in ~0.4 s.
- DOM-derived coords produced visibly perfect placement — every shape wraps the element it should.
- Two text labels (`"DOM-derived"` and `"branch picker"`) rendered with their backgrounds and padding correctly.
- Numbered callouts 1–5 sit cleanly at the corners of their sections in matching colours.
- Rounded-corner rectangle (`radius=6` on the Code button) rendered correctly.
- The script is reusable: change `URL` and the section selector list and you have a working QA-screenshot pipeline.

## Comparison vs `aau_annotated.png`

| Aspect                       | `aau_annotated.png` (iteration 1)        | `conductor_annotated.png` (iteration 2)         |
|------------------------------|------------------------------------------|-------------------------------------------------|
| Coordinate source            | LLM visual estimate                      | DOM `getBoundingClientRect()`                   |
| Accuracy                     | ±20–50 px (shapes visibly shifted)       | Pixel-perfect (shapes hug their elements)       |
| Repo accessibility           | private → 404 page                       | public → real repo                              |
| MCP invocation               | Python entry point (transport bypassed)  | JSON-RPC via `mcp__image-annotator__…`          |
| Notable failure              | `save_to_disk` didn't return a path      | `ImageContent` overflowed host result limit     |

The accuracy delta is the headline result: **use the DOM as the source of truth for "where things are", and stop asking the LLM to read pixels.**
