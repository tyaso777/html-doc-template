# Agent Instructions

This repository commits generated HTML for both the starter document and the persistent template guide.

When changing template behavior, shared assets, layouts, or documentation examples, keep these source/output pairs in sync:

- `chapters-src/` -> `chapters/`
- `template-docs/chapters-src/` -> `template-docs/chapters/`

For template-development changes, run `npm run build:all` before finishing so both generated output trees are refreshed. Do not update only `template-docs/chapters/` or only `chapters/` when the corresponding source or shared rendering behavior has changed.

The two generated trees are not expected to contain identical content. `chapters/` is the minimal starter document, while `template-docs/chapters/` is the maintained guide with detailed component examples. They should, however, both be regenerated from their current sources whenever shared template behavior changes.

Prefer editing source files first:

- Edit `chapters-src/*.html` for starter document examples.
- Edit `template-docs/chapters-src/*.html` for the persistent template guide.
- Treat `chapters/` and `template-docs/chapters/` as generated output.

Run `npm run check:html` after rebuilding.
