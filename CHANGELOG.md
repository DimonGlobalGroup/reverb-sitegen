# Changelog

All notable changes to Reverb Sitegen are documented here.

## [1.0.0] - 2026-11-01

Initial public release.

- Single-file static site generator (`reverb_sitegen.py`), Python 3
  standard library only, no dependencies.
- Hand-written Markdown renderer: headings, bold/italic, links, images,
  ordered/unordered lists, fenced code blocks, blockquotes, horizontal
  rules, paragraphs; raw HTML always escaped.
- Optional front matter (`title`, `date`) and optional custom
  `template.html` with `{{title}}` / `{{content}}` / `{{nav}}`
  placeholders; clean built-in default template.
- Per-post HTML pages, date-sorted index, Atom feed (`feed.xml`) and
  `sitemap.xml` on every build; relative links throughout.
- `build` CLI with `--title`, plus `--serve` / `--port` for local
  preview via `http.server`.
- Test suite: 18 tests covering the renderer, front matter, and
  end-to-end builds.
