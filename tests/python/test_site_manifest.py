import unittest

from scripts.site_manifest import (
    forbidden_source_patterns,
    manifest_validation_errors,
    missing_shell_tokens,
    normalize_manifest,
)


class SiteManifestTests(unittest.TestCase):
    def test_normalize_manifest_applies_defaults(self) -> None:
        manifest = normalize_manifest(
            {
                "chapters": [
                    {
                        "title": "Intro",
                        "source": "01-introduction.html",
                        "href": "01-introduction.html",
                    }
                ]
            }
        )

        self.assertEqual(manifest.shell, "../layouts/chapter-shell.html")
        self.assertEqual(manifest.output_dir, "../chapters")
        self.assertEqual(manifest.document_lang, "en")
        self.assertEqual(manifest.materials, [])
        self.assertEqual(manifest.external_links, [])
        self.assertEqual(
            manifest.chapters,
            [
                {
                    "title": "Intro",
                    "source": "01-introduction.html",
                    "href": "01-introduction.html",
                    "sidebarTitle": "Intro",
                    "subtitle": "",
                }
            ],
        )

    def test_manifest_validation_reports_invalid_shapes(self) -> None:
        self.assertEqual(manifest_validation_errors([]), ["site manifest must be a JSON object"])

        errors = manifest_validation_errors(
            {
                "shell": "",
                "outputDir": "",
                "lang": "",
                "materials": {},
                "externalLinks": {},
                "chapters": [
                    "not an object",
                    {
                        "title": "",
                        "source": "",
                        "href": "",
                        "sidebarTitle": 123,
                        "subtitle": 456,
                    },
                ],
            }
        )

        self.assertIn("site manifest must have a non-empty shell path", errors)
        self.assertIn("site manifest must have a non-empty outputDir", errors)
        self.assertIn("site manifest lang must be a non-empty string", errors)
        self.assertIn("site manifest materials must be an array when provided", errors)
        self.assertIn("site manifest externalLinks must be an array when provided", errors)
        self.assertIn("chapter 1 must be an object", errors)
        self.assertIn("chapter 2 must have a non-empty title", errors)
        self.assertIn("chapter 2 must have a non-empty source", errors)
        self.assertIn("chapter 2 must have a non-empty href", errors)
        self.assertIn("chapter 2 sidebarTitle must be a string", errors)
        self.assertIn("chapter 2 subtitle must be a string", errors)

    def test_normalize_manifest_raises_for_invalid_manifest(self) -> None:
        with self.assertRaisesRegex(ValueError, "site manifest must contain a chapters array"):
            normalize_manifest({})

    def test_shell_and_source_policy_helpers(self) -> None:
        shell = "{{DOCUMENT_LANG}} {{DOCUMENT_TITLE}}"
        self.assertIn("{{CONTENT}}", missing_shell_tokens(shell))

        patterns = forbidden_source_patterns("<article><script src=\"x.js\"></script></article>")
        self.assertEqual([pattern.pattern for pattern in patterns], [r"<script(?:\s|>)"])


if __name__ == "__main__":
    unittest.main()
