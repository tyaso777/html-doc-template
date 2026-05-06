"""Shared site manifest and chapter-source validation helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Pattern

REQUIRED_SHELL_TOKENS = {
    "{{DOCUMENT_LANG}}",
    "{{DOCUMENT_TITLE}}",
    "{{SIDEBAR_TITLE}}",
    "{{SIDEBAR_SUBTITLE}}",
    "{{ASSET_PREFIX}}",
    "{{CONTENT}}",
    "{{CONTENTS_TREE}}",
    "{{MATERIALS_SECTION}}",
    "{{EXTERNAL_LINKS_SECTION}}",
}
SOURCE_FRAGMENT_FORBIDDEN_PATTERNS = (
    re.compile(r"<!doctype", re.I),
    re.compile(r"<html(?:\s|>)", re.I),
    re.compile(r"<head(?:\s|>)", re.I),
    re.compile(r"<body(?:\s|>)", re.I),
    re.compile(r"<script(?:\s|>)", re.I),
    re.compile(r"<link(?:\s|>)", re.I),
)


@dataclass(frozen=True)
class SiteManifest:
    shell: str
    output_dir: str
    document_lang: str
    chapters: list[dict[str, Any]]
    materials: list[Any]
    external_links: list[Any]
    heading_numbering: dict[str, Any]
    numbering: dict[str, Any]


HEADING_NUMBERING_TITLE_MODES = {"numbered", "plain"}
NUMBERING_SECTIONS = ("figures", "tables", "equations")
NUMBERING_RESETS = {"chapter", "document"}


def link_tree_validation_errors(items: Any, path: str) -> list[str]:
    errors: list[str] = []

    if not isinstance(items, list):
        return [f"{path} must be an array when provided"]

    for index, item in enumerate(items, start=1):
        item_path = f"{path} item {index}"
        if not isinstance(item, dict):
            errors.append(f"{item_path} must be an object")
            continue

        title = item.get("title")
        nested_items = item.get("items")
        label = item.get("label")
        href = item.get("href")

        if "items" in item or "title" in item:
            if not isinstance(title, str) or not title.strip():
                errors.append(f"{item_path} group must have a non-empty title")
            if not isinstance(nested_items, list):
                errors.append(f"{item_path} group items must be an array")
            else:
                errors.extend(link_tree_validation_errors(nested_items, f"{item_path} group items"))
            continue

        if not isinstance(label, str) or not label.strip():
            errors.append(f"{item_path} link must have a non-empty label")
        if not isinstance(href, str) or not href.strip():
            errors.append(f"{item_path} link must have a non-empty href")

    return errors


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def heading_numbering_validation_errors(config: Any) -> list[str]:
    errors: list[str] = []

    if config is None:
        return errors
    if not isinstance(config, dict):
        return ["site manifest headingNumbering must be an object when provided"]

    enabled = config.get("enabled", False)
    levels = config.get("levels", [])
    body = config.get("body", True)
    toc = config.get("toc", True)
    default_format = config.get("format", "{number}. {title}")
    level_formats = config.get("levelFormats", {})
    toc_title_mode = config.get("tocTitleMode", "numbered")

    if not isinstance(enabled, bool):
        errors.append("site manifest headingNumbering enabled must be a boolean")
    if not isinstance(body, bool):
        errors.append("site manifest headingNumbering body must be a boolean")
    if not isinstance(toc, bool):
        errors.append("site manifest headingNumbering toc must be a boolean")
    if not isinstance(default_format, str) or "{title}" not in default_format:
        errors.append('site manifest headingNumbering format must be a string containing "{title}"')
    if not isinstance(levels, list) or not all(isinstance(level, int) and 2 <= level <= 6 for level in levels):
        errors.append("site manifest headingNumbering levels must be an array of integers from 2 to 6")
    if not isinstance(level_formats, dict):
        errors.append("site manifest headingNumbering levelFormats must be an object")
    else:
        for raw_level, format_text in level_formats.items():
            if str(raw_level) not in {"2", "3", "4", "5", "6"}:
                errors.append("site manifest headingNumbering levelFormats keys must be heading levels 2 through 6")
            if not isinstance(format_text, str) or "{title}" not in format_text:
                errors.append(f'site manifest headingNumbering levelFormats {raw_level} must be a string containing "{{title}}"')
    if toc_title_mode not in HEADING_NUMBERING_TITLE_MODES:
        errors.append('site manifest headingNumbering tocTitleMode must be "numbered" or "plain"')

    return errors


def normalize_heading_numbering(config: Any) -> dict[str, Any]:
    if config is None:
        config = {}

    assert isinstance(config, dict)
    enabled = config.get("enabled", False)
    levels = config.get("levels", [])
    body = config.get("body", True)
    toc = config.get("toc", True)
    default_format = config.get("format", "{number}. {title}")
    level_formats = config.get("levelFormats", {})
    toc_title_mode = config.get("tocTitleMode", "numbered")

    assert isinstance(enabled, bool)
    assert isinstance(levels, list)
    assert isinstance(body, bool)
    assert isinstance(toc, bool)
    assert isinstance(default_format, str)
    assert isinstance(level_formats, dict)
    assert isinstance(toc_title_mode, str)

    return {
        "enabled": enabled,
        "levels": levels,
        "body": body,
        "toc": toc,
        "format": default_format,
        "levelFormats": level_formats,
        "tocTitleMode": toc_title_mode,
    }


def numbering_validation_errors(config: Any) -> list[str]:
    errors: list[str] = []

    if config is None:
        return errors
    if not isinstance(config, dict):
        return ["site manifest numbering must be an object when provided"]

    for section in NUMBERING_SECTIONS:
        section_config = config.get(section, {})
        if not isinstance(section_config, dict):
            errors.append(f"site manifest numbering {section} must be an object when provided")
            continue

        enabled = section_config.get("enabled", False)
        format_text = section_config.get("format", "{index}")
        reset = section_config.get("reset", "chapter")

        if not isinstance(enabled, bool):
            errors.append(f"site manifest numbering {section} enabled must be a boolean")
        if not isinstance(format_text, str) or "{index}" not in format_text:
            errors.append(f'site manifest numbering {section} format must be a string containing "{{index}}"')
        if reset not in NUMBERING_RESETS:
            errors.append(f'site manifest numbering {section} reset must be "chapter" or "document"')

    return errors


def normalize_numbering(config: Any) -> dict[str, Any]:
    if config is None:
        config = {}

    assert isinstance(config, dict)
    normalized: dict[str, Any] = {}
    for section in NUMBERING_SECTIONS:
        section_config = config.get(section, {})
        assert isinstance(section_config, dict)
        enabled = section_config.get("enabled", False)
        format_text = section_config.get("format", "{index}")
        reset = section_config.get("reset", "chapter")
        assert isinstance(enabled, bool)
        assert isinstance(format_text, str)
        assert isinstance(reset, str)
        normalized[section] = {
            "enabled": enabled,
            "format": format_text,
            "reset": reset,
        }

    return normalized


def manifest_validation_errors(manifest: Any) -> list[str]:
    errors: list[str] = []

    if not isinstance(manifest, dict):
        return ["site manifest must be a JSON object"]

    shell = manifest.get("shell", "../layouts/chapter-shell.html")
    output_dir = manifest.get("outputDir", "../chapters")
    document_lang = manifest.get("lang", "en")
    materials = manifest.get("materials", [])
    external_links = manifest.get("externalLinks", [])
    heading_numbering = manifest.get("headingNumbering", {})
    numbering = manifest.get("numbering", {})
    chapters = manifest.get("chapters")

    if not isinstance(shell, str) or not shell.strip():
        errors.append("site manifest must have a non-empty shell path")
    if not isinstance(output_dir, str) or not output_dir.strip():
        errors.append("site manifest must have a non-empty outputDir")
    if not isinstance(document_lang, str) or not document_lang.strip():
        errors.append("site manifest lang must be a non-empty string")
    errors.extend(link_tree_validation_errors(materials, "site manifest materials"))
    errors.extend(link_tree_validation_errors(external_links, "site manifest externalLinks"))
    errors.extend(heading_numbering_validation_errors(heading_numbering))
    errors.extend(numbering_validation_errors(numbering))
    if not isinstance(chapters, list):
        errors.append("site manifest must contain a chapters array")
        return errors

    for index, chapter in enumerate(chapters, start=1):
        if not isinstance(chapter, dict):
            errors.append(f"chapter {index} must be an object")
            continue

        title = chapter.get("title")
        href = chapter.get("href")
        source = chapter.get("source")
        chapter_number = chapter.get("number", index)
        sidebar_title = chapter.get("sidebarTitle", title)
        subtitle = chapter.get("subtitle", "")
        chapter_external_links = chapter.get("externalLinks", [])

        if not isinstance(title, str) or not title.strip():
            errors.append(f"chapter {index} must have a non-empty title")
        if not isinstance(href, str) or not href.strip():
            errors.append(f"chapter {index} must have a non-empty href")
        if not isinstance(source, str) or not source.strip():
            errors.append(f"chapter {index} must have a non-empty source")
        if not isinstance(chapter_number, (int, str)) or (isinstance(chapter_number, str) and not chapter_number.strip()):
            errors.append(f"chapter {index} number must be a non-empty string or integer")
        if not isinstance(sidebar_title, str):
            errors.append(f"chapter {index} sidebarTitle must be a string")
        if not isinstance(subtitle, str):
            errors.append(f"chapter {index} subtitle must be a string")
        errors.extend(link_tree_validation_errors(chapter_external_links, f"chapter {index} externalLinks"))

    return errors


def normalize_manifest(manifest: Any) -> SiteManifest:
    errors = manifest_validation_errors(manifest)
    if errors:
        raise ValueError("; ".join(errors))

    assert isinstance(manifest, dict)
    shell = manifest.get("shell", "../layouts/chapter-shell.html")
    output_dir = manifest.get("outputDir", "../chapters")
    document_lang = manifest.get("lang", "en")
    materials = manifest.get("materials", [])
    external_links = manifest.get("externalLinks", [])
    heading_numbering = normalize_heading_numbering(manifest.get("headingNumbering", {}))
    numbering = normalize_numbering(manifest.get("numbering", {}))
    raw_chapters = manifest["chapters"]

    assert isinstance(shell, str)
    assert isinstance(output_dir, str)
    assert isinstance(document_lang, str)
    assert isinstance(materials, list)
    assert isinstance(external_links, list)
    assert isinstance(raw_chapters, list)

    chapters: list[dict[str, Any]] = []
    for chapter in raw_chapters:
        assert isinstance(chapter, dict)
        title = chapter["title"]
        href = chapter["href"]
        source = chapter["source"]
        chapter_number = chapter.get("number", len(chapters) + 1)
        sidebar_title = chapter.get("sidebarTitle", title)
        subtitle = chapter.get("subtitle", "")
        chapter_external_links = chapter.get("externalLinks", [])
        assert isinstance(title, str)
        assert isinstance(href, str)
        assert isinstance(source, str)
        assert isinstance(chapter_number, (int, str))
        assert isinstance(sidebar_title, str)
        assert isinstance(subtitle, str)
        assert isinstance(chapter_external_links, list)
        chapters.append(
            {
                "title": title,
                "href": href,
                "source": source,
                "number": str(chapter_number),
                "sidebarTitle": sidebar_title,
                "subtitle": subtitle,
                "externalLinks": chapter_external_links,
            }
        )

    return SiteManifest(
        shell=shell,
        output_dir=output_dir,
        document_lang=document_lang,
        chapters=chapters,
        materials=materials,
        external_links=external_links,
        heading_numbering=heading_numbering,
        numbering=numbering,
    )


def missing_shell_tokens(shell_text: str) -> list[str]:
    return sorted(token for token in REQUIRED_SHELL_TOKENS if token not in shell_text)


def forbidden_source_patterns(source_text: str) -> list[Pattern[str]]:
    return [pattern for pattern in SOURCE_FRAGMENT_FORBIDDEN_PATTERNS if pattern.search(source_text)]
