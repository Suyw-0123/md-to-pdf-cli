# Images (`images.py`)

This module fixes the classic **"image is broken after conversion"** bug — the
one where an image looks fine in the editor preview but comes out blank in the
PDF. It rewrites every `<img src>` in the rendered HTML so the source resolves
correctly at print time.

## The problem

Markdown like `![](../figures/plot.png)` carries a path relative to the `.md`
file. By the time the HTML reaches Chromium it is loaded from a temp directory,
so a bare relative path no longer points anywhere. And Chromium, for security,
will not load `file://` images from a page whose origin is `about:blank`. Both
issues conspire to produce blank images.

`images.py` handles the path half; `pdf_render.py` handles the origin half (it
loads the page from a real `file://` document — see [PDF Rendering](PDF-Rendering.md)).

## What it does

`rewrite_image_sources(html_body, base_dir, *, embed=False)` (images.py:38) runs
a regex over `<img …src="…">` tags and rewrites each local source:

1. **Skip remote/already-absolute sources.** The `_REMOTE` pattern matches
   `http:`, `https:`, `data:`, `file:`, and protocol-relative `//` — these are
   left untouched (remote images are fetched by Chromium at render time).
2. **Resolve relative paths** against `base_dir` (the source `.md` file's
   directory), expanding `~`.
3. **If the file doesn't exist**, the source is left *as-is* on purpose, so the
   broken reference stays visible/debuggable rather than being silently dropped.
4. **Otherwise rewrite** to either:
   - `file://` absolute URL (default), or
   - a base64 `data:` URI (when `embed=True`, i.e. `embed_images` / `--embed-images`).

`embed=True` is what produces a **fully self-contained PDF** — the bytes are
baked into the HTML, so there are no external file references at print time. The
trade-off is a larger intermediate HTML string.

## Implementation notes

- The `<img>` matcher (`_IMG_SRC`) handles single- or double-quoted `src` and is
  `DOTALL` so multi-line tags match. It deliberately only touches `src`.
- `_to_file_url()` builds `file://` + `quote(path)` so spaces and non-ASCII path
  characters are percent-encoded.
- `_to_data_uri()` guesses the MIME type from the filename (`application/
  octet-stream` fallback) and base64-encodes the bytes. If reading fails it
  returns `None` and the caller falls back to a `file://` URL.
- This module operates purely on the HTML string — it has no browser or config
  dependency, which makes it easy to unit-test (`tests/test_images.py`).

## Related test

`tests/test_converter.py::test_relative_parent_image_loads` is an end-to-end
regression (marked `slow`) that converts Markdown referencing a `../`-relative
image and asserts it actually embeds/loads — this is the guard against the
broken-image bug regressing.
