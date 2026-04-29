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
    chapters: list[dict[str, str]]
    materials: list[Any]
    external_links: list[Any]


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_validation_errors(manifest: Any) -> list[str]:
    errors: list[str] = []

    if not isinstance(manifest, dict):
        return ["site manifest must be a JSON object"]

    shell = manifest.get("shell", "../layouts/chapter-shell.html")
    output_dir = manifest.get("outputDir", "../chapters")
    document_lang = manifest.get("lang", "en")
    materials = manifest.get("materials", [])
    external_links = manifest.get("externalLinks", [])
    chapters = manifest.get("chapters")

    if not isinstance(shell, str) or not shell.strip():
        errors.append("site manifest must have a non-empty shell path")
    if not isinstance(output_dir, str) or not output_dir.strip():
        errors.append("site manifest must have a non-empty outputDir")
    if not isinstance(document_lang, str) or not document_lang.strip():
        errors.append("site manifest lang must be a non-empty string")
    if not isinstance(materials, list):
        errors.append("site manifest materials must be an array when provided")
    if not isinstance(external_links, list):
        errors.append("site manifest externalLinks must be an array when provided")
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
        sidebar_title = chapter.get("sidebarTitle", title)
        subtitle = chapter.get("subtitle", "")

        if not isinstance(title, str) or not title.strip():
            errors.append(f"chapter {index} must have a non-empty title")
        if not isinstance(href, str) or not href.strip():
            errors.append(f"chapter {index} must have a non-empty href")
        if not isinstance(source, str) or not source.strip():
            errors.append(f"chapter {index} must have a non-empty source")
        if not isinstance(sidebar_title, str):
            errors.append(f"chapter {index} sidebarTitle must be a string")
        if not isinstance(subtitle, str):
            errors.append(f"chapter {index} subtitle must be a string")

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
    raw_chapters = manifest["chapters"]

    assert isinstance(shell, str)
    assert isinstance(output_dir, str)
    assert isinstance(document_lang, str)
    assert isinstance(materials, list)
    assert isinstance(external_links, list)
    assert isinstance(raw_chapters, list)

    chapters: list[dict[str, str]] = []
    for chapter in raw_chapters:
        assert isinstance(chapter, dict)
        title = chapter["title"]
        href = chapter["href"]
        source = chapter["source"]
        sidebar_title = chapter.get("sidebarTitle", title)
        subtitle = chapter.get("subtitle", "")
        assert isinstance(title, str)
        assert isinstance(href, str)
        assert isinstance(source, str)
        assert isinstance(sidebar_title, str)
        assert isinstance(subtitle, str)
        chapters.append(
            {
                "title": title,
                "href": href,
                "source": source,
                "sidebarTitle": sidebar_title,
                "subtitle": subtitle,
            }
        )

    return SiteManifest(
        shell=shell,
        output_dir=output_dir,
        document_lang=document_lang,
        chapters=chapters,
        materials=materials,
        external_links=external_links,
    )


def missing_shell_tokens(shell_text: str) -> list[str]:
    return sorted(token for token in REQUIRED_SHELL_TOKENS if token not in shell_text)


def forbidden_source_patterns(source_text: str) -> list[Pattern[str]]:
    return [pattern for pattern in SOURCE_FRAGMENT_FORBIDDEN_PATTERNS if pattern.search(source_text)]
