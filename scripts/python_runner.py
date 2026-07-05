"""Expand source Python runner placeholders into generated runner markup."""

from __future__ import annotations

import base64
import html

try:
    from html_fragment import (
        FragmentNode,
        has_class,
        iter_nodes,
        node_inner_html,
        parse_fragment,
        replace_ranges,
        text_content,
    )
except ModuleNotFoundError:
    from scripts.html_fragment import (
        FragmentNode,
        has_class,
        iter_nodes,
        node_inner_html,
        parse_fragment,
        replace_ranges,
        text_content,
    )


def render_python_runner(caption: str | None, code: str, runner_id: str) -> str:
    default_help = "Edit the code in the highlighted Python editor, then press Run Python."
    help_text = html.escape(html.unescape(caption or default_help))
    encoded_code = base64.b64encode(html.unescape(code).strip("\n").encode("utf-8")).decode("ascii")
    help_id = f"{runner_id}-help"
    code_id = f"{runner_id}-code"
    output_id = f"{runner_id}-output"
    print_code_id = f"{runner_id}-print-code"
    print_output_id = f"{runner_id}-print-output"
    return f'''<div class="runner-panel" data-python-runner-panel>
  <p id="{help_id}" data-python-runner-help>
    {help_text}
    On slow connections or constrained devices, the first Python runtime load can take some time.
  </p>

  <div class="runner-toolbar">
    <button class="button secondary" type="button" data-python-load-button>Load Python Runtime</button>
    <button class="button" type="button" data-python-run-button disabled>Run Python</button>
    <button class="button secondary" type="button" data-python-reset-button>Reset Code Text</button>
    <button class="button secondary" type="button" data-python-restart-button disabled>Restart Python Runtime</button>
  </div>

  <label for="{code_id}" class="visually-hidden">Python code editor</label>
  <div class="python-editor-wrap">
    <textarea
      id="{code_id}"
      spellcheck="false"
      aria-describedby="{help_id} {output_id}"
      autocomplete="off"
      autocorrect="off"
      autocapitalize="off"
      data-initial-code-base64="{encoded_code}"
      data-python-code
    ></textarea>
    <button class="copy-code-button python-editor-copy-button" type="button" aria-label="Copy Python code" data-python-copy-button>Copy</button>
  </div>

  <h3>Output</h3>
  <div
    id="{output_id}"
    class="output"
    role="log"
    aria-live="polite"
    aria-atomic="true"
    data-python-output
  >Press "Load Python Runtime" first. Python will run in a Web Worker.</div>

  <section class="print-only print-runner-snapshot" aria-label="Printed Python runner snapshot">
    <h3>Printed Python Code</h3>
    <pre id="{print_code_id}" class="print-code-block" data-python-print-code></pre>

    <h3>Printed Python Output</h3>
    <pre id="{print_output_id}" class="print-output-block" data-python-print-output></pre>
  </section>
</div>'''


def extract_python_runner_source(source: str, node: FragmentNode) -> tuple[str | None, str]:
    descendants = iter_nodes(node.children)
    caption_nodes = [
        child
        for child in descendants
        if child.tag == "p" and has_class(child.attrs, "runner-caption")
    ]
    code_nodes = [
        child
        for child in descendants
        if child.tag == "code" and has_class(child.attrs, "language-python")
    ]

    if len(code_nodes) != 1:
        raise ValueError("each data-python-runner element must contain exactly one code.language-python element")

    caption = text_content(source, caption_nodes[0]) if caption_nodes else None
    code = node_inner_html(source, code_nodes[0])
    return caption, code


def expand_python_runners(source: str) -> str:
    replacements: list[tuple[int, int, str]] = []
    runner_nodes = [
        node
        for node in iter_nodes(parse_fragment(source))
        if "data-python-runner" in node.attrs
    ]

    for runner_index, node in enumerate(runner_nodes, start=1):
        if node.end is None:
            raise ValueError("data-python-runner element is missing its closing tag")

        caption, code = extract_python_runner_source(source, node)
        replacements.append((node.start, node.end, render_python_runner(caption, code, f"python-runner-{runner_index}")))

    return replace_ranges(source, replacements)
