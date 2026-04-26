#!/usr/bin/env python3
"""Build generated chapter HTML from source fragments and chapters-src/site-manifest.json.

Editable chapter bodies and the manifest live under chapters-src/. This script
combines each source fragment with layouts/chapter-shell.html, injects
Previous/Next navigation from the manifest order, and writes complete public
HTML files under chapters/.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
from pathlib import Path
from typing import Any

NAV_PATTERN = re.compile(
    r'<nav class="chapter-nav" data-chapter-nav aria-label="Chapter navigation">.*?</nav>',
    re.S,
)
PYTHON_RUNNER_SOURCE_PATTERN = re.compile(
    r'<div class="python-runner-source" data-python-runner>\s*'
    r'(?:<p class="runner-caption">(?P<caption>.*?)</p>\s*)?'
    r'<pre><code class="language-python">(?P<code>.*?)</code></pre>\s*'
    r'</div>',
    re.S,
)
ATTR_PATTERN = re.compile(r'([:\w-]+)(?:\s*=\s*"([^"]*)")?')
TOC_TARGET_PATTERN = re.compile(r'<(?P<tag>section|h[2-6])\b(?P<attrs>[^>]*)>', re.I)
REQUIRED_SHELL_TOKENS = {
    "{{DOCUMENT_TITLE}}",
    "{{SIDEBAR_TITLE}}",
    "{{SIDEBAR_SUBTITLE}}",
    "{{ASSET_PREFIX}}",
    "{{CONTENT}}",
    "{{CONTENTS_TREE}}",
    "{{MATERIALS_SECTION}}",
    "{{EXTERNAL_LINKS_SECTION}}",
}
FORBIDDEN_SOURCE_PATTERNS = (
    re.compile(r"<!doctype", re.I),
    re.compile(r"<html(?:\s|>)", re.I),
    re.compile(r"<head(?:\s|>)", re.I),
    re.compile(r"<body(?:\s|>)", re.I),
    re.compile(r"<script(?:\s|>)", re.I),
    re.compile(r"<link(?:\s|>)", re.I),
)


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def relative_path(from_file: Path, to_file: Path) -> str:
    return Path(os.path.relpath(to_file.resolve(), from_file.resolve().parent)).as_posix()


def asset_prefix(output_path: Path, root: Path) -> str:
    relative = Path(os.path.relpath(root.resolve(), output_path.resolve().parent)).as_posix()
    return "" if relative == "." else relative.rstrip("/") + "/"


def sidebar_title_html(title: str) -> str:
    return "<br>".join(html.escape(part.strip()) for part in title.splitlines() if part.strip())


def indent_content(content: str, indent: str) -> str:
    return "\n".join((indent + line if line else "") for line in content.splitlines())


def render_nav_link(direction: str, title: str, href: str, indent: str) -> str:
    label = "Previous" if direction == "previous" else "Next"
    item_indent = indent + "  "
    child_indent = indent + "    "
    return (
        f'{item_indent}<a class="chapter-nav-link {direction}" href="{html.escape(href, quote=True)}">\n'
        f"{child_indent}<span>{label}</span>\n"
        f"{child_indent}<strong>{html.escape(title)}</strong>\n"
        f"{item_indent}</a>"
    )


def render_chapter_nav(chapters: list[dict[str, str]], index: int, output_path: Path, output_dir: Path, indent: str = "") -> str:
    links: list[str] = []

    if index > 0:
        previous = chapters[index - 1]
        previous_path = output_dir / previous["href"]
        links.append(render_nav_link("previous", previous["title"], relative_path(output_path, previous_path), indent))

    if index < len(chapters) - 1:
        next_chapter = chapters[index + 1]
        next_path = output_dir / next_chapter["href"]
        links.append(render_nav_link("next", next_chapter["title"], relative_path(output_path, next_path), indent))

    if not links:
        return '<nav class="chapter-nav" data-chapter-nav aria-label="Chapter navigation"></nav>'

    return '<nav class="chapter-nav" data-chapter-nav aria-label="Chapter navigation">\n' + "\n".join(links) + f"\n{indent}</nav>"




def parse_attrs(raw_attrs: str) -> dict[str, str | None]:
    return {name: value for name, value in ATTR_PATTERN.findall(raw_attrs)}


def extract_toc_entries(source: str) -> list[dict[str, str | int]]:
    entries: list[dict[str, str | int]] = []
    source = re.sub(r"<!--.*?-->", "", source, flags=re.S)

    for match in TOC_TARGET_PATTERN.finditer(source):
        attrs = parse_attrs(match.group("attrs"))
        if "data-toc" not in attrs or "id" not in attrs:
            continue

        element_id = attrs.get("id")
        if not element_id or element_id == "...":
            continue

        title = attrs.get("data-toc-title") or element_id
        raw_level = attrs.get("data-toc-level")
        if raw_level and raw_level.isdigit():
            level = int(raw_level)
        elif match.group("tag").lower().startswith("h"):
            level = int(match.group("tag")[1])
        else:
            level = 2

        entries.append({"id": element_id, "title": title, "level": level})

    return entries


def render_toc_entry_link(entry: dict[str, str | int], chapter_path: Path, output_path: Path, indent: str) -> str:
    href = f"{relative_path(output_path, chapter_path)}#{entry['id']}"
    return f'{indent}<li><a href="{html.escape(href, quote=True)}">{html.escape(str(entry["title"]))}</a></li>'


def group_toc_entries(entries: list[dict[str, str | int]]) -> list[dict[str, object]]:
    groups: list[dict[str, object]] = []

    for entry in entries:
        if int(entry["level"]) <= 2 or not groups:
            groups.append({"entry": entry, "children": []})
        else:
            children = groups[-1]["children"]
            assert isinstance(children, list)
            children.append(entry)

    return groups


def render_chapter_toc_entries(entries: list[dict[str, str | int]], chapter_path: Path, output_path: Path, indent: str) -> str:
    groups = group_toc_entries(entries)

    if not groups:
        return f"{indent}<li>No sections</li>"

    lines: list[str] = []
    for group in groups:
        entry = group["entry"]
        children = group["children"]
        assert isinstance(entry, dict)
        assert isinstance(children, list)
        href = f"{relative_path(output_path, chapter_path)}#{entry['id']}"
        lines.append(f'{indent}<li><a href="{html.escape(href, quote=True)}">{html.escape(str(entry["title"]))}</a>')
        if children:
            lines.append(f"{indent}  <ol>")
            for child in children:
                assert isinstance(child, dict)
                lines.append(render_toc_entry_link(child, chapter_path, output_path, indent + "    "))
            lines.append(f"{indent}  </ol>")
        lines.append(f"{indent}</li>")

    return "\n".join(lines)


def render_contents_tree(
    chapters: list[dict[str, str]],
    current_index: int,
    output_path: Path,
    output_dir: Path,
    toc_entries_by_chapter: list[list[dict[str, str | int]]],
    indent: str = "            ",
) -> str:
    lines: list[str] = []

    for index, chapter in enumerate(chapters):
        chapter_path = output_dir / chapter["href"]
        href = html.escape(relative_path(output_path, chapter_path), quote=True)
        title = html.escape(chapter["title"])
        open_attr = " open" if index == current_index else ""
        current_attr = ' aria-current="page"' if index == current_index else ""
        lines.append(f'{indent}<li class="site-contents-chapter">')
        lines.append(f'{indent}  <details{open_attr}>')
        lines.append(f'{indent}    <summary><a href="{href}"{current_attr}>{title}</a></summary>')
        lines.append(f'{indent}    <ol class="toc-tree">')
        lines.append(render_chapter_toc_entries(toc_entries_by_chapter[index], chapter_path, output_path, indent + "      "))
        lines.append(f'{indent}    </ol>')
        lines.append(f'{indent}  </details>')
        lines.append(f'{indent}</li>')

    return "\n".join(lines)

def render_python_runner(caption: str | None, code: str) -> str:
    help_text = caption or "Edit the code in the highlighted Python editor, then press Run Python."
    encoded_code = base64.b64encode(html.unescape(code).strip("\n").encode("utf-8")).decode("ascii")
    return f'''<div class="runner-panel">
  <p id="python-code-help">
    {help_text}
    On slow connections or constrained devices, the first Python runtime load can take some time.
  </p>

  <div class="runner-toolbar">
    <button id="load-button" class="button secondary" type="button">Load Python Runtime</button>
    <button id="run-button" class="button" type="button" disabled>Run Python</button>
    <button id="reset-button" class="button secondary" type="button">Reset Code Text</button>
    <button id="restart-runtime-button" class="button secondary" type="button" disabled>Restart Python Runtime</button>
  </div>

  <label for="python-code" class="visually-hidden">Python code editor</label>
  <div class="python-editor-wrap">
    <textarea
      id="python-code"
      spellcheck="false"
      aria-describedby="python-code-help output"
      autocomplete="off"
      autocorrect="off"
      autocapitalize="off"
      data-initial-code-base64="{encoded_code}"
    ></textarea>
    <button id="copy-python-code-button" class="copy-code-button python-editor-copy-button" type="button" aria-label="Copy Python code">Copy</button>
  </div>

  <h3>Output</h3>
  <div
    id="output"
    class="output"
    role="log"
    aria-live="polite"
    aria-atomic="true"
  >Press "Load Python Runtime" first. Python will run in a Web Worker.</div>

  <section class="print-only print-runner-snapshot" aria-label="Printed Python runner snapshot">
    <h3>Printed Python Code</h3>
    <pre id="print-python-code" class="print-code-block"></pre>

    <h3>Printed Python Output</h3>
    <pre id="print-python-output" class="print-output-block"></pre>
  </section>
</div>'''


def expand_python_runners(source: str) -> str:
    def replace(match: re.Match[str]) -> str:
        return render_python_runner(match.group("caption"), match.group("code"))

    return PYTHON_RUNNER_SOURCE_PATTERN.sub(replace, source)


def inject_chapter_nav(source: str, chapters: list[dict[str, str]], index: int, output_path: Path, output_dir: Path) -> str:
    matches = list(NAV_PATTERN.finditer(source))

    if len(matches) != 1:
        raise ValueError(f'{chapters[index]["source"]} must contain exactly one data-chapter-nav element')

    match = matches[0]
    line_start = source.rfind("\n", 0, match.start()) + 1
    indent = source[line_start:match.start()]
    nav = render_chapter_nav(chapters, index, output_path, output_dir, indent)
    return source[:match.start()] + nav + source[match.end():]


def validate_source_fragment(source_path: Path, text: str) -> None:
    for pattern in FORBIDDEN_SOURCE_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"{source_path} should be an article fragment and must not match {pattern.pattern}")



def is_external_href(href: str) -> bool:
    return href.startswith(("http://", "https://", "mailto:", "tel:"))


def render_manifest_href(href: str, manifest_dir: Path, output_path: Path) -> str:
    if is_external_href(href) or href.startswith("#"):
        return href
    return relative_path(output_path, manifest_dir / href)


def render_link_tree_items(
    items: list[Any],
    manifest_dir: Path,
    output_path: Path,
    external_section: bool,
    indent: str,
) -> str:
    lines: list[str] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        title = item.get("title")
        nested_items = item.get("items")
        label = item.get("label")
        href = item.get("href")

        if isinstance(title, str) and isinstance(nested_items, list):
            lines.append(f'{indent}<li>')
            lines.append(f'{indent}  <span class="nav-list-category">{html.escape(title)}</span>')
            lines.append(f'{indent}  <ol>')
            nested = render_link_tree_items(nested_items, manifest_dir, output_path, external_section, indent + "    ")
            if nested:
                lines.append(nested)
            lines.append(f'{indent}  </ol>')
            lines.append(f'{indent}</li>')
            continue

        if isinstance(label, str) and isinstance(href, str):
            rendered_href = html.escape(render_manifest_href(href, manifest_dir, output_path), quote=True)
            attrs = ''
            if external_section and is_external_href(href):
                attrs = ' target="_blank" rel="noopener"'
            lines.append(f'{indent}<li><a href="{rendered_href}"{attrs}>{html.escape(label)}</a></li>')

    return "\n".join(lines)


def render_link_section(
    section_title: str,
    items: list[Any],
    manifest_dir: Path,
    output_path: Path,
    external_section: bool = False,
    indent: str = "      ",
) -> str:
    body = render_link_tree_items(items, manifest_dir, output_path, external_section, indent + "        ")
    if not body:
        return ""

    return (
        f'{indent}<details class="nav-section">\n'
        f'{indent}  <summary>{html.escape(section_title)}</summary>\n'
        f'{indent}  <div class="nav-body">\n'
        f'{indent}    <ol class="nav-list">\n'
        f'{body}\n'
        f'{indent}    </ol>\n'
        f'{indent}  </div>\n'
        f'{indent}</details>'
    )

def render_shell(
    shell: str,
    chapter: dict[str, str],
    content: str,
    output_path: Path,
    root: Path,
    manifest_dir: Path,
    chapters: list[dict[str, str]],
    current_index: int,
    output_dir: Path,
    toc_entries_by_chapter: list[list[dict[str, str | int]]],
    materials: list[Any],
    external_links: list[Any],
) -> str:
    replacements = {
        "{{DOCUMENT_TITLE}}": html.escape(chapter["title"]),
        "{{SIDEBAR_TITLE}}": sidebar_title_html(chapter.get("sidebarTitle", chapter["title"])),
        "{{SIDEBAR_SUBTITLE}}": html.escape(chapter.get("subtitle", "")),
        "{{ASSET_PREFIX}}": asset_prefix(output_path, root),
        "{{CONTENTS_TREE}}": render_contents_tree(chapters, current_index, output_path, output_dir, toc_entries_by_chapter),
        "{{MATERIALS_SECTION}}": render_link_section("Materials", materials, manifest_dir, output_path),
        "{{EXTERNAL_LINKS_SECTION}}": render_link_section("External Links", external_links, manifest_dir, output_path, external_section=True),
        "{{CONTENT}}": indent_content(content.rstrip(), "        "),
    }

    rendered = shell
    for token, value in replacements.items():
        rendered = rendered.replace(token, value)
    return rendered


def build_chapter(
    root: Path,
    manifest_dir: Path,
    output_dir: Path,
    shell: str,
    chapters: list[dict[str, str]],
    index: int,
    toc_entries_by_chapter: list[list[dict[str, str | int]]],
    materials: list[Any],
    external_links: list[Any],
) -> Path:
    chapter = chapters[index]
    source_path = manifest_dir / chapter["source"]
    output_path = output_dir / chapter["href"]

    source = source_path.read_text(encoding="utf-8")
    validate_source_fragment(source_path, source)
    source = expand_python_runners(source)
    content = inject_chapter_nav(source, chapters, index, output_path, output_dir)
    text = render_shell(
        shell,
        chapter,
        content,
        output_path,
        root,
        manifest_dir,
        chapters,
        index,
        output_dir,
        toc_entries_by_chapter,
        materials,
        external_links,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return output_path


def validate_shell(shell: str, shell_path: Path) -> None:
    missing = sorted(token for token in REQUIRED_SHELL_TOKENS if token not in shell)
    if missing:
        raise ValueError(f"{shell_path} is missing required token(s): {', '.join(missing)}")


def validate_manifest(manifest: dict[str, Any]) -> tuple[str, str, list[dict[str, str]], list[Any], list[Any]]:
    shell = manifest.get("shell", "../layouts/chapter-shell.html")
    output_dir = manifest.get("outputDir", "../chapters")
    materials = manifest.get("materials", [])
    external_links = manifest.get("externalLinks", [])

    if not isinstance(shell, str) or not shell.strip():
        raise ValueError("site manifest must have a non-empty shell path")
    if not isinstance(output_dir, str) or not output_dir.strip():
        raise ValueError("site manifest must have a non-empty outputDir")

    if not isinstance(materials, list):
        raise ValueError("site manifest materials must be an array when provided")
    if not isinstance(external_links, list):
        raise ValueError("site manifest externalLinks must be an array when provided")

    chapters = manifest.get("chapters")
    if not isinstance(chapters, list):
        raise ValueError("site manifest must contain a chapters array")

    normalized: list[dict[str, str]] = []
    for index, chapter in enumerate(chapters, start=1):
        if not isinstance(chapter, dict):
            raise ValueError(f"chapter {index} must be an object")

        title = chapter.get("title")
        href = chapter.get("href")
        source = chapter.get("source")
        sidebar_title = chapter.get("sidebarTitle", title)
        subtitle = chapter.get("subtitle", "")

        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"chapter {index} must have a non-empty title")
        if not isinstance(href, str) or not href.strip():
            raise ValueError(f"chapter {index} must have a non-empty href")
        if not isinstance(source, str) or not source.strip():
            raise ValueError(f"chapter {index} must have a non-empty source")
        if not isinstance(sidebar_title, str):
            raise ValueError(f"chapter {index} sidebarTitle must be a string")
        if not isinstance(subtitle, str):
            raise ValueError(f"chapter {index} subtitle must be a string")

        normalized.append({"title": title, "href": href, "source": source, "sidebarTitle": sidebar_title, "subtitle": subtitle})

    return shell, output_dir, normalized, materials, external_links


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build generated chapter HTML from source fragments and chapters-src/site-manifest.json.")
    parser.add_argument("--root", default=".", help="Project root.")
    parser.add_argument("--manifest", default="chapters-src/site-manifest.json", help="Manifest path relative to root.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    manifest_path = (root / args.manifest).resolve()
    manifest_dir = manifest_path.parent
    manifest = load_manifest(manifest_path)
    shell_path_raw, output_dir_raw, chapters, materials, external_links = validate_manifest(manifest)
    shell_path = (manifest_dir / shell_path_raw).resolve()
    output_dir = (manifest_dir / output_dir_raw).resolve()
    shell = shell_path.read_text(encoding="utf-8")
    validate_shell(shell, shell_path)

    toc_entries_by_chapter = [
        extract_toc_entries((manifest_dir / chapter["source"]).read_text(encoding="utf-8"))
        for chapter in chapters
    ]

    for index in range(len(chapters)):
        output_path = build_chapter(
            root,
            manifest_dir,
            output_dir,
            shell,
            chapters,
            index,
            toc_entries_by_chapter,
            materials,
            external_links,
        )
        print(f"built {output_path.relative_to(root)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
