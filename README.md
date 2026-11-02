# Reverb Sitegen

**A single-file static site generator.** One Python file, zero dependencies,
nothing to install — drop it in a folder and build a complete website:
one page per post, a date-sorted index, an Atom feed, and a sitemap.

By **Dimon Global Group**.

## Quickstart

```bash
mkdir content
cat > content/hello.md <<'EOF'
---
title: Hello World
date: 2026-01-01
---

# Hello World

My first post, with **bold** text and a [link](https://example.com).
EOF

python3 reverb_sitegen.py build content site --title "My Site"
# -> site/index.html, site/hello.html, site/feed.xml, site/sitemap.xml

python3 reverb_sitegen.py build content site --serve
# preview at http://127.0.0.1:8000/
```

Open `site/index.html` in a browser, or upload the `site/` folder to any
static host. All links are relative, so the output works from `file://`
and from any subpath on any host.

## How it works

- **Content** is a folder of `.md` files. Each file becomes one page,
  named after the file (`hello-world.md` → `hello-world.html`).
- **Front matter** is optional. A block delimited by `---` lines at the
  top of a file can set `title:` and `date:` (ISO format). Without it,
  the title falls back to the first heading, then to the filename.
- **Templates** are optional too. Put a `template.html` in the content
  folder with the placeholders `{{title}}`, `{{content}}` and `{{nav}}`,
  or use the clean built-in default.
- **Output** is `index.html` (posts newest-first, with dates),
  `feed.xml` (Atom), `sitemap.xml`, and one HTML page per post with a
  shared navigation header.

## Features

- Single file, Python 3 standard library only — no pip, no build step
- Hand-written Markdown renderer: headings, bold/italic, links, images,
  ordered and unordered lists, fenced code blocks, blockquotes,
  horizontal rules, paragraphs
- Raw HTML in source files is always escaped, never passed through
- Simple `key: value` front matter (`title`, `date`)
- Custom `template.html` support with `{{title}}` / `{{content}}` / `{{nav}}`
- Atom feed and sitemap generated on every build
- Relative links throughout — works from `file://` or any static host
- `--serve` preview via the standard library's HTTP server

## Deliberate limits

This is a small tool on purpose. There are no nested lists, tables,
syntax highlighting, tags, or themes. If you need those, you need a
bigger generator — this one is for getting a clean site up in a minute
and being able to read every line of the tool that built it.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

18 tests: inline and block rendering, front matter, and full
end-to-end builds on fixture content.

## Lineage

Reverb Sitegen is part of the **Reverb** line: clean-room revivals of
beloved early-web tool ideas, rebuilt from scratch for today. The
one-file site builders of the early 2000s proved a website never needed
a framework — this is that idea, reimplemented fresh. No code, name, or
text from any earlier project was used; the design started from the
question "what is the smallest program that turns a folder of Markdown
into a finished site?"

## License

MIT — see [LICENSE](LICENSE). © 2026 Dimon Global Group.
