"""Shared primitives for generated HTML text processing."""

from __future__ import annotations

import re

try:
    from html_fragment import iter_nodes, parse_fragment
except ModuleNotFoundError:
    from scripts.html_fragment import iter_nodes, parse_fragment

RAW_TEXT_INDENT_TAGS = {"pre", "code", "script", "style", "textarea"}


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
