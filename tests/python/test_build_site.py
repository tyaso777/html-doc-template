import unittest

from scripts.build_site import indent_content_preserving_raw_text


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


if __name__ == "__main__":
    unittest.main()
