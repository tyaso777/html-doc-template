#!/usr/bin/env python3
"""Build generated chapter HTML from source fragments and chapters-src/site-manifest.json.

Editable chapter bodies and the manifest live under chapters-src/. This script
combines each source fragment with layouts/chapter-shell.html, injects
Previous/Next navigation from the manifest order, and writes complete public
HTML files under chapters/.
"""

from __future__ import annotations

import argparse
import html
import os
import re
from pathlib import Path
from typing import Any

try:
    from html_fragment import (
        FragmentNode,
        iter_nodes,
        node_inner_html,
        parse_fragment,
        replace_ranges,
        text_content,
    )
    from site_manifest import (
        forbidden_source_patterns,
        load_manifest,
        missing_shell_tokens,
        normalize_manifest,
    )
    from site_builder.link_sections import chapter_external_links, render_link_section
    from site_builder.navigation import relative_path, render_chapter_nav, render_contents_tree
    from site_builder.python_runner import expand_python_runners
except ModuleNotFoundError:
    from scripts.html_fragment import (
        FragmentNode,
        iter_nodes,
        node_inner_html,
        parse_fragment,
        replace_ranges,
        text_content,
    )
    from scripts.site_manifest import (
        forbidden_source_patterns,
        load_manifest,
        missing_shell_tokens,
        normalize_manifest,
    )
    from scripts.site_builder.link_sections import chapter_external_links, render_link_section
    from scripts.site_builder.navigation import relative_path, render_chapter_nav, render_contents_tree
    from scripts.site_builder.python_runner import expand_python_runners


def asset_prefix(output_path: Path, root: Path) -> str:
    relative = Path(os.path.relpath(root.resolve(), output_path.resolve().parent)).as_posix()
    return "" if relative == "." else relative.rstrip("/") + "/"


def sidebar_title_html(title: str) -> str:
    return "<br>".join(html.escape(part.strip()) for part in title.splitlines() if part.strip())


RAW_TEXT_INDENT_TAGS = {"pre", "code", "script", "style", "textarea"}
HEADING_TAG_PATTERN = re.compile(r"h[2-6]")
HEADING_NUMBER_TOKENS = re.compile(r"(\{title\}|\{number\}|\{local\})")
NUMBERED_KIND_TO_SECTION = {"figure": "figures", "table": "tables", "equation": "equations"}
NUMBERED_KIND_TO_CLASS = {"figure": "figure-number", "table": "table-number", "equation": "equation-number"}
NUMBERED_SHORTHAND_PREFIX = {"図": "figure", "表": "table", "式": "equation"}
NUMBERED_REF_PATTERN = re.compile(r"(?<![\w.-])(?P<prefix>図|表|式)\((?P<id>[A-Za-z][A-Za-z0-9_.:-]*)\)")
SECTION_REF_PATTERN = re.compile(r"(?<![\w.-])(?:節|参照)\((?P<id>[A-Za-z][A-Za-z0-9_.:-]*)\)")


def indent_content_preserving_raw_text(content: str, indent: str) -> str:
    protected_ranges: list[tuple[int, int]] = []

    for node in iter_nodes(parse_fragment(content)):
        if node.tag in RAW_TEXT_INDENT_TAGS and node.end_tag_start is not None:
            protected_ranges.append((node.start_tag_end, node.end_tag_start))

    protected_ranges.sort()
    protected_index = 0
    rendered_lines: list[str] = []
    line_start = 0

    for line in content.splitlines(keepends=True):
        while protected_index < len(protected_ranges) and protected_ranges[protected_index][1] <= line_start:
            protected_index += 1

        in_protected_range = (
            protected_index < len(protected_ranges)
            and protected_ranges[protected_index][0] <= line_start < protected_ranges[protected_index][1]
        )
        rendered_lines.append(line if in_protected_range or not line.strip() else indent + line)
        line_start += len(line)

    return "".join(rendered_lines)


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


def numbered_caption_replacement(source: str, node: FragmentNode, item: dict[str, str]) -> tuple[int, int, str] | None:
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


def replace_explicit_numbered_refs(source: str, registry: dict[str, dict[str, str]], output_path: Path, output_dir: Path) -> str:
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


def protected_text_ranges(source: str) -> list[tuple[int, int]]:
    ranges = [(match.start(), match.end()) for match in re.finditer(r"<[^>]+>", source)]
    for node in iter_nodes(parse_fragment(source)):
        if node.tag in RAW_TEXT_INDENT_TAGS and node.end_tag_start is not None:
            ranges.append((node.start_tag_end, node.end_tag_start))

    merged: list[tuple[int, int]] = []
    for start, end in sorted(ranges):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            previous_start, previous_end = merged[-1]
            merged[-1] = (previous_start, max(previous_end, end))
    return merged


def replace_numbered_shorthand_refs(source: str, registry: dict[str, dict[str, str]], output_path: Path, output_dir: Path) -> str:
    ranges = protected_text_ranges(source)
    rendered: list[str] = []
    position = 0

    def replace_match(match: re.Match[str]) -> str:
        ref_id = match.group("id")
        expected_kind = NUMBERED_SHORTHAND_PREFIX[match.group("prefix")]
        if ref_id not in registry:
            raise ValueError(f'unknown numbered shorthand reference target "{ref_id}"')
        item = registry[ref_id]
        if item["kind"] != expected_kind:
            raise ValueError(f'numbered shorthand reference "{match.group(0)}" points to {item["kind"]}, not {expected_kind}')
        return numbered_ref_link(item, output_path, output_dir)

    for start, end in ranges:
        if position < start:
            rendered.append(NUMBERED_REF_PATTERN.sub(replace_match, source[position:start]))
        rendered.append(source[start:end])
        position = end

    rendered.append(NUMBERED_REF_PATTERN.sub(replace_match, source[position:]))
    return "".join(rendered)


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
        replacement = numbered_caption_replacement(source, node, registry[element_id])
        if replacement is not None:
            replacements.append(replacement)

    source = replace_ranges(source, replacements)
    source = replace_explicit_numbered_refs(source, registry, output_path, output_dir)
    return replace_numbered_shorthand_refs(source, registry, output_path, output_dir)


def heading_level(node: FragmentNode) -> int:
    raw_level = node.attrs.get("data-toc-level")
    if raw_level and raw_level.isdigit():
        return int(raw_level)
    if node.tag.startswith("h") and node.tag[1:].isdigit():
        return int(node.tag[1:])
    return 2


def heading_number_format(config: dict[str, Any], level: int) -> str:
    level_formats = config.get("levelFormats", {})
    if isinstance(level_formats, dict):
        format_text = level_formats.get(str(level))
        if isinstance(format_text, str):
            return format_text
    format_text = config.get("format", "{number}. {title}")
    return format_text if isinstance(format_text, str) else "{number}. {title}"


def format_numbered_heading_html(format_text: str, number: str, local: str, title_html: str) -> str:
    parts: list[str] = []
    for token in HEADING_NUMBER_TOKENS.split(format_text):
        if token == "{title}":
            parts.append(title_html)
        elif token == "{number}":
            parts.append(html.escape(number))
        elif token == "{local}":
            parts.append(html.escape(local))
        else:
            parts.append(html.escape(token))
    return "".join(parts)


def format_numbered_heading_text(format_text: str, number: str, local: str, title: str) -> str:
    return format_text.replace("{number}", number).replace("{local}", local).replace("{title}", title)


def first_heading_child(node: FragmentNode) -> FragmentNode | None:
    return next((child for child in node.children if HEADING_TAG_PATTERN.fullmatch(child.tag)), None)


def section_toc_level(section: FragmentNode, heading: FragmentNode) -> int:
    raw_level = section.attrs.get("data-toc-level")
    if raw_level and raw_level.isdigit():
        return int(raw_level)
    return heading_level(heading)


def heading_numbering_targets(source: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    if not config.get("enabled", False):
        return []

    roots = parse_fragment(source)
    nodes = iter_nodes(roots)
    levels = set(config.get("levels", []))
    section_targets: dict[int, tuple[str, int]] = {}

    for node in nodes:
        if node.tag != "section" or "data-toc" not in node.attrs:
            continue
        element_id = node.attrs.get("id")
        heading = first_heading_child(node)
        if element_id and heading is not None:
            section_targets[heading.start] = (element_id, section_toc_level(node, heading))

    targets: list[dict[str, Any]] = []
    seen: set[int] = set()
    for node in nodes:
        if not HEADING_TAG_PATTERN.fullmatch(node.tag):
            continue

        target_id: str | None = None
        level = heading_level(node)
        if node.start in section_targets:
            target_id, level = section_targets[node.start]
        elif "data-toc" in node.attrs and isinstance(node.attrs.get("id"), str):
            target_id = node.attrs["id"]

        if node.start in section_targets or "data-toc" in node.attrs or level in levels:
            if node.start in seen:
                continue
            targets.append({"node": node, "id": target_id, "level": level})
            seen.add(node.start)

    return targets


def apply_heading_numbering(source: str, config: dict[str, Any]) -> tuple[str, dict[str, dict[str, str]]]:
    targets = heading_numbering_targets(source, config)
    if not targets:
        return source, {}

    counters = {level: 0 for level in range(2, 7)}
    replacements: list[tuple[int, int, str]] = []
    numbering_by_id: dict[str, dict[str, str]] = {}

    for target in targets:
        node = target["node"]
        assert isinstance(node, FragmentNode)
        level = int(target["level"])
        counters[level] += 1
        for deeper_level in range(level + 1, 7):
            counters[deeper_level] = 0
        for parent_level in range(2, level):
            if counters[parent_level] == 0:
                counters[parent_level] = 1

        parts = [str(counters[number_level]) for number_level in range(2, level + 1)]
        number = ".".join(parts)
        local = str(counters[level])
        format_text = heading_number_format(config, level)
        title_html = node_inner_html(source, node)
        title_text = text_content(source, node)

        target_id = target.get("id")
        if isinstance(target_id, str):
            numbering_by_id[target_id] = {
                "format": format_text,
                "number": number,
                "local": local,
                "title": title_text,
                "level": str(level),
            }

        if config.get("body", True) and node.end_tag_start is not None:
            replacements.append(
                (
                    node.start_tag_end,
                    node.end_tag_start,
                    format_numbered_heading_html(format_text, number, local, title_html),
                )
            )

    return replace_ranges(source, replacements), numbering_by_id


def collect_section_refs(
    chapter_sources: list[str],
    chapters: list[dict[str, Any]],
    heading_numbering: dict[str, Any],
) -> dict[str, list[dict[str, str]]]:
    if not heading_numbering.get("enabled", False):
        return {}

    registry: dict[str, list[dict[str, str]]] = {}
    for index, source in enumerate(chapter_sources):
        _, numbering_by_id = apply_heading_numbering(source, heading_numbering)
        chapter = chapters[index]
        for element_id, numbering in numbering_by_id.items():
            registry.setdefault(element_id, []).append({
                "id": element_id,
                "number": numbering["number"],
                "local": numbering["local"],
                "title": numbering["title"],
                "level": numbering["level"],
                "chapterHref": str(chapter["href"]),
                "source": str(chapter["source"]),
            })
    return registry


def section_ref_label(item: dict[str, str], heading_numbering: dict[str, Any]) -> str:
    format_text = heading_numbering.get("referenceFormat", "{number}")
    reference_level_formats = heading_numbering.get("referenceLevelFormats", {})
    if isinstance(reference_level_formats, dict):
        level_format = reference_level_formats.get(item["level"])
        if isinstance(level_format, str):
            format_text = level_format
    if not isinstance(format_text, str):
        format_text = "{number}"
    return (
        format_text
        .replace("{number}", item["number"])
        .replace("{local}", item["local"])
        .replace("{title}", item["title"])
    )


def section_ref_href(item: dict[str, str], output_path: Path, output_dir: Path) -> str:
    target_path = output_dir / item["chapterHref"]
    return f"{relative_path(output_path, target_path)}#{item['id']}"


def section_ref_link(
    item: dict[str, str],
    output_path: Path,
    output_dir: Path,
    heading_numbering: dict[str, Any],
) -> str:
    href = html.escape(section_ref_href(item, output_path, output_dir), quote=True)
    label = html.escape(section_ref_label(item, heading_numbering))
    return f'<a class="xref section-ref" href="{href}">{label}</a>'


def resolve_section_ref(
    registry: dict[str, list[dict[str, str]]],
    ref_id: str,
    output_path: Path,
    output_dir: Path,
    source_label: str,
) -> dict[str, str]:
    matches = registry.get(ref_id, [])
    if not matches:
        raise ValueError(f'unknown {source_label} target "{ref_id}"')
    if len(matches) == 1:
        return matches[0]

    current_href = Path(os.path.relpath(output_path.resolve(), output_dir.resolve())).as_posix()
    current_matches = [item for item in matches if item["chapterHref"] == current_href]
    if len(current_matches) == 1:
        return current_matches[0]

    targets = ", ".join(f'{item["chapterHref"]}#{item["id"]}' for item in matches)
    raise ValueError(f'ambiguous {source_label} target "{ref_id}" matches {targets}')


def replace_explicit_section_refs(
    source: str,
    registry: dict[str, list[dict[str, str]]],
    output_path: Path,
    output_dir: Path,
    heading_numbering: dict[str, Any],
) -> str:
    replacements: list[tuple[int, int, str]] = []
    for node in iter_nodes(parse_fragment(source)):
        for attr_name in ("data-heading-ref", "data-section-ref"):
            ref_id = node.attrs.get(attr_name)
            if ref_id is None:
                continue
            if node.end is None:
                raise ValueError(f'{attr_name}="{ref_id}" element is missing its closing tag')
            item = resolve_section_ref(registry, ref_id, output_path, output_dir, attr_name)
            replacements.append((node.start, node.end, section_ref_link(item, output_path, output_dir, heading_numbering)))
            break

    return replace_ranges(source, replacements)


def replace_section_shorthand_refs(
    source: str,
    registry: dict[str, list[dict[str, str]]],
    output_path: Path,
    output_dir: Path,
    heading_numbering: dict[str, Any],
) -> str:
    ranges = protected_text_ranges(source)
    rendered: list[str] = []
    position = 0

    def replace_match(match: re.Match[str]) -> str:
        ref_id = match.group("id")
        item = resolve_section_ref(registry, ref_id, output_path, output_dir, "section shorthand reference")
        return section_ref_link(item, output_path, output_dir, heading_numbering)

    for start, end in ranges:
        if position < start:
            rendered.append(SECTION_REF_PATTERN.sub(replace_match, source[position:start]))
        rendered.append(source[start:end])
        position = end

    rendered.append(SECTION_REF_PATTERN.sub(replace_match, source[position:]))
    return "".join(rendered)


def apply_section_refs(
    source: str,
    registry: dict[str, list[dict[str, str]]],
    output_path: Path,
    output_dir: Path,
    heading_numbering: dict[str, Any],
) -> str:
    source = replace_explicit_section_refs(source, registry, output_path, output_dir, heading_numbering)
    return replace_section_shorthand_refs(source, registry, output_path, output_dir, heading_numbering)


def extract_toc_entries(
    source: str,
    numbering_by_id: dict[str, dict[str, str]] | None = None,
    heading_numbering: dict[str, Any] | None = None,
) -> list[dict[str, str | int]]:
    entries: list[dict[str, str | int]] = []
    numbering_by_id = numbering_by_id or {}
    heading_numbering = heading_numbering or {}
    use_numbered_toc = heading_numbering.get("enabled", False) and heading_numbering.get("toc", True)
    toc_title_mode = heading_numbering.get("tocTitleMode", "numbered")

    for node in iter_nodes(parse_fragment(source)):
        if node.tag != "section" and not HEADING_TAG_PATTERN.fullmatch(node.tag):
            continue

        attrs = node.attrs
        if "data-toc" not in attrs or "id" not in attrs:
            continue

        element_id = attrs.get("id")
        if not element_id or element_id == "...":
            continue

        title = attrs.get("data-toc-title")
        if not title and node.tag == "section":
            headings = [
                child
                for child in node.children
                if child.tag in {"h2", "h3", "h4", "h5", "h6"}
            ]
            title = numbering_by_id[element_id]["title"] if element_id in numbering_by_id else text_content(source, headings[0]) if headings else None
        if not title:
            title = numbering_by_id[element_id]["title"] if element_id in numbering_by_id else text_content(source, node) if node.tag.startswith("h") else element_id

        if use_numbered_toc and toc_title_mode == "numbered" and element_id in numbering_by_id:
            numbering = numbering_by_id[element_id]
            title = format_numbered_heading_text(numbering["format"], numbering["number"], numbering["local"], title)

        level = heading_level(node)
        entries.append({"id": element_id, "title": title, "level": level})

    return entries


def inject_chapter_nav(source: str, chapters: list[dict[str, Any]], index: int, output_path: Path, output_dir: Path) -> str:
    matches = [
        node
        for node in iter_nodes(parse_fragment(source))
        if node.tag == "nav" and "data-chapter-nav" in node.attrs
    ]

    if len(matches) != 1:
        raise ValueError(f'{chapters[index]["source"]} must contain exactly one data-chapter-nav element')

    match = matches[0]
    if match.end is None:
        raise ValueError(f'{chapters[index]["source"]} data-chapter-nav element is missing its closing tag')

    line_start = source.rfind("\n", 0, match.start) + 1
    indent = source[line_start:match.start]
    nav = render_chapter_nav(chapters, index, output_path, output_dir, indent)
    return replace_ranges(source, [(match.start, match.end, nav)])


def validate_source_fragment(source_path: Path, text: str) -> None:
    for pattern in forbidden_source_patterns(text):
        raise ValueError(f"{source_path} should be an article fragment and must not match {pattern.pattern}")



def render_shell(
    shell: str,
    chapter: dict[str, Any],
    content: str,
    output_path: Path,
    root: Path,
    manifest_dir: Path,
    document_lang: str,
    chapters: list[dict[str, Any]],
    current_index: int,
    output_dir: Path,
    toc_entries_by_chapter: list[list[dict[str, str | int]]],
    materials: list[Any],
    external_links: list[Any],
    heading_numbering: dict[str, Any] | None = None,
) -> str:
    numbered_toc = bool((heading_numbering or {}).get("enabled", False) and (heading_numbering or {}).get("toc", True))
    replacements = {
        "{{DOCUMENT_LANG}}": html.escape(document_lang, quote=True),
        "{{DOCUMENT_TITLE}}": html.escape(chapter["title"]),
        "{{SIDEBAR_TITLE}}": sidebar_title_html(chapter.get("sidebarTitle", chapter["title"])),
        "{{SIDEBAR_SUBTITLE}}": html.escape(chapter.get("subtitle", "")),
        "{{ASSET_PREFIX}}": asset_prefix(output_path, root),
        "{{CONTENTS_TREE}}": render_contents_tree(
            chapters,
            current_index,
            output_path,
            output_dir,
            toc_entries_by_chapter,
            numbered_toc=numbered_toc,
        ),
        "{{MATERIALS_SECTION}}": render_link_section("Materials", materials, manifest_dir, output_path),
        "{{EXTERNAL_LINKS_SECTION}}": render_link_section(
            "External Links",
            chapter_external_links(external_links, chapter),
            manifest_dir,
            output_path,
            external_section=True,
        ),
        "{{CONTENT}}": indent_content_preserving_raw_text(content.rstrip(), "        "),
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
    chapters: list[dict[str, Any]],
    chapter_sources: list[str],
    index: int,
    toc_entries_by_chapter: list[list[dict[str, str | int]]],
    document_lang: str,
    materials: list[Any],
    external_links: list[Any],
    heading_numbering: dict[str, Any],
    numbered_items: dict[str, dict[str, str]],
    section_refs: dict[str, list[dict[str, str]]],
) -> Path:
    chapter = chapters[index]
    source_path = manifest_dir / chapter["source"]
    output_path = output_dir / chapter["href"]

    source = chapter_sources[index]
    validate_source_fragment(source_path, source)
    source = apply_numbered_items(source, numbered_items, output_path, output_dir)
    source, _ = apply_heading_numbering(source, heading_numbering)
    source = apply_section_refs(source, section_refs, output_path, output_dir, heading_numbering)
    source = expand_python_runners(source)
    content = inject_chapter_nav(source, chapters, index, output_path, output_dir)
    text = render_shell(
        shell,
        chapter,
        content,
        output_path,
        root,
        manifest_dir,
        document_lang,
        chapters,
        index,
        output_dir,
        toc_entries_by_chapter,
        materials,
        external_links,
        heading_numbering,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return output_path


def validate_shell(shell: str, shell_path: Path) -> None:
    missing = missing_shell_tokens(shell)
    if missing:
        raise ValueError(f"{shell_path} is missing required token(s): {', '.join(missing)}")


def display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def build_site(root: Path, manifest_path: Path, output_dir_override: Path | None = None) -> list[Path]:
    manifest_dir = manifest_path.parent
    manifest = normalize_manifest(load_manifest(manifest_path))
    shell_path = (manifest_dir / manifest.shell).resolve()
    output_dir = output_dir_override.resolve() if output_dir_override is not None else (manifest_dir / manifest.output_dir).resolve()
    shell = shell_path.read_text(encoding="utf-8")
    validate_shell(shell, shell_path)
    chapter_sources = [
        (manifest_dir / chapter["source"]).read_text(encoding="utf-8")
        for chapter in manifest.chapters
    ]
    numbered_items = collect_numbered_items(chapter_sources, manifest.chapters, manifest.numbering)
    section_refs = collect_section_refs(chapter_sources, manifest.chapters, manifest.heading_numbering)

    toc_entries_by_chapter = [
        extract_toc_entries(
            *apply_heading_numbering(chapter_sources[index], manifest.heading_numbering),
            manifest.heading_numbering,
        )
        for index, chapter in enumerate(manifest.chapters)
    ]

    output_paths: list[Path] = []
    for index in range(len(manifest.chapters)):
        output_paths.append(
            build_chapter(
                root,
                manifest_dir,
                output_dir,
                shell,
                manifest.chapters,
                chapter_sources,
                index,
                toc_entries_by_chapter,
                manifest.document_lang,
                manifest.materials,
                manifest.external_links,
                manifest.heading_numbering,
                numbered_items,
                section_refs,
            )
        )

    return output_paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build generated chapter HTML from source fragments and chapters-src/site-manifest.json.")
    parser.add_argument("--root", default=".", help="Project root.")
    parser.add_argument("--manifest", default="chapters-src/site-manifest.json", help="Manifest path relative to root.")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override the manifest outputDir. Relative paths are resolved from root.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    manifest_path = (root / args.manifest).resolve()
    output_dir_override = (root / args.output_dir).resolve() if args.output_dir else None

    for output_path in build_site(root, manifest_path, output_dir_override):
        print(f"built {display_path(output_path, root)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
