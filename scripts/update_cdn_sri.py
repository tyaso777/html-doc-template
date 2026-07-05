#!/usr/bin/env python3
"""Update or verify SRI hashes in scripts/site_builder/cdn-assets.json."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any, Iterable


DEFAULT_ASSETS_PATH = Path(__file__).resolve().parent / "site_builder" / "cdn-assets.json"
SUPPORTED_ALGORITHMS = {"sha256", "sha384", "sha512"}


def iter_assets(config: dict[str, Any]) -> Iterable[dict[str, Any]]:
    fixed = config.get("fixed", [])
    if isinstance(fixed, list):
        yield from (asset for asset in fixed if isinstance(asset, dict))

    optional = config.get("optional", {})
    if isinstance(optional, dict):
        for assets in optional.values():
            if isinstance(assets, list):
                yield from (asset for asset in assets if isinstance(asset, dict))


def asset_url(asset: dict[str, Any]) -> str:
    raw_url = asset.get("href") if asset.get("type") == "stylesheet" else asset.get("src")
    if not isinstance(raw_url, str) or not raw_url:
        raise ValueError(f"CDN asset is missing href/src: {asset!r}")
    return raw_url


def integrity_algorithm(integrity: str) -> str:
    algorithm = integrity.split("-", 1)[0]
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError(f'unsupported SRI algorithm "{algorithm}"')
    return algorithm


def fetch_bytes(url: str, timeout: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "html-doc-template-sri-updater"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def sri_hash(content: bytes, algorithm: str) -> str:
    digest = hashlib.new(algorithm, content).digest()
    return f"{algorithm}-{base64.b64encode(digest).decode('ascii')}"


def load_assets(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_assets(path: Path, config: dict[str, Any]) -> None:
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def update_integrities(config: dict[str, Any], *, check: bool, timeout: int) -> list[str]:
    mismatches: list[str] = []

    for asset in iter_assets(config):
        url = asset_url(asset)
        current_integrity = asset.get("integrity")
        if not isinstance(current_integrity, str) or not current_integrity:
            raise ValueError(f"CDN asset is missing integrity: {url}")

        expected_integrity = sri_hash(fetch_bytes(url, timeout), integrity_algorithm(current_integrity))
        if current_integrity == expected_integrity:
            continue

        mismatches.append(url)
        if not check:
            asset["integrity"] = expected_integrity

    return mismatches


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update or verify SRI hashes in cdn-assets.json.")
    parser.add_argument("--assets", default=str(DEFAULT_ASSETS_PATH), help="Path to cdn-assets.json.")
    parser.add_argument("--check", action="store_true", help="Fail if any integrity value is stale.")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds per asset.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    assets_path = Path(args.assets)
    config = load_assets(assets_path)
    mismatches = update_integrities(config, check=args.check, timeout=args.timeout)

    if args.check:
        if mismatches:
            for url in mismatches:
                print(f"stale SRI: {url}", file=sys.stderr)
            return 1
        print("OK: CDN SRI hashes are current")
        return 0

    if mismatches:
        write_assets(assets_path, config)
        print(f"updated {len(mismatches)} CDN SRI hash(es)")
    else:
        print("OK: CDN SRI hashes are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
