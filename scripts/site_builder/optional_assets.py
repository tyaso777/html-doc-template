from __future__ import annotations

import html
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    from html_fragment import iter_nodes, parse_fragment
except ModuleNotFoundError:
    from scripts.html_fragment import iter_nodes, parse_fragment


CDN_ASSETS_PATH = Path(__file__).with_name("cdn-assets.json")


@lru_cache(maxsize=1)
def load_cdn_assets() -> dict[str, Any]:
    return json.loads(CDN_ASSETS_PATH.read_text(encoding="utf-8"))


def render_asset_tag(asset: dict[str, Any]) -> str:
    asset_type = asset.get("type")
    attrs: list[tuple[str, str | None]] = []

    if asset_type == "stylesheet":
        attrs.append(("rel", "stylesheet"))
        attrs.append(("href", str(asset["href"])))
    elif asset_type == "script":
        if asset.get("defer", False):
            attrs.append(("defer", None))
        attrs.append(("src", str(asset["src"])))
    else:
        raise ValueError(f'unsupported CDN asset type "{asset_type}"')

    for name in ("integrity", "crossorigin", "referrerpolicy"):
        if name in asset:
            attrs.append((name, str(asset[name])))

    rendered_attrs = " ".join(
        html.escape(name, quote=True) if value is None else f'{html.escape(name, quote=True)}="{html.escape(value, quote=True)}"'
        for name, value in attrs
    )

    if asset_type == "stylesheet":
        return f"<link {rendered_attrs}>"
    return f"<script {rendered_attrs}></script>"


def render_asset_tags(assets: list[dict[str, Any]], indent: str = "  ") -> str:
    return "\n".join(f"{indent}{render_asset_tag(asset)}" for asset in assets)


def render_fixed_head_assets(indent: str = "  ") -> str:
    return render_asset_tags(load_cdn_assets().get("fixed", []), indent)


def node_classes(class_value: str | None) -> set[str]:
    return set((class_value or "").split())


def optional_asset_keys(source: str) -> set[str]:
    keys: set[str] = set()

    for node in iter_nodes(parse_fragment(source)):
        classes = node_classes(node.attrs.get("class"))
        if "mermaid" in classes:
            keys.add("mermaid")
        if "vega-lite" in classes or "data-vega-lite" in node.attrs:
            keys.add("vega-lite")

    return keys


def render_optional_head_assets(source: str, indent: str = "  ") -> str:
    keys = optional_asset_keys(source)
    optional_assets = load_cdn_assets().get("optional", {})
    assets: list[str] = []

    for key in ("mermaid", "vega-lite"):
        if key in keys:
            assets.extend(render_asset_tag(asset) for asset in optional_assets.get(key, []))

    return "\n".join(f"{indent}{asset}" for asset in assets)
