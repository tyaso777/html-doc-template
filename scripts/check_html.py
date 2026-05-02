#!/usr/bin/env python3
"""Lightweight checks for generated technical-document HTML.

This script intentionally uses only the Python standard library so it can be
copied into document projects without installing dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlparse

try:
    from html_fragment import VOID_TAGS, has_class, language_from_classes
    from site_manifest import (
        forbidden_source_patterns,
        load_manifest,
        manifest_validation_errors,
        missing_shell_tokens,
        normalize_manifest,
    )
except ModuleNotFoundError:
    from scripts.html_fragment import VOID_TAGS, has_class, language_from_classes
    from scripts.site_manifest import (
        forbidden_source_patterns,
        load_manifest,
        manifest_validation_errors,
        missing_shell_tokens,
        normalize_manifest,
    )

LOCAL_REF_ATTRS = {"href", "src"}
SKIP_REF_SCHEMES = {"http", "https", "mailto", "tel", "data", "javascript"}
EXTERNAL_ASSET_SCHEMES = {"http", "https"}
LEGACY_PYTHON_RUNNER_IDS = {
    "copy-python-code-button",
    "load-button",
    "output",
    "print-python-code",
    "print-python-output",
    "pyodide-status",
    "python-code",
    "python-code-help",
    "reset-button",
    "restart-runtime-button",
    "run-button",
}


@dataclass(frozen=True)
class Issue:
    severity: str
    path: Path
    line: int
    column: int
    message: str


@dataclass
class Element:
    tag: str
    attrs: dict[str, str | None]
    line: int
    column: int


@dataclass
class LocalRef:
    attr: str
    value: str
    line: int
    column: int


@dataclass
class CodeBlock:
    line: int
    column: int
    pre_language: str | None
    code_count: int = 0
    code_languages: list[tuple[str | None, int, int]] | None = None

    def __post_init__(self) -> None:
        if self.code_languages is None:
            self.code_languages = []


class DocumentParser(HTMLParser):
    def __init__(self, path: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.path = path
        self.issues: list[Issue] = []
        self.ids: dict[str, tuple[int, int]] = {}
        self.local_refs: list[LocalRef] = []
        self.aria_refs: list[tuple[str, int, int]] = []
        self.stack: list[Element] = []
        self.open_code_blocks: list[CodeBlock] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = dict(attrs_list)
        line, column = self.getpos()
        element = Element(tag=tag, attrs=attrs, line=line, column=column)

        element_id = attrs.get("id")
        if element_id:
            if element_id in LEGACY_PYTHON_RUNNER_IDS:
                self.error(line, column, f'legacy Python runner id "{element_id}" should use scoped generated IDs')
            if element_id in self.ids:
                first_line, first_column = self.ids[element_id]
                self.error(
                    line,
                    column,
                    f'duplicate id "{element_id}"; first seen at {first_line}:{first_column}',
                )
            else:
                self.ids[element_id] = (line, column)

        if "data-toc" in attrs and not element_id:
            self.error(line, column, "data-toc element must have an id")

        toc_level = attrs.get("data-toc-level")
        if toc_level and not toc_level.isdigit():
            self.error(line, column, f'data-toc-level must be numeric, got "{toc_level}"')

        described_by = attrs.get("aria-describedby")
        if described_by:
            for ref_id in described_by.split():
                self.aria_refs.append((ref_id, line, column))

        for attr in LOCAL_REF_ATTRS:
            value = attrs.get(attr)
            if value and self.is_local_ref(value):
                self.local_refs.append(LocalRef(attr=attr, value=value, line=line, column=column))

        self.validate_external_asset_policy(tag, attrs, line, column)

        if tag == "pre" and has_class(attrs, "code-block"):
            self.open_code_blocks.append(
                CodeBlock(line=line, column=column, pre_language=language_from_classes(attrs.get("class")))
            )

        if tag == "code" and self.open_code_blocks:
            block = self.open_code_blocks[-1]
            block.code_count += 1
            block.code_languages.append((language_from_classes(attrs.get("class")), line, column))

        if tag not in VOID_TAGS:
            self.stack.append(element)

    def handle_endtag(self, tag: str) -> None:
        line, column = self.getpos()

        if tag == "pre" and self.open_code_blocks:
            self.validate_code_block(self.open_code_blocks.pop())

        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

        self.warn(line, column, f'unmatched closing tag </{tag}>')

    def close(self) -> None:
        super().close()

        for block in self.open_code_blocks:
            self.validate_code_block(block)

        for ref_id, line, column in self.aria_refs:
            if ref_id not in self.ids:
                self.error(line, column, f'aria-describedby references missing id "{ref_id}"')

        for ref in self.local_refs:
            self.validate_local_ref(ref)

    def validate_code_block(self, block: CodeBlock) -> None:
        if block.code_count == 0:
            self.error(block.line, block.column, "pre.code-block must contain a code element")
            return

        for code_language, line, column in block.code_languages:
            if block.pre_language and not code_language:
                self.error(line, column, f'code inside language-{block.pre_language} block must also declare language-{block.pre_language}')
            elif block.pre_language and code_language != block.pre_language:
                self.error(
                    line,
                    column,
                    f'pre/code language mismatch: pre is language-{block.pre_language}, code is language-{code_language}',
                )

    def validate_local_ref(self, ref: LocalRef) -> None:
        parsed = urlparse(ref.value)
        target_path = unquote(parsed.path)
        fragment = unquote(parsed.fragment)

        if not target_path and fragment:
            if fragment not in self.ids:
                self.error(ref.line, ref.column, f'{ref.attr} references missing fragment "#{fragment}"')
            return

        if not target_path:
            return

        target = (self.path.parent / target_path).resolve()
        if not target.exists():
            self.error(ref.line, ref.column, f'{ref.attr} references missing local file "{ref.value}"')

    def is_local_ref(self, value: str) -> bool:
        parsed = urlparse(value)
        if parsed.scheme.lower() in SKIP_REF_SCHEMES:
            return False
        if value.startswith("//"):
            return False
        return True

    def validate_external_asset_policy(self, tag: str, attrs: dict[str, str | None], line: int, column: int) -> None:
        asset_url = None

        if tag == "script":
            asset_url = attrs.get("src")
        elif tag == "link" and "stylesheet" in (attrs.get("rel") or "").lower().split():
            asset_url = attrs.get("href")

        if not asset_url:
            return

        parsed = urlparse(asset_url)
        if parsed.scheme.lower() not in EXTERNAL_ASSET_SCHEMES:
            return

        if not attrs.get("integrity"):
            self.error(line, column, f'external {tag} asset "{asset_url}" must declare integrity')

        if attrs.get("crossorigin") != "anonymous":
            self.error(line, column, f'external {tag} asset "{asset_url}" must declare crossorigin="anonymous"')

    def error(self, line: int, column: int, message: str) -> None:
        self.issues.append(Issue("ERROR", self.path, line, column, message))

    def warn(self, line: int, column: int, message: str) -> None:
        self.issues.append(Issue("WARN", self.path, line, column, message))


def check_file(path: Path) -> list[Issue]:
    parser = DocumentParser(path)
    try:
        parser.feed(path.read_text(encoding="utf-8"))
        parser.close()
    except UnicodeDecodeError as exc:
        return [Issue("ERROR", path, 1, 1, f"file is not valid UTF-8: {exc}")]
    except Exception as exc:  # HTMLParser is permissive, but keep failures visible.
        return [Issue("ERROR", path, 1, 1, f"could not parse file: {exc}")]
    return parser.issues



def check_site_manifest(root: Path, manifest_path: Path) -> list[Issue]:
    if not manifest_path.exists():
        return [Issue("ERROR", manifest_path, 1, 1, "site manifest file does not exist")]

    try:
        manifest_data = load_manifest(manifest_path)
    except json.JSONDecodeError as exc:
        return [Issue("ERROR", manifest_path, exc.lineno, exc.colno, f"invalid JSON: {exc.msg}")]

    manifest_dir = manifest_path.parent
    issues: list[Issue] = []
    manifest_errors = manifest_validation_errors(manifest_data)
    for message in manifest_errors:
        issues.append(Issue("ERROR", manifest_path, 1, 1, message))

    if manifest_errors:
        return issues

    manifest = normalize_manifest(manifest_data)

    shell_path = (manifest_dir / manifest.shell).resolve()
    if not shell_path.exists():
        issues.append(Issue("ERROR", manifest_path, 1, 1, f'shell references missing file "{manifest.shell}"'))
    else:
        shell_text = shell_path.read_text(encoding="utf-8")
        for token in missing_shell_tokens(shell_text):
            issues.append(Issue("ERROR", shell_path, 1, 1, f'shell is missing token "{token}"'))

    output_dir = (manifest_dir / manifest.output_dir).resolve()

    seen_hrefs: set[str] = set()

    for index, chapter in enumerate(manifest.chapters, start=1):
        href = chapter["href"]
        source = chapter["source"]

        source_path = (manifest_dir / source).resolve()
        if not source_path.exists():
            issues.append(Issue("ERROR", manifest_path, 1, 1, f'chapter source references missing file "{source}"'))
        else:
            source_text = source_path.read_text(encoding="utf-8")
            if "data-chapter-nav" not in source_text:
                issues.append(Issue("ERROR", source_path, 1, 1, "chapter source must contain a data-chapter-nav placeholder"))
            for pattern in forbidden_source_patterns(source_text):
                issues.append(Issue("ERROR", source_path, 1, 1, f"chapter source should be an article fragment and must not match {pattern.pattern}"))

        if href in seen_hrefs:
            issues.append(Issue("ERROR", manifest_path, 1, 1, f'duplicate chapter href "{href}"'))
        seen_hrefs.add(href)

        chapter_path = (output_dir / href).resolve()
        if not chapter_path.exists():
            issues.append(Issue("ERROR", manifest_path, 1, 1, f'chapter href references missing generated file "{href}"'))
            continue

        chapter_text = chapter_path.read_text(encoding="utf-8")
        if "data-chapter-nav" not in chapter_text:
            issues.append(Issue("ERROR", chapter_path, 1, 1, "generated chapter must contain a data-chapter-nav element"))

        if index > 1:
            previous_href = manifest.chapters[index - 2]["href"]
            expected_previous = Path(os.path.relpath((output_dir / previous_href).resolve(), chapter_path.parent)).as_posix()
            if expected_previous not in chapter_text:
                issues.append(Issue("ERROR", chapter_path, 1, 1, f'generated chapter is missing previous link "{expected_previous}"'))

        if index < len(manifest.chapters):
            next_href = manifest.chapters[index]["href"]
            expected_next = Path(os.path.relpath((output_dir / next_href).resolve(), chapter_path.parent)).as_posix()
            if expected_next not in chapter_text:
                issues.append(Issue("ERROR", chapter_path, 1, 1, f'generated chapter is missing next link "{expected_next}"'))

    return issues


def check_project_policy(root: Path) -> list[Issue]:
    return check_site_manifest(root, root / "chapters-src/site-manifest.json")

def existing_html_files(paths: Iterable[str], root: Path) -> list[Path]:
    result: list[Path] = []
    for raw_path in paths:
        path = (root / raw_path).resolve()
        if not path.exists():
            result.append(path)
            continue
        if path.is_dir():
            result.extend(sorted(path.rglob("*.html")))
        else:
            result.append(path)
    return result


def print_issues(issues: list[Issue]) -> None:
    for issue in issues:
        print(f"{issue.severity}: {issue.path}:{issue.line}:{issue.column}: {issue.message}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check generated technical-document HTML files.")
    parser.add_argument(
        "paths",
        nargs="*",
        default=["index.html", "chapters-src", "chapters"],
        help="HTML files or directories to check. Defaults to maintained project HTML files.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Project root used for default paths and project policy checks.",
    )
    parser.add_argument(
        "--no-project-policy",
        action="store_true",
        help="Skip checks that are specific to this template repository.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    paths = existing_html_files(args.paths, root)
    issues: list[Issue] = []

    for path in paths:
        if not path.exists():
            issues.append(Issue("ERROR", path, 1, 1, "file does not exist"))
            continue
        issues.extend(check_file(path))

    if not args.no_project_policy:
        issues.extend(check_project_policy(root))

    print_issues(issues)

    error_count = sum(1 for issue in issues if issue.severity == "ERROR")
    warn_count = sum(1 for issue in issues if issue.severity == "WARN")

    if not issues:
        print("OK: no issues found")
    else:
        print(f"Found {error_count} error(s), {warn_count} warning(s)")

    return 1 if error_count else 0


if __name__ == "__main__":
    sys.exit(main())
