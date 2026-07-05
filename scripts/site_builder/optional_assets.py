from __future__ import annotations

try:
    from html_fragment import iter_nodes, parse_fragment
except ModuleNotFoundError:
    from scripts.html_fragment import iter_nodes, parse_fragment


MERMAID_ASSET = '<script defer src="https://cdn.jsdelivr.net/npm/mermaid@11.14.0/dist/mermaid.min.js" integrity="sha512-1CZj4aGbVA13DvizpBtnnUCPqBMDokst010DHdNrd7E79k2BoZqRaU0xybAKlsWERxKlLoAqvHpuKE1mBuveUQ==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>'
VEGA_LITE_ASSETS = [
    '<script defer src="https://cdn.jsdelivr.net/npm/vega@5.33.0/build/vega.min.js" integrity="sha384-Kpi0LDGE2Pg6N3+B3LiVIugYJ3rGL3AAqlnkRLfFxZtmejptl+TJ3iKY54HF5U3l" crossorigin="anonymous" referrerpolicy="no-referrer"></script>',
    '<script defer src="https://cdn.jsdelivr.net/npm/vega-lite@5.23.0/build/vega-lite.min.js" integrity="sha384-D9LYH0esGjcxQJsBuxOuXtCDJGXRWW1+KhluzWPqi0rLJmiR/ygPChefaD+rFFDQ" crossorigin="anonymous" referrerpolicy="no-referrer"></script>',
    '<script defer src="https://cdn.jsdelivr.net/npm/vega-embed@6.29.0/build/vega-embed.min.js" integrity="sha384-M+Ax7e/WFJpxSOF09HzI+Sj4wg9ottVd/uxmV2ItGGh02fLH28t2FAOJx3TJBap5" crossorigin="anonymous" referrerpolicy="no-referrer"></script>',
]


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
    assets: list[str] = []

    if "mermaid" in keys:
        assets.append(MERMAID_ASSET)
    if "vega-lite" in keys:
        assets.extend(VEGA_LITE_ASSETS)

    return "\n".join(f"{indent}{asset}" for asset in assets)
