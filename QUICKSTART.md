# Quickstart

Use this file when you want to create a document from this template. This workflow requires only Python 3 and the Python standard library.

For project overview, template development, CI, and browser-test details, see [README.md](README.md).

## 1. Edit Content

Edit the source files under `chapters-src/`:

- `chapters-src/site-manifest.json`
- `chapters-src/*.html`

Files under `chapters-src/` are article fragments. They are inserted into `<article class="content">` by `scripts/build_site.py`.

Use top-level `externalLinks` in `chapters-src/site-manifest.json` for links that should appear on every chapter. Use optional chapter-level `externalLinks` for links that should appear only on that chapter.

If `headingNumbering.enabled` is `true` in `chapters-src/site-manifest.json`, write headings without hand-written numbers. The build script will add heading numbers to the generated `chapters/` files.

If figure/table/equation numbering is enabled in `numbering`, mark only intentional targets with `data-numbered` and reference them with `span[data-ref]`:

```html
<figure id="example-flow" data-numbered="figure">
  <figcaption>Example flow</figcaption>
</figure>
<p>See <span data-ref="example-flow"></span>.</p>
```

Do not include these in chapter fragments:

- `<!doctype>`
- `<html>`
- `<head>`
- `<body>`
- `<script>`
- `<link>`

Keep the shared shell, CDN assets, sidebar, CSS, and JavaScript in `layouts/chapter-shell.html`.

## 2. Add Sections

Use stable IDs and `data-toc` for sections that should appear in the table of contents:

```html
<section id="example-section" data-toc data-toc-title="Example Section">
  <h2>Example Section</h2>
  <p>Write the section content here.</p>
</section>
```

Optional lower-level TOC entries can use headings:

```html
<h3 id="example-detail" data-toc data-toc-level="3" data-toc-title="Example Detail">
  Example Detail
</h3>
```

## 3. Add Python Examples

For static Python code:

```html
<div class="code-caption">python</div>
<pre class="code-block language-python"><code class="language-python">print("Hello")</code></pre>
```

For executable Python examples, write only the source form:

```html
<div class="python-runner-source" data-python-runner>
  <p class="runner-caption">Try changing the values and run the code.</p>
  <pre><code class="language-python">scores = [72, 88, 91]
print(sum(scores) / len(scores))</code></pre>
</div>
```

Do not hand-write Pyodide buttons, textareas, output panels, or runtime wiring. The build script expands `div[data-python-runner]` into the full runner UI.

## 4. Build

Linux/macOS:

```bash
python3 scripts/build_site.py
```

Windows:

```powershell
py -3 scripts/build_site.py
```

Generated public chapter files are written under `chapters/`.

## 5. Check

Linux/macOS:

```bash
python3 scripts/check_html.py
```

Windows:

```powershell
py -3 scripts/check_html.py
```

Fix reported errors before publishing or committing generated output.

## 6. Commit Or Publish

If `chapters-src/` changes, rebuild `chapters/` before committing or publishing.

For a multi-page document, keep these together:

- `index.html`
- `assets/`
- `layouts/`
- `chapters-src/`
- `chapters/`
- `scripts/`

## AI Agent Rules

If you are an AI agent using this template:

- Prefer editing `chapters-src/`, not generated `chapters/`.
- Edit only the requested content unless asked to change the template.
- Create only article fragments for chapter content.
- Do not add full HTML document wrappers to chapter fragments.
- Do not add CDN tags, `<script>`, `<link>`, or custom runtime wiring to chapter fragments.
- For executable Python examples, use `div.python-runner-source` with `data-python-runner`.
- Run `python3 scripts/build_site.py` after content changes.
- Run `python3 scripts/check_html.py` after building.
- Do not require Node.js, npm, Playwright, or browser tests unless explicitly requested.
