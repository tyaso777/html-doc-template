# html-doc-template

HTML templates for technical documents that include code blocks, math, diagrams, and optional in-browser Python execution.

Live demo: https://tyaso777.github.io/html-doc-template/

The browser entry page is `index.html`.

Main files:

```text
chapters-src/                         # editable chapter fragments and manifest
layouts/chapter-shell.html             # shared shell used by the build script
```

## Positioning

This project is not a full static site generator, Markdown converter, or web application framework.

It can be used for single-page or multi-page HTML documents. For multi-page chapter sets, `scripts/build_site.py` copies source chapters from `chapters-src/` to `chapters/` and injects Previous/Next navigation from `chapters-src/site-manifest.json`. It does not provide routes, search indexes, theme systems, or content pipelines.

Use this template when you want:

- Direct control over document HTML, CSS, and browser behavior.
- Shared CSS and JavaScript for single-page documents without a build step.
- Built-in examples for code highlighting, MathJax, Mermaid, and optional Pyodide execution.
- A structure that works well with AI-assisted authoring by generating only the `<article class="content">` fragment.
- Easy publishing through GitHub Pages.

If you primarily want Markdown-first authoring, automatic page generation, site-wide navigation, search indexes, theme systems, or content pipelines, a static site generator may be a better fit.

## Features

- Responsive two-column layout with a collapsible sidebar.
- Auto-generated table of contents from `data-toc` elements.
- Document metadata block for version, update date, and author.
- Callout blocks for notes and warnings.
- Card components for compact document sections.
- Prism code highlighting for Python, PowerShell, SQL, and Mermaid.
- Copy buttons for static code blocks and the Python runner editor.
- MathJax support for inline and display math.
- Mermaid diagram rendering from text definitions.
- Optional Pyodide-based Python runner in a Web Worker.
- Changelog table for versioned document maintenance.
- Project entry page for local browsing or GitHub Pages.

## Project Structure

```text
html-doc-template/
  README.md
  index.html
  html-doc-template.code-workspace
  assets/
    css/
      technical-doc.css
    js/
      technical-doc.js
  scripts/
    build_site.py
    check_html.py
    html_fragment.py
    run_python.mjs
    site_manifest.py
  chapters-src/
    site-manifest.json
    01-introduction.html
    02-examples.html
    03-reference.html
  chapters/
    01-introduction.html
    02-examples.html
    03-reference.html
  layouts/
    chapter-shell.html
```

## Folder Roles

Use `layouts/chapter-shell.html` as the shared wrapper for generated multi-page chapters. It contains the document shell: `<html>`, `<head>`, CDN assets, sidebar, shared CSS, and shared JavaScript.

## Basic Usage

For the multi-page workflow, edit `chapters-src/*.html` and `chapters-src/site-manifest.json`, then run `npm run build`.

Typical edits:

- Replace the document title and subtitle.
- Update the document metadata.
- Add sections with `id`, `data-toc`, and `data-toc-title`.
- Replace sample math, code, Mermaid, and Python runner content.
- Update Materials and External Links in the sidebar as needed.
- Update the changelog when publishing a new version.

Top-level sections that should appear in the sidebar TOC should use this pattern:

```html
<section id="example-section" data-toc data-toc-title="Example Section">
  <h2>Example Section</h2>
</section>
```

Optional lower-level TOC entries can use:

```html
<h3 id="example-subsection" data-toc data-toc-level="3" data-toc-title="Example Subsection">
  Example Subsection
</h3>
```

## Multi-page Documents

This template can be used for multi-page documents by sharing one shell template and the same `assets/` directory across generated HTML files. In this workflow, edit `chapters-src/` and treat `chapters/` as generated output. See `chapters/01-introduction.html`, `chapters/02-examples.html`, and `chapters/03-reference.html` for a minimal three-page example.

Each file under `chapters-src/` is an article fragment, not a complete HTML document. It should contain only the content that belongs inside `<article class="content">`. Keep CDN assets, `<head>`, sidebar markup, shared CSS, and shared JavaScript in `layouts/chapter-shell.html`.

Edit chapter source files under `chapters-src/`, define chapter order and shell metadata in `chapters-src/site-manifest.json`, then build the public chapter files under `chapters/`:

```bash
npm run build
```

The npm build command runs `scripts/build_site.py` through `scripts/run_python.mjs`, which detects Python from `PYTHON`, `python3`, `python`, or the Windows `py -3` launcher. If you prefer to call Python directly, use `python3 scripts/build_site.py` on Linux/macOS or `py -3 scripts/build_site.py` on Windows.

Each source chapter should include a chapter navigation placeholder near the end of the fragment:

```html
<nav class="chapter-nav" data-chapter-nav aria-label="Chapter navigation"></nav>
```

`scripts/build_site.py` reads `chapters-src/site-manifest.json`, combines each source fragment with `layouts/chapter-shell.html`, writes the left-side nested Contents tree from all chapter TOC entries, renders manifest-managed Materials and External Links sections, and writes the generated Previous and Next links into each output file. It uses Python's standard-library HTML parser for chapter TOC extraction, Python runner expansion, and chapter navigation replacement. This keeps chapter order, document language, shell metadata, and document-level link lists in one place while keeping the generated HTML usable through GitHub Pages or direct `file://` previews.

CI runs the build and checks that the generated `chapters/` files have no uncommitted diff, so updates to `chapters-src/` should be committed together with the rebuilt public chapter files.

```json
{
  "title": "html-doc-template chapter examples",
  "lang": "en",
  "shell": "../layouts/chapter-shell.html",
  "outputDir": "../chapters",
  "chapters": [
    {
      "title": "Chapter 1: Introduction",
      "sidebarTitle": "Chapter 1\nIntroduction",
      "subtitle": "Multi-page example",
      "source": "01-introduction.html",
      "href": "01-introduction.html"
    },
    {
      "title": "Chapter 2: Minimal Page",
      "sidebarTitle": "Chapter 2\nMinimal Page",
      "subtitle": "Multi-page example",
      "source": "02-examples.html",
      "href": "02-examples.html"
    },
    {
      "title": "Chapter 3: Reference Page",
      "sidebarTitle": "Chapter 3\nReference Page",
      "subtitle": "Multi-page example",
      "source": "03-reference.html",
      "href": "03-reference.html"
    }
  ],
  "materials": [
    {
      "title": "Project",
      "items": [
        { "label": "Project index", "href": "../index.html" },
        { "label": "Repository README", "href": "../README.md" }
      ]
    }
  ],
  "externalLinks": [
    {
      "title": "Rendering",
      "items": [
        { "label": "Prism.js", "href": "https://prismjs.com/" },
        { "label": "MathJax", "href": "https://www.mathjax.org/" },
        { "label": "Mermaid", "href": "https://mermaid.js.org/" }
      ]
    },
    {
      "title": "Python runtime",
      "items": [
        { "label": "Pyodide", "href": "https://pyodide.org/" }
      ]
    }
  ]
}
```

`materials` and `externalLinks` use the same recursive `items` structure. An item with `label` and `href` is rendered as a link. An item with `title` and `items` is rendered as a nested group.

## Common Components

Use these patterns inside the document body:

```html
<aside class="callout callout-success">Supplemental note.</aside>
<aside class="callout callout-warning">Important warning.</aside>
<div class="card">Standard card content.</div>
<div class="card card-muted">Subtle card content.</div>
<div class="card card-compact">Compact card content.</div>
```

Python code block:

```html
<div class="code-caption">python</div>
<pre class="code-block language-python"><code class="language-python">print("Hello")</code></pre>
```

Executable Python runner source block for `chapters-src/`:

```html
<div class="python-runner-source" data-python-runner>
  <p class="runner-caption">Try changing the values and run the code.</p>
  <pre><code class="language-python">scores = [72, 88, 91]
print(sum(scores) / len(scores))</code></pre>
</div>
```

`build_site.py` expands each `div[data-python-runner]` into a scoped Pyodide runner UI in the generated `chapters/` files. A generated page may contain multiple runner blocks. Do not write Load, Run, Restart buttons, textareas, or output panels by hand in `chapters-src/`.

Mermaid code block and rendered diagram examples are included in the template.

## AI-Assisted Authoring

When asking a generation model to create content for the split template, constrain the task to the article fragment only. A useful instruction is:

```text
Create only the HTML fragment that will be inserted inside <article class="content">.
Do not include doctype, html, head, body, style, script, link, CDN, or external library tags.
Use existing classes such as callout, card, code-block, math-block, and mermaid.
For executable Python examples, use div.python-runner-source with data-python-runner and a pre/code.language-python block.
Do not write Pyodide buttons, textareas, output panels, or runtime wiring by hand.
Use section elements with id, data-toc, and data-toc-title for TOC entries.
```

## HTML Checker

Run the lightweight checker after editing generated or AI-assisted HTML:

```bash
npm run check:html
```

To run the checker directly without npm, use `python3 scripts/check_html.py` on Linux/macOS or `py -3 scripts/check_html.py` on Windows.

The checker uses only the Python standard library. It validates duplicate IDs, missing `data-toc` IDs, local file links, same-page fragment links, `aria-describedby` references, `pre.code-block` / `code.language-*` consistency, chapter manifest integrity, shell template tokens, generated Previous/Next navigation, and the scoped IDs emitted for generated Python runners.

When using this template in another document project, copy `scripts/check_html.py`, `scripts/html_fragment.py`, and `scripts/site_manifest.py` with the template and run the checker against the generated HTML file. For multi-page chapter sets, keep `chapters-src/site-manifest.json`, `chapters-src/`, and `chapters/` together so the manifest checks can verify generated navigation.

## Browser Smoke Tests

Browser smoke tests use Playwright as a development dependency. They verify that generated chapters open in Chromium, the sidebar and chapter navigation work, and JavaScript enhancements initialize for copy buttons, CodeMirror, MathJax, and Mermaid.

Install the test dependency and browser once:

```bash
npm install
npx playwright install chromium
```

On Linux systems that do not already have Chromium runtime libraries, run Playwright's dependency helper:

```bash
npx playwright install-deps chromium
```

Run the regular browser smoke tests on Windows, macOS, Linux, or WSL:

```bash
npm run test:e2e
```

The Pyodide runtime test is intentionally separate because it downloads and starts Pyodide from the CDN:

```bash
npm run test:e2e:pyodide
```

If a WSL environment accidentally points Node or Playwright temporary files at the Windows temp directory, set `TMPDIR` only for that local run:

```bash
TMPDIR=/tmp npm run test:e2e
TMPDIR=/tmp npm run test:e2e:pyodide
```

Windows `cmd.exe` and PowerShell users usually do not need `TMPDIR`. The Pyodide smoke-test flag is set through `cross-env` in `package.json` so the same `npm run test:e2e:pyodide` command works across Windows, macOS, Linux, and WSL.

## External Libraries

The template currently loads these libraries from CDN:

- Prism
- CodeMirror
- MathJax
- Mermaid
- Pyodide

Normal script and stylesheet CDN assets use SRI where applicable.

Pyodide is different: it is loaded inside a Web Worker with `importScripts()` when the user presses `Load Python Runtime`. `importScripts()` does not support normal script-tag SRI. If strict supply-chain verification is required, host a reviewed Pyodide build locally and update `PYODIDE_WORKER_CONFIG` in the template or split JavaScript.

## Python Runner

The Python runner is optional. The document remains readable without loading Pyodide.

For generated chapters, initial Python code is taken from `div[data-python-runner]` blocks in `chapters-src/`. The `DEFAULT_CODE` JavaScript constant in `assets/js/technical-doc.js` remains a fallback for standalone pages.

## Notes

This project is intended as a source template. Documents created from it should usually be copied into another project rather than editing the base template directly for each document.

## Third-party Libraries

This template loads third-party libraries from public CDNs. Those libraries are distributed under their own licenses, including MIT, Apache-2.0, and MPL-2.0. The MIT License in this repository applies to the template files maintained here, not to third-party libraries loaded from CDNs.

## License

The template files in this repository are licensed under the MIT License.

Documents, course materials, and other content created with this template may use a different license.
