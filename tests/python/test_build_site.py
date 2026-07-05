import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.build_site import (
    apply_numbered_items,
    apply_section_refs,
    apply_heading_numbering,
    build_site,
    chapter_external_links,
    collect_numbered_items,
    collect_section_refs,
    extract_toc_entries,
    indent_content_preserving_raw_text,
    render_shell,
)
from scripts.site_builder.optional_assets import optional_asset_keys, render_fixed_head_assets, render_optional_head_assets


class BuildSiteTests(unittest.TestCase):
    def test_optional_head_assets_detect_mermaid_and_vega_lite(self) -> None:
        source = (
            '<pre class="code-block language-mermaid"><code>flowchart LR</code></pre>'
            '<div class="mermaid">flowchart LR\nA --> B</div>'
            '<div data-vega-lite data-vega-lite-spec="chart-spec"></div>'
        )

        self.assertEqual(optional_asset_keys(source), {"mermaid", "vega-lite"})

        rendered = render_optional_head_assets(source)
        self.assertIn("mermaid.min.js", rendered)
        self.assertIn("vega.min.js", rendered)
        self.assertIn("vega-lite.min.js", rendered)
        self.assertIn("vega-embed.min.js", rendered)

    def test_fixed_head_assets_render_from_json(self) -> None:
        rendered = render_fixed_head_assets()

        self.assertIn("prism.min.css", rendered)
        self.assertIn("prism.min.js", rendered)
        self.assertIn("mathjax@3.2.2", rendered)
        self.assertIn('crossorigin="anonymous"', rendered)
        self.assertIn('referrerpolicy="no-referrer"', rendered)

    def test_optional_head_assets_ignore_mermaid_code_blocks(self) -> None:
        source = '<pre class="code-block language-mermaid"><code>flowchart LR</code></pre>'

        self.assertEqual(optional_asset_keys(source), set())
        self.assertEqual(render_optional_head_assets(source), "")

    def test_build_site_can_build_basic_fixture_to_temp_output(self) -> None:
        root = Path(__file__).resolve().parents[2]
        manifest_path = root / "tests/fixtures/basic-site/chapters-src/site-manifest.json"

        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "chapters"
            output_paths = build_site(root, manifest_path, output_dir)

            self.assertEqual(
                [path.name for path in output_paths],
                ["01-introduction.html", "02-examples.html", "03-reference.html"],
            )
            introduction = (output_dir / "01-introduction.html").read_text(encoding="utf-8")
            self.assertIn('href="01-introduction.html#python-runner-example">Section 4.2</a>', introduction)
            self.assertIn('href="02-examples.html"', introduction)

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

    def test_section_refs_use_heading_numbering_registry(self) -> None:
        sources = [
            """<p>See <a data-heading-ref="plan"></a>, <a data-section-ref="detail"></a>, and <span data-heading-ref="deeper"></span>.</p>
<section id="plan" data-toc data-toc-title="Plan">
  <h2>DAG Plan</h2>
  <h3 id="detail" data-toc data-toc-level="3" data-toc-title="Detail">Execution Detail</h3>
  <h4 id="deeper" data-toc data-toc-level="4" data-toc-title="Deeper">Execution Detail Item</h4>
</section>"""
        ]
        chapters = [{"href": "chapter.html", "source": "chapter.html", "number": "4"}]
        config = {
            "enabled": True,
            "body": True,
            "toc": True,
            "format": "{number}. {title}",
            "levels": [],
            "referenceFormat": "{number} {title}",
            "referenceLevelFormats": {
                "2": "第{number}章",
                "3": "第{number}節",
                "4": "第{number}項",
            },
        }

        registry = collect_section_refs(sources, chapters, config)
        numbered_source, _ = apply_heading_numbering(sources[0], config)
        rendered = apply_section_refs(
            numbered_source,
            registry,
            Path("/tmp/project/chapters/chapter.html"),
            Path("/tmp/project/chapters"),
            config,
        )

        self.assertIn('<a class="xref section-ref" href="chapter.html#plan">第1章</a>', rendered)
        self.assertIn('<a class="xref section-ref" href="chapter.html#detail">第1.1節</a>', rendered)
        self.assertIn('<a class="xref section-ref" href="chapter.html#deeper">第1.1.1項</a>', rendered)

    def test_section_refs_fall_back_to_default_reference_format(self) -> None:
        sources = ['<section id="plan" data-toc><h2>Plan</h2></section><p><span data-heading-ref="plan"></span></p>']
        chapters = [{"href": "chapter.html", "source": "chapter.html", "number": "1"}]
        config = {
            "enabled": True,
            "body": True,
            "toc": True,
            "format": "{number}. {title}",
            "levels": [],
            "referenceFormat": "{number} {title}",
            "referenceLevelFormats": {"3": "第{number}節"},
        }

        registry = collect_section_refs(sources, chapters, config)
        rendered = apply_section_refs(
            sources[0],
            registry,
            Path("/tmp/project/chapters/chapter.html"),
            Path("/tmp/project/chapters"),
            config,
        )

        self.assertIn('<a class="xref section-ref" href="chapter.html#plan">1 Plan</a>', rendered)

    def test_unknown_section_refs_raise(self) -> None:
        with self.assertRaisesRegex(ValueError, 'unknown data-section-ref target "missing"'):
            apply_section_refs(
                '<p><a data-section-ref="missing"></a></p>',
                {},
                Path("/tmp/project/chapters/chapter.html"),
                Path("/tmp/project/chapters"),
                {"enabled": True, "referenceFormat": "{number}"},
            )

    def test_render_shell_includes_common_and_chapter_external_links(self) -> None:
        shell = (
            "{{DOCUMENT_LANG}} {{DOCUMENT_TITLE}} {{DOCUMENT_DESCRIPTION}} {{SITE_TITLE}} {{SIDEBAR_TITLE}} {{SIDEBAR_SUBTITLE}} "
            "{{ASSET_PREFIX}} {{DEFAULT_LAYOUT_MODE}} {{FIXED_HEAD_ASSETS}} {{OPTIONAL_HEAD_ASSETS}} {{CONTENTS_TREE}} {{MATERIALS_SECTION}} "
            "{{EXTERNAL_LINKS_SECTION}} {{CONTENT}}"
        )
        chapter = {
            "title": "Chapter",
            "href": "chapter.html",
            "source": "chapter.html",
            "sidebarTitle": "Chapter",
            "subtitle": "",
            "description": "Chapter & details",
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
            "Site & Docs",
            "Site description",
            [chapter],
            0,
            Path("/tmp/project/chapters"),
            [[]],
            [],
            [{"title": "Common", "items": [{"label": "Common link", "href": "https://example.com/common"}]}],
            "<script defer src=\"optional.js\"></script>",
            {"defaultMode": "wide"},
        )

        self.assertIn("Common link", rendered)
        self.assertIn("Chapter &amp; details", rendered)
        self.assertIn("Site &amp; Docs", rendered)
        self.assertIn("Chapter link", rendered)
        self.assertIn("prism.min.css", rendered)
        self.assertIn("wide", rendered)
        self.assertIn("optional.js", rendered)
        self.assertIn('href="https://example.com/common" target="_blank" rel="noopener"', rendered)
        self.assertIn('href="https://example.com/chapter" target="_blank" rel="noopener"', rendered)

    def test_render_shell_marks_numbered_toc_lists(self) -> None:
        shell = "{{DOCUMENT_LANG}} {{DOCUMENT_TITLE}} {{DOCUMENT_DESCRIPTION}} {{SITE_TITLE}} {{SIDEBAR_TITLE}} {{SIDEBAR_SUBTITLE}} {{ASSET_PREFIX}} {{DEFAULT_LAYOUT_MODE}} {{FIXED_HEAD_ASSETS}} {{OPTIONAL_HEAD_ASSETS}} {{CONTENTS_TREE}} {{MATERIALS_SECTION}} {{EXTERNAL_LINKS_SECTION}} {{CONTENT}}"
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
            "Site",
            "Description",
            [chapter],
            0,
            Path("/tmp/project/chapters"),
            [[{"id": "intro", "title": "1. Intro", "level": 2}]],
            [],
            [],
            "",
            {"defaultMode": "standard"},
            {"enabled": True, "toc": True},
        )

        self.assertIn('class="toc-tree toc-tree-numbered"', rendered)

    def test_numbered_items_add_labels_and_resolve_refs(self) -> None:
        sources = [
            """<p>See <span data-ref="flow"></span>, <span data-ref="logs"></span>, and <span data-ref="cost-model"></span>.</p>
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

if __name__ == "__main__":
    unittest.main()
