from __future__ import annotations

import html
from pathlib import Path
from typing import Any

try:
    from html_fragment import FragmentNode, iter_nodes, parse_fragment, replace_ranges
    from site_builder.navigation import relative_path
except ModuleNotFoundError:
    from scripts.html_fragment import FragmentNode, iter_nodes, parse_fragment, replace_ranges
    from scripts.site_builder.navigation import relative_path


NUMBERED_KIND_TO_SECTION = {"figure": "figures", "table": "tables", "equation": "equations"}
NUMBERED_KIND_TO_CLASS = {"figure": "figure-number", "table": "table-number", "equation": "equation-number"}


def numbered_kind_config(numbering: dict[str, Any], kind: str) -> dict[str, Any]:
    section = NUMBERED_KIND_TO_SECTION[kind]
    config = numbering.get(section, {})
    return config if isinstance(config, dict) else {}


def numbered_kind_enabled(numbering: dict[str, Any], kind: str) -> bool:
    return bool(numbered_kind_config(numbering, kind).get("enabled", False))


def format_numbered_item_label(format_text: str, chapter: str, index: int) -> str:
    return format_text.replace("{chapter}", chapter).replace("{index}", str(index))


def collect_numbered_items(
    chapter_sources: list[str],
    chapters: list[dict[str, Any]],
    numbering: dict[str, Any],
) -> dict[str, dict[str, str]]:
    registry: dict[str, dict[str, str]] = {}
    document_counters = {kind: 0 for kind in NUMBERED_KIND_TO_SECTION}

    for chapter_index, source in enumerate(chapter_sources):
        chapter = chapters[chapter_index]
        chapter_counters = {kind: 0 for kind in NUMBERED_KIND_TO_SECTION}
        chapter_number = str(chapter.get("number", chapter_index + 1))

        for node in iter_nodes(parse_fragment(source)):
            kind = node.attrs.get("data-numbered")
            if kind not in NUMBERED_KIND_TO_SECTION or not numbered_kind_enabled(numbering, kind):
                continue

            element_id = node.attrs.get("id")
            if not element_id:
                raise ValueError(f'{chapter["source"]} data-numbered="{kind}" element must have an id')
            if element_id in registry:
                raise ValueError(f'duplicate numbered reference id "{element_id}"')

            config = numbered_kind_config(numbering, kind)
            if config.get("reset", "chapter") == "document":
                document_counters[kind] += 1
                item_index = document_counters[kind]
            else:
                chapter_counters[kind] += 1
                item_index = chapter_counters[kind]

            label = format_numbered_item_label(str(config.get("format", "{index}")), chapter_number, item_index)
            registry[element_id] = {
                "id": element_id,
                "kind": kind,
                "label": label,
                "chapterHref": str(chapter["href"]),
                "source": str(chapter["source"]),
            }

    return registry


def numbered_label_html(item: dict[str, str]) -> str:
    class_name = NUMBERED_KIND_TO_CLASS[item["kind"]]
    return f'<span class="numbered-label {class_name}">{html.escape(item["label"])}</span>'


def first_child_by_tag(node: FragmentNode, tag: str) -> FragmentNode | None:
    return next((child for child in node.children if child.tag == tag), None)


def numbered_caption_replacement(node: FragmentNode, item: dict[str, str]) -> tuple[int, int, str] | None:
    label = numbered_label_html(item)
    kind = item["kind"]

    if kind == "figure":
        caption = first_child_by_tag(node, "figcaption")
        if caption is not None:
            return (caption.start_tag_end, caption.start_tag_end, f"{label} ")
        if node.end_tag_start is not None:
            return (node.end_tag_start, node.end_tag_start, f"\n  <figcaption>{label}</figcaption>\n")
        return None

    if kind == "table":
        caption = first_child_by_tag(node, "caption")
        if caption is not None:
            return (caption.start_tag_end, caption.start_tag_end, f"{label} ")
        return (node.start_tag_end, node.start_tag_end, f"\n  <caption>{label}</caption>")

    if kind == "equation":
        if node.end_tag_start is not None:
            return (node.end_tag_start, node.end_tag_start, f'\n  <div class="equation-label">{label}</div>\n')
        return None

    return None


def numbered_ref_href(item: dict[str, str], output_path: Path, output_dir: Path) -> str:
    target_path = output_dir / item["chapterHref"]
    return f"{relative_path(output_path, target_path)}#{item['id']}"


def numbered_ref_link(item: dict[str, str], output_path: Path, output_dir: Path) -> str:
    href = html.escape(numbered_ref_href(item, output_path, output_dir), quote=True)
    label = html.escape(item["label"])
    return f'<a class="xref {item["kind"]}-ref" href="{href}">{label}</a>'


def replace_explicit_numbered_refs(
    source: str,
    registry: dict[str, dict[str, str]],
    output_path: Path,
    output_dir: Path,
) -> str:
    replacements: list[tuple[int, int, str]] = []
    for node in iter_nodes(parse_fragment(source)):
        ref_id = node.attrs.get("data-ref")
        if ref_id is None:
            continue
        if node.end is None:
            raise ValueError(f'data-ref="{ref_id}" element is missing its closing tag')
        if ref_id not in registry:
            raise ValueError(f'unknown data-ref target "{ref_id}"')
        replacements.append((node.start, node.end, numbered_ref_link(registry[ref_id], output_path, output_dir)))

    return replace_ranges(source, replacements)


def apply_numbered_items(
    source: str,
    registry: dict[str, dict[str, str]],
    output_path: Path,
    output_dir: Path,
) -> str:
    replacements: list[tuple[int, int, str]] = []

    for node in iter_nodes(parse_fragment(source)):
        element_id = node.attrs.get("id")
        if not element_id or element_id not in registry:
            continue
        replacement = numbered_caption_replacement(node, registry[element_id])
        if replacement is not None:
            replacements.append(replacement)

    source = replace_ranges(source, replacements)
    return replace_explicit_numbered_refs(source, registry, output_path, output_dir)
