import tempfile
import unittest
from pathlib import Path

from scripts.check_html import check_file


class CheckHtmlTests(unittest.TestCase):
    def test_external_script_and_stylesheet_require_sri_and_crossorigin(self) -> None:
        html = """<!doctype html>
<html lang="en">
<head>
  <script src="https://cdn.example.test/library.js"></script>
  <link rel="stylesheet" href="https://cdn.example.test/library.css">
</head>
<body></body>
</html>
"""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "page.html"
            path.write_text(html, encoding="utf-8")
            messages = [issue.message for issue in check_file(path)]

        self.assertIn('external script asset "https://cdn.example.test/library.js" must declare integrity', messages)
        self.assertIn('external script asset "https://cdn.example.test/library.js" must declare crossorigin="anonymous"', messages)
        self.assertIn('external link asset "https://cdn.example.test/library.css" must declare integrity', messages)
        self.assertIn('external link asset "https://cdn.example.test/library.css" must declare crossorigin="anonymous"', messages)

    def test_external_assets_with_sri_and_crossorigin_pass_policy(self) -> None:
        html = """<!doctype html>
<html lang="en">
<head>
  <script src="https://cdn.example.test/library.js" integrity="sha384-example" crossorigin="anonymous"></script>
  <link rel="stylesheet" href="https://cdn.example.test/library.css" integrity="sha384-example" crossorigin="anonymous">
</head>
<body></body>
</html>
"""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "page.html"
            path.write_text(html, encoding="utf-8")
            messages = [issue.message for issue in check_file(path)]

        self.assertFalse([message for message in messages if "external" in message])

    def test_callout_requires_direct_label_child(self) -> None:
        html = """<!doctype html>
<html lang="en">
<body>
  <aside class="callout callout-note">
    <p>This note is missing a label.</p>
  </aside>
  <aside class="callout callout-warning">
    <div><div class="callout-label">Warning</div></div>
    <p>This warning has a nested label, not a direct label.</p>
  </aside>
</body>
</html>
"""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "page.html"
            path.write_text(html, encoding="utf-8")
            messages = [issue.message for issue in check_file(path)]

        self.assertEqual(messages.count(".callout must contain a direct .callout-label child"), 2)

    def test_callout_accepts_direct_label_child(self) -> None:
        html = """<!doctype html>
<html lang="en">
<body>
  <aside class="callout callout-note">
    <div class="callout-label">Note</div>
    <p>This note has a direct label.</p>
  </aside>
</body>
</html>
"""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "page.html"
            path.write_text(html, encoding="utf-8")
            messages = [issue.message for issue in check_file(path)]

        self.assertNotIn(".callout must contain a direct .callout-label child", messages)


if __name__ == "__main__":
    unittest.main()
