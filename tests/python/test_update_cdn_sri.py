import base64
import hashlib
import unittest
from unittest.mock import patch

from scripts.update_cdn_sri import integrity_algorithm, sri_hash, update_integrities


class UpdateCdnSriTests(unittest.TestCase):
    def test_sri_hash_uses_requested_algorithm(self) -> None:
        content = b"example"
        expected = base64.b64encode(hashlib.sha384(content).digest()).decode("ascii")

        self.assertEqual(sri_hash(content, "sha384"), f"sha384-{expected}")

    def test_integrity_algorithm_rejects_unsupported_algorithm(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported SRI algorithm"):
            integrity_algorithm("md5-example")

    def test_update_integrities_updates_nested_assets(self) -> None:
        config = {
            "fixed": [
                {
                    "type": "script",
                    "src": "https://example.test/app.js",
                    "integrity": "sha384-stale",
                }
            ],
            "optional": {
                "chart": [
                    {
                        "type": "stylesheet",
                        "href": "https://example.test/chart.css",
                        "integrity": "sha384-stale",
                    }
                ]
            },
        }

        with patch("scripts.update_cdn_sri.fetch_bytes", return_value=b"asset"):
            mismatches = update_integrities(config, check=False, timeout=1)

        self.assertEqual(
            mismatches,
            ["https://example.test/app.js", "https://example.test/chart.css"],
        )
        self.assertEqual(config["fixed"][0]["integrity"], sri_hash(b"asset", "sha384"))
        self.assertEqual(config["optional"]["chart"][0]["integrity"], sri_hash(b"asset", "sha384"))

    def test_update_integrities_check_mode_does_not_mutate(self) -> None:
        config = {
            "fixed": [
                {
                    "type": "script",
                    "src": "https://example.test/app.js",
                    "integrity": "sha384-stale",
                }
            ]
        }

        with patch("scripts.update_cdn_sri.fetch_bytes", return_value=b"asset"):
            mismatches = update_integrities(config, check=True, timeout=1)

        self.assertEqual(mismatches, ["https://example.test/app.js"])
        self.assertEqual(config["fixed"][0]["integrity"], "sha384-stale")


if __name__ == "__main__":
    unittest.main()
