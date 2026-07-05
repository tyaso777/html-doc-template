"""Render generated chapter navigation and contents trees."""

from __future__ import annotations

import html
import os
from pathlib import Path
from typing import Any


def relative_path(from_file: Path, to_file: Path) -> str:
    try:
        return Path(os.path.relpath(to_file.resolve(), from_file.resolve().parent)).as_posix()
    except ValueError:
        return to_file.resolve().as_uri()


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


def render_chapter_nav(chapters: list[dict[str, Any]], index: int, output_path: Path, output_dir: Path, indent: str = "") -> str:
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
    chapters: list[dict[str, Any]],
    current_index: int,
    output_path: Path,
    output_dir: Path,
    toc_entries_by_chapter: list[list[dict[str, str | int]]],
    numbered_toc: bool = False,
    indent: str = "            ",
) -> str:
    lines: list[str] = []
    toc_tree_class = "toc-tree toc-tree-numbered" if numbered_toc else "toc-tree"

    for index, chapter in enumerate(chapters):
        chapter_path = output_dir / chapter["href"]
        href = html.escape(relative_path(output_path, chapter_path), quote=True)
        title = html.escape(chapter["title"])
        open_attr = " open" if index == current_index else ""
        current_attr = ' aria-current="page"' if index == current_index else ""
        lines.append(f'{indent}<li class="site-contents-chapter">')
        lines.append(f'{indent}  <details{open_attr}>')
        lines.append(f'{indent}    <summary><a href="{href}"{current_attr}>{title}</a></summary>')
        lines.append(f'{indent}    <ol class="{toc_tree_class}">')
        lines.append(render_chapter_toc_entries(toc_entries_by_chapter[index], chapter_path, output_path, indent + "      "))
        lines.append(f'{indent}    </ol>')
        lines.append(f'{indent}  </details>')
        lines.append(f'{indent}</li>')

    return "\n".join(lines)
