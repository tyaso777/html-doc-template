"""Render manifest-managed sidebar link sections."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from .navigation import relative_path


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


def chapter_external_links(common_external_links: list[Any], chapter: dict[str, Any]) -> list[Any]:
    specific_external_links = chapter.get("externalLinks", [])
    if not specific_external_links:
        return common_external_links
    assert isinstance(specific_external_links, list)
    return [*common_external_links, *specific_external_links]
