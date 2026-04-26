#!/usr/bin/env python3
"""Lightweight checks for generated technical-document HTML.

This script intentionally uses only the Python standard library so it can be
copied into document projects without installing dependencies.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlparse


VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}

LOCAL_REF_ATTRS = {"href", "src"}
SKIP_REF_SCHEMES = {"http", "https", "mailto", "tel", "data", "javascript"}


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

    def error(self, line: int, column: int, message: str) -> None:
        self.issues.append(Issue("ERROR", self.path, line, column, message))

    def warn(self, line: int, column: int, message: str) -> None:
        self.issues.append(Issue("WARN", self.path, line, column, message))


def has_class(attrs: dict[str, str | None], class_name: str) -> bool:
    class_attr = attrs.get("class") or ""
    return class_name in class_attr.split()


def language_from_classes(class_attr: str | None) -> str | None:
    for class_name in (class_attr or "").split():
        if class_name.startswith("language-"):
            return class_name.removeprefix("language-")
    return None


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


def check_project_policy(root: Path) -> list[Issue]:
    return []

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
        default=["index.html", "templates/technical-doc-template.html", "templates/content-example.html"],
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
