# html-doc-template

HTML templates for technical documents that include code blocks, math, diagrams, and optional in-browser Python execution.

The browser entry page is `index.html`.

Main templates:

```text
templates/technical-doc-template.html      # document template using assets/
templates/content-example.html          # content-only fragment for AI-assisted authoring
```

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
    check_html.py
  templates/
    technical-doc-template.html
    content-example.html
```

## Template Files

Use `templates/technical-doc-template.html` as the maintained document template. It keeps layout, CSS, and JavaScript separate from the document content, which is better for iterative authoring and AI-assisted content generation.

Use `templates/content-example.html` as a content-only reference. Generated content should be pasted inside `<article class="content">` in a shell document and should not include `<html>`, `<head>`, `<style>`, or `<script>`.

## Basic Usage

Copy `templates/technical-doc-template.html` and edit the copy.

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

Mermaid code block and rendered diagram examples are included in the template.

## AI-Assisted Authoring

When asking a generation model to create content for the split template, constrain the task to the article content only. A useful instruction is:

```text
Create only the HTML fragment for <article class="content">.
Do not include html, head, style, script, or external library tags.
Use existing classes such as callout, card, code-block, math-block, and mermaid.
Use section elements with id, data-toc, and data-toc-title for TOC entries.
```

## HTML Checker

Run the lightweight checker after editing generated or AI-assisted HTML:

```bash
python3 scripts/check_html.py
```

The checker uses only the Python standard library. It validates duplicate IDs, missing `data-toc` IDs, local file links, same-page fragment links, `aria-describedby` references, and `pre.code-block` / `code.language-*` consistency.

When using this template in another document project, copy `scripts/check_html.py` with the template and run it against the generated HTML file.

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

The initial Python code is stored in the `DEFAULT_CODE` JavaScript constant in `assets/js/technical-doc.js`.

## Notes

This project is intended as a source template. Documents created from it should usually be copied into another project or an `examples/` directory rather than editing the base template directly for each document.
