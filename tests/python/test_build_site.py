import unittest
from pathlib import Path

from scripts.build_site import chapter_external_links, indent_content_preserving_raw_text, render_shell


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


if __name__ == "__main__":
    unittest.main()
