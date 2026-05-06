import unittest
from pathlib import Path

from scripts.build_site import (
    apply_numbered_items,
    apply_heading_numbering,
    chapter_external_links,
    collect_numbered_items,
    extract_toc_entries,
    indent_content_preserving_raw_text,
    render_shell,
)


class BuildSiteTests(unittest.TestCase):
    def test_indent_content_preserves_pre_code_text(self) -> None:
        content = """<section>
  <p>Before</p>
  <pre class="code-block language-python"><code class="language-python">counts = {}

for log in logs:
    url = log["url"]
    counts[url] = counts.get(url, 0) + 1
</code></pre>
  <p>After</p>
</section>"""

        rendered = indent_content_preserving_raw_text(content, "        ")

        self.assertIn("        <section>", rendered)
        self.assertIn("        <p>Before</p>", rendered)
        self.assertIn("counts = {}\n\nfor log in logs:\n    url = log[\"url\"]", rendered)
        self.assertNotIn("\n        for log in logs:", rendered)
        self.assertIn("        <p>After</p>", rendered)

    def test_indent_content_preserves_textarea_text(self) -> None:
        content = """<div>
<textarea>line one
  line two
</textarea>
</div>"""

        rendered = indent_content_preserving_raw_text(content, "  ")

        self.assertIn("  <div>", rendered)
        self.assertIn("<textarea>line one\n  line two\n", rendered)
        self.assertNotIn("\n    line two", rendered)

    def test_chapter_external_links_append_to_common_links(self) -> None:
        common = [{"title": "Common", "items": [{"label": "Common link", "href": "https://example.com/common"}]}]
        chapter = {
            "externalLinks": [
                {"title": "Chapter", "items": [{"label": "Chapter link", "href": "https://example.com/chapter"}]}
            ]
        }

        links = chapter_external_links(common, chapter)

        self.assertEqual([item["title"] for item in links], ["Common", "Chapter"])
        self.assertEqual([item["title"] for item in common], ["Common"])

    def test_heading_numbering_updates_body_and_toc_titles(self) -> None:
        source = """<section id="overview" data-toc data-toc-title="Overview">
  <h2>Overview</h2>
</section>
<section id="diagrams" data-toc data-toc-title="Diagrams">
  <h2>Diagrams</h2>
  <h3 id="flow" data-toc data-toc-level="3" data-toc-title="Flow">Flow</h3>
  <h3 id="sequence" data-toc data-toc-level="3">Sequence</h3>
</section>"""
        config = {"enabled": True, "body": True, "toc": True, "format": "{number}. {title}", "levels": []}

        rendered, numbering_by_id = apply_heading_numbering(source, config)
        entries = extract_toc_entries(rendered, numbering_by_id, config)

        self.assertIn("<h2>1. Overview</h2>", rendered)
        self.assertIn("<h2>2. Diagrams</h2>", rendered)
        self.assertIn('<h3 id="flow" data-toc data-toc-level="3" data-toc-title="Flow">2.1. Flow</h3>', rendered)
        self.assertEqual([entry["title"] for entry in entries], ["1. Overview", "2. Diagrams", "2.1. Flow", "2.2. Sequence"])

    def test_heading_numbering_numbers_data_toc_title_separately_from_body_heading(self) -> None:
        source = """<section id="failure-patterns" data-toc data-toc-title="Typical Failures">
  <h2>Typical Big Data Failure Patterns</h2>
</section>"""
        config = {
            "enabled": True,
            "body": True,
            "toc": True,
            "format": "{number}. {title}",
            "levels": [],
        }

        rendered, numbering_by_id = apply_heading_numbering(source, config)
        entries = extract_toc_entries(rendered, numbering_by_id, config)

        self.assertIn("<h2>1. Typical Big Data Failure Patterns</h2>", rendered)
        self.assertEqual([entry["title"] for entry in entries], ["1. Typical Failures"])

    def test_heading_numbering_can_keep_toc_titles_plain(self) -> None:
        source = """<section id="overview" data-toc data-toc-title="Short Overview">
  <h2>Long Overview Heading</h2>
</section>"""
        config = {
            "enabled": True,
            "body": True,
            "toc": True,
            "tocTitleMode": "plain",
            "format": "第{local}章 {title}",
            "levels": [],
        }

        rendered, numbering_by_id = apply_heading_numbering(source, config)
        entries = extract_toc_entries(rendered, numbering_by_id, config)

        self.assertIn("<h2>第1章 Long Overview Heading</h2>", rendered)
        self.assertEqual([entry["title"] for entry in entries], ["Short Overview"])

    def test_heading_numbering_can_target_configured_levels(self) -> None:
        source = """<section>
  <h2>Untoced Heading</h2>
  <h3>Untoced Detail</h3>
</section>"""
        config = {
            "enabled": True,
            "body": True,
            "toc": False,
            "format": "{number}. {title}",
            "levels": [2, 3],
        }

        rendered, numbering_by_id = apply_heading_numbering(source, config)

        self.assertIn("<h2>1. Untoced Heading</h2>", rendered)
        self.assertIn("<h3>1.1. Untoced Detail</h3>", rendered)
        self.assertEqual(numbering_by_id, {})

    def test_render_shell_includes_common_and_chapter_external_links(self) -> None:
        shell = (
            "{{DOCUMENT_LANG}} {{DOCUMENT_TITLE}} {{SIDEBAR_TITLE}} {{SIDEBAR_SUBTITLE}} "
            "{{ASSET_PREFIX}} {{CONTENTS_TREE}} {{MATERIALS_SECTION}} "
            "{{EXTERNAL_LINKS_SECTION}} {{CONTENT}}"
        )
        chapter = {
            "title": "Chapter",
            "href": "chapter.html",
            "source": "chapter.html",
            "sidebarTitle": "Chapter",
            "subtitle": "",
            "externalLinks": [
                {"title": "Chapter links", "items": [{"label": "Chapter link", "href": "https://example.com/chapter"}]}
            ],
        }

        rendered = render_shell(
            shell,
            chapter,
            "<p>Body</p>",
            Path("/tmp/project/chapters/chapter.html"),
            Path("/tmp/project"),
            Path("/tmp/project/chapters-src"),
            "en",
            [chapter],
            0,
            Path("/tmp/project/chapters"),
            [[]],
            [],
            [{"title": "Common", "items": [{"label": "Common link", "href": "https://example.com/common"}]}],
        )

        self.assertIn("Common link", rendered)
        self.assertIn("Chapter link", rendered)
        self.assertIn('href="https://example.com/common" target="_blank" rel="noopener"', rendered)
        self.assertIn('href="https://example.com/chapter" target="_blank" rel="noopener"', rendered)

    def test_render_shell_marks_numbered_toc_lists(self) -> None:
        shell = "{{DOCUMENT_LANG}} {{DOCUMENT_TITLE}} {{SIDEBAR_TITLE}} {{SIDEBAR_SUBTITLE}} {{ASSET_PREFIX}} {{CONTENTS_TREE}} {{MATERIALS_SECTION}} {{EXTERNAL_LINKS_SECTION}} {{CONTENT}}"
        chapter = {
            "title": "Chapter",
            "href": "chapter.html",
            "source": "chapter.html",
            "sidebarTitle": "Chapter",
            "subtitle": "",
            "externalLinks": [],
        }

        rendered = render_shell(
            shell,
            chapter,
            "<p>Body</p>",
            Path("/tmp/project/chapters/chapter.html"),
            Path("/tmp/project"),
            Path("/tmp/project/chapters-src"),
            "en",
            [chapter],
            0,
            Path("/tmp/project/chapters"),
            [[{"id": "intro", "title": "1. Intro", "level": 2}]],
            [],
            [],
            {"enabled": True, "toc": True},
        )

        self.assertIn('class="toc-tree toc-tree-numbered"', rendered)

    def test_numbered_items_add_labels_and_resolve_refs(self) -> None:
        sources = [
            """<p>See <span data-ref="flow"></span>, 表(logs), and 式(cost-model).</p>
<figure id="flow" data-numbered="figure">
  <figcaption>MapReduce flow</figcaption>
</figure>
<table id="logs" data-numbered="table">
  <caption>Log sample</caption>
</table>
<div id="cost-model" class="math-block" data-numbered="equation">
  \\[T(n) = O(n \\log n)\\]
</div>"""
        ]
        chapters = [{"href": "chapter.html", "source": "chapter.html", "number": "2"}]
        numbering = {
            "figures": {"enabled": True, "format": "図{chapter}-{index}", "reset": "chapter"},
            "tables": {"enabled": True, "format": "表{chapter}-{index}", "reset": "chapter"},
            "equations": {"enabled": True, "format": "式{chapter}-{index}", "reset": "chapter"},
        }

        registry = collect_numbered_items(sources, chapters, numbering)
        rendered = apply_numbered_items(
            sources[0],
            registry,
            Path("/tmp/project/chapters/chapter.html"),
            Path("/tmp/project/chapters"),
        )

        self.assertIn('<span class="numbered-label figure-number">図2-1</span> MapReduce flow', rendered)
        self.assertIn('<span class="numbered-label table-number">表2-1</span> Log sample', rendered)
        self.assertIn('<div class="equation-label"><span class="numbered-label equation-number">式2-1</span></div>', rendered)
        self.assertIn('<a class="xref figure-ref" href="chapter.html#flow">図2-1</a>', rendered)
        self.assertIn('<a class="xref table-ref" href="chapter.html#logs">表2-1</a>', rendered)
        self.assertIn('<a class="xref equation-ref" href="chapter.html#cost-model">式2-1</a>', rendered)

    def test_numbered_items_can_reset_by_document(self) -> None:
        sources = [
            '<figure id="first" data-numbered="figure"><figcaption>First</figcaption></figure>',
            '<figure id="second" data-numbered="figure"><figcaption>Second</figcaption></figure>',
        ]
        chapters = [
            {"href": "one.html", "source": "one.html", "number": "1"},
            {"href": "two.html", "source": "two.html", "number": "2"},
        ]
        numbering = {
            "figures": {"enabled": True, "format": "図{index}", "reset": "document"},
            "tables": {"enabled": False, "format": "表{index}", "reset": "chapter"},
            "equations": {"enabled": False, "format": "式{index}", "reset": "chapter"},
        }

        registry = collect_numbered_items(sources, chapters, numbering)

        self.assertEqual(registry["first"]["label"], "図1")
        self.assertEqual(registry["second"]["label"], "図2")

    def test_unknown_numbered_refs_raise(self) -> None:
        with self.assertRaisesRegex(ValueError, 'unknown data-ref target "missing"'):
            apply_numbered_items(
                '<p><span data-ref="missing"></span></p>',
                {},
                Path("/tmp/project/chapters/chapter.html"),
                Path("/tmp/project/chapters"),
            )

    def test_numbered_shorthand_does_not_corrupt_raw_text_blocks(self) -> None:
        source = """<div data-python-runner>
  <pre><code class="language-python">if x < 3:
    print("ok")
</code></pre>
</div>"""

        rendered = apply_numbered_items(
            source,
            {},
            Path("/tmp/project/chapters/chapter.html"),
            Path("/tmp/project/chapters"),
        )

        self.assertEqual(rendered, source)


if __name__ == "__main__":
    unittest.main()
