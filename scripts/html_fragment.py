"""Shared helpers for parsing small HTML document fragments.

The build and check scripts intentionally use only the Python standard library
so the template remains easy to copy into document projects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser


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


@dataclass
class FragmentNode:
    tag: str
    attrs: dict[str, str | None]
    start: int
    start_tag_end: int
    end_tag_start: int | None = None
    end: int | None = None
    children: list["FragmentNode"] = field(default_factory=list)


class FragmentParser(HTMLParser):
    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=False)
        self.source = source
        self.line_starts = self.build_line_starts(source)
        self.roots: list[FragmentNode] = []
        self.stack: list[FragmentNode] = []

    @staticmethod
    def build_line_starts(source: str) -> list[int]:
        starts = [0]
        for index, character in enumerate(source):
            if character == "\n":
                starts.append(index + 1)
        return starts

    def current_index(self) -> int:
        line, column = self.getpos()
        return self.line_starts[line - 1] + column

    def append_node(self, node: FragmentNode) -> None:
        if self.stack:
            self.stack[-1].children.append(node)
        else:
            self.roots.append(node)

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        start = self.current_index()
        start_tag_text = self.get_starttag_text() or ""
        node = FragmentNode(
            tag=tag.lower(),
            attrs=dict(attrs_list),
            start=start,
            start_tag_end=start + len(start_tag_text),
        )
        self.append_node(node)

        if node.tag not in VOID_TAGS:
            self.stack.append(node)
        else:
            node.end_tag_start = node.start_tag_end
            node.end = node.start_tag_end

    def handle_startendtag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        start = self.current_index()
        start_tag_text = self.get_starttag_text() or ""
        node = FragmentNode(
            tag=tag.lower(),
            attrs=dict(attrs_list),
            start=start,
            start_tag_end=start + len(start_tag_text),
            end_tag_start=start + len(start_tag_text),
            end=start + len(start_tag_text),
        )
        self.append_node(node)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        end_tag_start = self.current_index()
        end = self.source.find(">", end_tag_start)
        end_tag_end = len(self.source) if end == -1 else end + 1

        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                node = self.stack[index]
                node.end_tag_start = end_tag_start
                node.end = end_tag_end
                del self.stack[index:]
                return

    def close(self) -> None:
        super().close()
        for node in self.stack:
            node.end_tag_start = len(self.source)
            node.end = len(self.source)
        self.stack.clear()


def parse_fragment(source: str) -> list[FragmentNode]:
    parser = FragmentParser(source)
    parser.feed(source)
    parser.close()
    return parser.roots


def iter_nodes(nodes: list[FragmentNode]) -> list[FragmentNode]:
    result: list[FragmentNode] = []
    stack = list(reversed(nodes))

    while stack:
        node = stack.pop()
        result.append(node)
        stack.extend(reversed(node.children))

    return result


def has_class(attrs: dict[str, str | None], class_name: str) -> bool:
    return class_name in (attrs.get("class") or "").split()


def language_from_classes(class_attr: str | None) -> str | None:
    for class_name in (class_attr or "").split():
        if class_name.startswith("language-"):
            return class_name.removeprefix("language-")
    return None


def node_inner_html(source: str, node: FragmentNode) -> str:
    end = node.end_tag_start if node.end_tag_start is not None else node.end or len(source)
    return source[node.start_tag_end:end]


def text_content(source: str, node: FragmentNode) -> str:
    class TextCollector(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.parts: list[str] = []

        def handle_data(self, data: str) -> None:
            self.parts.append(data)

    collector = TextCollector()
    collector.feed(node_inner_html(source, node))
    collector.close()
    return "".join(collector.parts).strip()


def replace_ranges(source: str, replacements: list[tuple[int, int, str]]) -> str:
    rendered = source

    for start, end, replacement in sorted(replacements, key=lambda item: item[0], reverse=True):
        rendered = rendered[:start] + replacement + rendered[end:]

    return rendered
