#!/usr/bin/env python3
"""Reverb Sitegen - a single-file static site generator.

Turns a directory of Markdown files into a complete static site:
one HTML page per post, a date-sorted index, an Atom feed and a
sitemap. Pure Python 3 standard library; no dependencies, no build
tools, nothing to install.

Usage:
    python3 reverb_sitegen.py build <content_dir> <output_dir> [--title NAME]
    python3 reverb_sitegen.py build <content_dir> <output_dir> --serve [--port N]

By Dimon Global Group. MIT licensed.
"""

import argparse
import datetime
import html
import os
import re
import sys
from xml.sax.saxutils import escape as xml_escape

__version__ = "1.0.0"

# ---------------------------------------------------------------------------
# Front matter
# ---------------------------------------------------------------------------

def parse_front_matter(text):
    """Split a document into (metadata dict, body string).

    Front matter is a block at the very top of the file, delimited by
    lines containing only '---', holding simple 'key: value' pairs:

        ---
        title: My Post
        date: 2026-01-15
        ---
    """
    meta = {}
    body = text
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                for fm_line in lines[1:idx]:
                    if ":" in fm_line:
                        key, _, value = fm_line.partition(":")
                        meta[key.strip().lower()] = value.strip().strip('"').strip("'")
                body = "\n".join(lines[idx + 1:])
                break
    return meta, body


def parse_date(value):
    """Parse an ISO date/datetime string into a datetime.date, or None."""
    if not value:
        return None
    value = value.strip()
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        pass
    try:
        return datetime.datetime.fromisoformat(value).date()
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Markdown rendering (hand-written, deliberately small)
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_HR_RE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")
_UL_ITEM_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
_OL_ITEM_RE = re.compile(r"^\s*\d+[.)]\s+(.*)$")
_CODE_SPAN_RE = re.compile(r"(`[^`]+`)")
_IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_BOLD_STAR_RE = re.compile(r"\*\*([^*]+)\*\*")
_BOLD_UNDER_RE = re.compile(r"__([^_]+)__")
_ITALIC_STAR_RE = re.compile(r"\*([^*]+)\*")
_ITALIC_UNDER_RE = re.compile(r"(?<![\w])_([^_]+)_(?![\w])")


def render_inline(text):
    """Render inline Markdown (code, images, links, bold, italic) to HTML.

    Raw HTML in the source is always escaped; only markup generated
    here is emitted.
    """
    out = []
    for part in _CODE_SPAN_RE.split(text):
        if len(part) >= 2 and part.startswith("`") and part.endswith("`"):
            out.append("<code>" + html.escape(part[1:-1]) + "</code>")
            continue
        seg = html.escape(part, quote=True)
        seg = _IMG_RE.sub(r'<img src="\2" alt="\1">', seg)
        seg = _LINK_RE.sub(r'<a href="\2">\1</a>', seg)
        seg = _BOLD_STAR_RE.sub(r"<strong>\1</strong>", seg)
        seg = _BOLD_UNDER_RE.sub(r"<strong>\1</strong>", seg)
        seg = _ITALIC_STAR_RE.sub(r"<em>\1</em>", seg)
        seg = _ITALIC_UNDER_RE.sub(r"<em>\1</em>", seg)
        out.append(seg)
    return "".join(out)


def _is_block_start(line):
    stripped = line.lstrip()
    return bool(
        stripped.startswith("```")
        or _HEADING_RE.match(line)
        or _HR_RE.match(line)
        or stripped.startswith(">")
        or _UL_ITEM_RE.match(line)
        or _OL_ITEM_RE.match(line)
    )


def render_markdown(text):
    """Render a Markdown document body to an HTML fragment."""
    lines = text.split("\n")
    blocks = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        # Fenced code block
        if line.lstrip().startswith("```"):
            code_lines = []
            i += 1
            while i < n and not lines[i].lstrip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # consume closing fence (or run off the end)
            blocks.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
            continue

        # Heading
        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            blocks.append("<h%d>%s</h%d>" % (level, render_inline(m.group(2).strip()), level))
            i += 1
            continue

        # Horizontal rule
        if _HR_RE.match(line):
            blocks.append("<hr>")
            i += 1
            continue

        # Blockquote: consecutive '>' lines, rendered as one paragraph
        if line.lstrip().startswith(">"):
            quote_lines = []
            while i < n and lines[i].lstrip().startswith(">"):
                content = lines[i].lstrip()[1:]
                if content.startswith(" "):
                    content = content[1:]
                quote_lines.append(content)
                i += 1
            blocks.append("<blockquote><p>" + render_inline(" ".join(quote_lines)) + "</p></blockquote>")
            continue

        # Unordered list
        if _UL_ITEM_RE.match(line):
            items = []
            while i < n:
                m = _UL_ITEM_RE.match(lines[i])
                if not m:
                    break
                items.append("<li>" + render_inline(m.group(1).strip()) + "</li>")
                i += 1
            blocks.append("<ul>" + "".join(items) + "</ul>")
            continue

        # Ordered list
        if _OL_ITEM_RE.match(line):
            items = []
            while i < n:
                m = _OL_ITEM_RE.match(lines[i])
                if not m:
                    break
                items.append("<li>" + render_inline(m.group(1).strip()) + "</li>")
                i += 1
            blocks.append("<ol>" + "".join(items) + "</ol>")
            continue

        # Paragraph: gather until a blank line or another block starts
        para_lines = [line.strip()]
        i += 1
        while i < n and lines[i].strip() and not _is_block_start(lines[i]):
            para_lines.append(lines[i].strip())
            i += 1
        blocks.append("<p>" + render_inline(" ".join(para_lines)) + "</p>")

    return "\n".join(blocks)


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

DEFAULT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{title}}</title>
<style>
  body { font-family: Georgia, 'Times New Roman', serif; margin: 0; color: #1c1c1c;
         background: #fdfdfa; line-height: 1.6; }
  header { border-bottom: 3px double #444; padding: 1rem 1.5rem; }
  header nav ul { list-style: none; margin: 0; padding: 0; display: flex; gap: 1rem; flex-wrap: wrap; }
  header nav a { color: #14532d; text-decoration: none; font-weight: bold; }
  header nav a:hover { text-decoration: underline; }
  main { max-width: 44rem; margin: 0 auto; padding: 1.5rem 1rem 3rem; }
  pre { background: #f0efe9; padding: 0.75rem 1rem; overflow-x: auto; border-radius: 4px; }
  code { font-family: 'Courier New', monospace; font-size: 0.92em; }
  blockquote { border-left: 3px solid #888; margin-left: 0; padding-left: 1rem; color: #444; }
  img { max-width: 100%; }
  .post-date { color: #666; font-size: 0.9em; }
  footer { border-top: 1px solid #ccc; padding: 1rem 1.5rem; color: #666; font-size: 0.85em; }
</style>
</head>
<body>
<header><nav>{{nav}}</nav></header>
<main>
{{content}}
</main>
<footer>Built with Reverb Sitegen.</footer>
</body>
</html>
"""


def load_template(content_dir):
    """Use template.html from the content dir if present, else the default."""
    path = os.path.join(content_dir, "template.html")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    return DEFAULT_TEMPLATE


def apply_template(template, title, content, nav):
    return (
        template.replace("{{title}}", html.escape(title))
        .replace("{{nav}}", nav)
        .replace("{{content}}", content)
    )


# ---------------------------------------------------------------------------
# Site building
# ---------------------------------------------------------------------------

def slugify(filename):
    stem = os.path.splitext(os.path.basename(filename))[0]
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return slug or "post"


def pretty_title(slug):
    return slug.replace("-", " ").title()


def first_heading(body):
    for line in body.split("\n"):
        m = _HEADING_RE.match(line)
        if m:
            text = m.group(2).strip()
            text = re.sub(r"[*_`]", "", text)
            return text
    return None


def collect_posts(content_dir):
    """Read every .md file in content_dir into a post dict, newest first."""
    posts = []
    for name in sorted(os.listdir(content_dir)):
        if not name.lower().endswith(".md"):
            continue
        path = os.path.join(content_dir, name)
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()
        meta, body = parse_front_matter(raw)
        slug = slugify(name)
        date = parse_date(meta.get("date", ""))
        posts.append(
            {
                "slug": slug,
                "filename": slug + ".html",
                "title": meta.get("title") or first_heading(body) or pretty_title(slug),
                "date": date,
                "body_html": render_markdown(body),
            }
        )
    # Newest first; undated posts go last, ties broken by slug for stability.
    posts.sort(key=lambda p: (p["date"] is not None, p["date"] or datetime.date.min, p["slug"]),
               reverse=True)
    return posts


def build_nav(posts):
    items = ['<li><a href="index.html">Home</a></li>']
    for post in posts:
        items.append(
            '<li><a href="%s">%s</a></li>'
            % (post["filename"], html.escape(post["title"]))
        )
    return "<ul>" + "".join(items) + "</ul>"


def build_index_content(posts, site_title):
    parts = ["<h1>%s</h1>" % html.escape(site_title)]
    for post in posts:
        date_html = ""
        if post["date"] is not None:
            iso = post["date"].isoformat()
            date_html = ' <span class="post-date"><time datetime="%s">%s</time></span>' % (iso, iso)
        parts.append(
            '<p><a href="%s">%s</a>%s</p>'
            % (post["filename"], html.escape(post["title"]), date_html)
        )
    return "\n".join(parts)


def build_feed(posts, site_title):
    """Build an Atom feed (well-formed XML) with relative entry links."""
    dated = [p["date"] for p in posts if p["date"] is not None]
    updated = max(dated) if dated else datetime.date.today()
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        "<title>%s</title>" % xml_escape(site_title),
        "<id>urn:reverb-sitegen:feed</id>",
        "<updated>%sT00:00:00Z</updated>" % updated.isoformat(),
    ]
    for post in posts:
        entry_date = post["date"] or updated
        lines += [
            "<entry>",
            "<title>%s</title>" % xml_escape(post["title"]),
            '<link href="%s"/>' % xml_escape(post["filename"], {'"': "&quot;"}),
            "<id>urn:reverb-sitegen:%s</id>" % xml_escape(post["slug"]),
            "<updated>%sT00:00:00Z</updated>" % entry_date.isoformat(),
            '<content type="html">%s</content>' % xml_escape(post["body_html"]),
            "</entry>",
        ]
    lines.append("</feed>")
    return "\n".join(lines) + "\n"


def build_sitemap(posts):
    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        "<url><loc>index.html</loc></url>",
    ]
    for post in posts:
        loc = "<url><loc>%s</loc>" % xml_escape(post["filename"])
        if post["date"] is not None:
            loc += "<lastmod>%s</lastmod>" % post["date"].isoformat()
        loc += "</url>"
        lines.append(loc)
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def build(content_dir, output_dir, site_title="My Site"):
    """Build the whole site. Returns the list of post dicts."""
    if not os.path.isdir(content_dir):
        raise SystemExit("content directory not found: %s" % content_dir)
    os.makedirs(output_dir, exist_ok=True)

    template = load_template(content_dir)
    posts = collect_posts(content_dir)
    nav = build_nav(posts)

    for post in posts:
        page = apply_template(template, post["title"], post["body_html"], nav)
        with open(os.path.join(output_dir, post["filename"]), "w", encoding="utf-8") as fh:
            fh.write(page)

    index_page = apply_template(template, site_title, build_index_content(posts, site_title), nav)
    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(index_page)

    with open(os.path.join(output_dir, "feed.xml"), "w", encoding="utf-8") as fh:
        fh.write(build_feed(posts, site_title))

    with open(os.path.join(output_dir, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write(build_sitemap(posts))

    return posts


def serve(output_dir, port):
    import functools
    import http.server

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=output_dir)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    print("Serving %s at http://127.0.0.1:%d/ (Ctrl+C to stop)" % (output_dir, port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="reverb_sitegen",
        description="Reverb Sitegen - a single-file static site generator.",
    )
    parser.add_argument("--version", action="version", version="Reverb Sitegen " + __version__)
    sub = parser.add_subparsers(dest="command", required=True)

    build_parser = sub.add_parser("build", help="build a site from a content directory")
    build_parser.add_argument("content_dir", help="directory of .md files")
    build_parser.add_argument("output_dir", help="where to write the site")
    build_parser.add_argument("--title", default="My Site", help="site title (default: 'My Site')")
    build_parser.add_argument("--serve", action="store_true", help="preview the built site locally")
    build_parser.add_argument("--port", type=int, default=8000, help="preview port (default: 8000)")

    args = parser.parse_args(argv)

    if args.command == "build":
        posts = build(args.content_dir, args.output_dir, site_title=args.title)
        print("Built %d post(s) + index + feed.xml + sitemap.xml into %s" % (len(posts), args.output_dir))
        if args.serve:
            serve(args.output_dir, args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
