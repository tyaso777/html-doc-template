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
            manifest.heading_numbering,
            {
                "enabled": False,
                "levels": [],
                "body": True,
                "toc": True,
                "format": "{number}. {title}",
                "levelFormats": {},
                "tocTitleMode": "numbered",
            },
        )
        self.assertEqual(
            manifest.numbering,
            {
                "figures": {"enabled": False, "format": "{index}", "reset": "chapter"},
                "tables": {"enabled": False, "format": "{index}", "reset": "chapter"},
                "equations": {"enabled": False, "format": "{index}", "reset": "chapter"},
            },
        )
        self.assertEqual(
            manifest.chapters,
            [
                {
                    "title": "Intro",
                    "source": "01-introduction.html",
                    "href": "01-introduction.html",
                    "number": "1",
                    "sidebarTitle": "Intro",
                    "subtitle": "",
                    "externalLinks": [],
                }
            ],
        )

    def test_normalize_manifest_keeps_chapter_external_links(self) -> None:
        manifest = normalize_manifest(
            {
                "externalLinks": [
                    {
                        "title": "Common",
                        "items": [{"label": "Common link", "href": "https://example.com/common"}],
                    }
                ],
                "chapters": [
                    {
                        "title": "Intro",
                        "source": "01-introduction.html",
                        "href": "01-introduction.html",
                        "externalLinks": [
                            {
                                "title": "Chapter links",
                                "items": [{"label": "Chapter link", "href": "https://example.com/chapter"}],
                            }
                        ],
                    }
                ],
            }
        )

        self.assertEqual(manifest.external_links[0]["title"], "Common")
        self.assertEqual(manifest.chapters[0]["externalLinks"][0]["title"], "Chapter links")

    def test_normalize_manifest_keeps_heading_numbering(self) -> None:
        manifest = normalize_manifest(
            {
                "headingNumbering": {
                    "enabled": True,
                    "levels": [2, 3],
                    "body": False,
                    "toc": True,
                    "format": "{number}. {title}",
                    "levelFormats": {"2": "第{local}章 {title}", "3": "{number} {title}"},
                    "tocTitleMode": "plain",
                },
                "chapters": [
                    {
                        "title": "Intro",
                        "source": "01-introduction.html",
                        "href": "01-introduction.html",
                    }
                ],
            }
        )

        self.assertTrue(manifest.heading_numbering["enabled"])
        self.assertEqual(manifest.heading_numbering["levels"], [2, 3])
        self.assertFalse(manifest.heading_numbering["body"])
        self.assertEqual(manifest.heading_numbering["levelFormats"]["2"], "第{local}章 {title}")
        self.assertEqual(manifest.heading_numbering["tocTitleMode"], "plain")

    def test_normalize_manifest_keeps_numbering(self) -> None:
        manifest = normalize_manifest(
            {
                "numbering": {
                    "figures": {"enabled": True, "format": "図{chapter}-{index}", "reset": "chapter"},
                    "tables": {"enabled": True, "format": "表{index}", "reset": "document"},
                    "equations": {"enabled": False, "format": "式{chapter}-{index}", "reset": "chapter"},
                },
                "chapters": [
                    {
                        "title": "Intro",
                        "source": "01-introduction.html",
                        "href": "01-introduction.html",
                        "number": "A",
                    }
                ],
            }
        )

        self.assertEqual(manifest.chapters[0]["number"], "A")
        self.assertTrue(manifest.numbering["figures"]["enabled"])
        self.assertEqual(manifest.numbering["figures"]["format"], "図{chapter}-{index}")
        self.assertEqual(manifest.numbering["tables"]["reset"], "document")

    def test_manifest_validation_reports_invalid_shapes(self) -> None:
        self.assertEqual(manifest_validation_errors([]), ["site manifest must be a JSON object"])

        errors = manifest_validation_errors(
            {
                "shell": "",
                "outputDir": "",
                "lang": "",
                "materials": {},
                "externalLinks": {},
                "headingNumbering": {
                    "enabled": "yes",
                    "levels": [1, "3"],
                    "body": "yes",
                    "toc": "yes",
                    "format": "{number}",
                    "levelFormats": {"1": "{title}", "2": "{number}"},
                    "tocTitleMode": "bad",
                },
                "numbering": {
                    "figures": {"enabled": "yes", "format": "図{chapter}", "reset": "bad"},
                    "tables": [],
                    "equations": {"enabled": True, "format": 123, "reset": "chapter"},
                },
                "chapters": [
                    "not an object",
                    {
                        "title": "",
                        "source": "",
                        "href": "",
                        "number": "",
                        "sidebarTitle": 123,
                        "subtitle": 456,
                        "externalLinks": {},
                    },
                ],
            }
        )

        self.assertIn("site manifest must have a non-empty shell path", errors)
        self.assertIn("site manifest must have a non-empty outputDir", errors)
        self.assertIn("site manifest lang must be a non-empty string", errors)
        self.assertIn("site manifest materials must be an array when provided", errors)
        self.assertIn("site manifest externalLinks must be an array when provided", errors)
        self.assertIn("site manifest headingNumbering enabled must be a boolean", errors)
        self.assertIn("site manifest headingNumbering body must be a boolean", errors)
        self.assertIn("site manifest headingNumbering toc must be a boolean", errors)
        self.assertIn("site manifest headingNumbering levels must be an array of integers from 2 to 6", errors)
        self.assertIn('site manifest headingNumbering format must be a string containing "{title}"', errors)
        self.assertIn("site manifest headingNumbering levelFormats keys must be heading levels 2 through 6", errors)
        self.assertIn('site manifest headingNumbering levelFormats 2 must be a string containing "{title}"', errors)
        self.assertIn('site manifest headingNumbering tocTitleMode must be "numbered" or "plain"', errors)
        self.assertIn("site manifest numbering figures enabled must be a boolean", errors)
        self.assertIn('site manifest numbering figures format must be a string containing "{index}"', errors)
        self.assertIn('site manifest numbering figures reset must be "chapter" or "document"', errors)
        self.assertIn("site manifest numbering tables must be an object when provided", errors)
        self.assertIn('site manifest numbering equations format must be a string containing "{index}"', errors)
        self.assertIn("chapter 1 must be an object", errors)
        self.assertIn("chapter 2 must have a non-empty title", errors)
        self.assertIn("chapter 2 must have a non-empty source", errors)
        self.assertIn("chapter 2 must have a non-empty href", errors)
        self.assertIn("chapter 2 number must be a non-empty string or integer", errors)
        self.assertIn("chapter 2 sidebarTitle must be a string", errors)
        self.assertIn("chapter 2 subtitle must be a string", errors)
        self.assertIn("chapter 2 externalLinks must be an array when provided", errors)

    def test_manifest_validation_reports_invalid_link_tree_items(self) -> None:
        errors = manifest_validation_errors(
            {
                "externalLinks": [
                    {"title": "Broken group", "items": [{"label": "Missing href"}]},
                    {"label": "", "href": ""},
                ],
                "chapters": [
                    {
                        "title": "Intro",
                        "source": "01-introduction.html",
                        "href": "01-introduction.html",
                        "externalLinks": [{"title": "", "items": "bad"}],
                    }
                ],
            }
        )

        self.assertIn("site manifest externalLinks item 1 group items item 1 link must have a non-empty href", errors)
        self.assertIn("site manifest externalLinks item 2 link must have a non-empty label", errors)
        self.assertIn("site manifest externalLinks item 2 link must have a non-empty href", errors)
        self.assertIn("chapter 1 externalLinks item 1 group must have a non-empty title", errors)
        self.assertIn("chapter 1 externalLinks item 1 group items must be an array", errors)

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
