# aau_annotated.png — Test Run Notes

Date: 2026-05-14
Target URL: https://github.com/ASL-AL-Uroba/aau

## What the test did
- Registered the MCP with Claude Code: `claude mcp add image-annotator --scope user -- /opt/homebrew/bin/uv run --project /Users/osamamuhammed/proline image-annotator-mcp`. Server reports `✓ Connected` in `claude mcp list`.
- Captured a screenshot of the URL.
- Called `annotate_image_tool` with 13 annotations covering all six shape types in 8 different colours, plus rounded corners on one rectangle.
- Wrote the result to `samples/aau_annotated.png` (1568 × 900).

## Annotations applied (13 total)

| # | Shape              | Where                  | Colour            | Notes                |
|---|--------------------|------------------------|-------------------|----------------------|
| 1 | rectangle          | Top nav bar            | `#22C55E` green   | full-width strip     |
| 2 | rectangle          | 404 hero               | `#06B6D4` cyan    |                      |
| 3 | rectangle          | Sign-in card           | `#EF4444` red     |                      |
| 4 | rectangle          | Search bar             | `#FACC15` yellow  |                      |
| 5 | rectangle          | Footer area            | `#A855F7` purple  | `radius=8` rounded   |
| 6 | circle             | GitHub logo            | `#EC4899` magenta |                      |
| 7 | arrow              | Hero → sign-in         | `#F97316` orange  | `head_size=14`       |
| 8 | line               | Separator              | `white`           | `line_width=2`       |
| 9 | text               | "MAJOR SECTIONS:"      | white on black    | `padding=6`          |
| 10 | numbered_callout  | "1" near nav           | green             |                      |
| 11 | numbered_callout  | "2" near hero          | cyan              |                      |
| 12 | numbered_callout  | "3" near sign-in       | red               |                      |
| 13 | numbered_callout  | "4" near search        | yellow            |                      |

## Constraints encountered

### 1. Target repository is private (the dominant constraint)
`github.com/ASL-AL-Uroba/aau` is a private repo. Any browser that isn't signed in to a member account gets a public 404 page. claude-in-chrome reached the repo because it inherits the user's authenticated Chrome session, but the screenshot bytes from that session could not be moved to a file on disk (see #2). Playwright in this venv has no cookies and lands on the 404 page. The annotated screenshot is therefore of the 404 page, not the actual repo content.

**Fix paths:**
- Use a public test URL for this exercise (e.g. `github.com/anthropics/claude-code` or any public org page).
- Or, run Playwright against the user's existing Chrome profile via `chromium.launch_persistent_context(user_data_dir=...)` — requires Chrome to be closed first because Chrome locks its profile directory while running.
- Or, export cookies from Chrome and load them into the Playwright context.

### 2. `claude-in-chrome`'s `save_to_disk: true` does not return a usable path
The `computer` tool documentation states: *"Returns the saved path in the tool result."* In practice, the call returned only `Successfully captured screenshot (1568x741, jpeg) - ID: ss_09196oihy`. No path. The image was rendered inline in the conversation, but there was no file at:
- `~/.claude/image-cache/<session>/`
- `~/.claude/projects/.../tasks/` or `.../tool-results/`
- `~/Library/Application Support/Google/Chrome/Default/Extensions/...`
- `/tmp`, `/var/folders/...`, `~/Downloads`

Without a file path, `image-annotator-mcp` can't read the image via `input_path` — and the inline image bytes aren't accessible to the agent as raw base64 either.

**Fix paths:**
- File a feature request on the claude-in-chrome MCP: have `save_to_disk` accept an explicit `save_path` parameter or echo the actual saved path in the result.
- Or, add a sibling tool to `image-annotator-mcp` that accepts the inline screenshot's `imageId`/base64 directly (a coupling-heavy workaround we'd want to avoid).
- Or, write screenshots straight to disk via Playwright (what we did here as the workaround).

### 3. macOS `screencapture` blocked by Screen Recording permission
`screencapture -x /tmp/screen_full.png` failed with *"could not create image from display"*. This is a macOS Screen Recording permission gate. Enable in System Settings → Privacy & Security → Screen Recording for the terminal / Claude Code parent process; one-time setup that survives restarts.

### 4. AppleScript `Google Chrome ... bounds of front window` timed out (AppleEvent -1712)
Trying to read Chrome window bounds via `osascript` failed with the standard Automation-permission timeout. Again a macOS Privacy & Security gate (System Events / Application automation). One-time grant.

### 5. The freshly registered MCP is not callable in the current session
`claude mcp add image-annotator …` updated `~/.claude.json` and `claude mcp list` shows `✓ Connected`, but Claude Code loads MCPs at session start. The new tool will only appear as `mcp__image-annotator__annotate_image` (or similar) **in a fresh session**. For this run I invoked the same code path by calling `annotate_image_tool(...)` from the package directly under `uv run`. The Python entry point is what the MCP server delegates to, so the test exercises the identical logic — just without the JSON-RPC transport in front.

**Fix path:**
- Open a new Claude Code session in this project to see `annotate_image` show up in the tool list and call it through the MCP transport end-to-end.

## What worked cleanly
- `image-annotator-mcp` accepted all 13 annotations across all six shape types in one call and produced a 1568×900 PNG in ~0.3 seconds.
- File path I/O (`input_path` + `output_path`) worked first try.
- The returned `ImageContent` block contained valid base64 PNG decodable by Pillow (verified via the `image` field of the result dict).
- Rounded-corner rectangle (`radius=8` on the purple footer box) rendered correctly.
- Text rendering with optional `background` and `padding` rendered correctly using Pillow's bundled font (no DejaVu vendoring needed — see Task 5 revision in the plan).
- Numbered callouts rendered with white digits centered on filled circles.
- The MCP's separation of concerns held: no DOM access, no navigation, no screenshot capture inside `image-annotator-mcp` — the screenshot came from a separate tool, then we just drew on it.
