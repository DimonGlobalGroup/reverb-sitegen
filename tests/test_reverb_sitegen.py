"""Tests for Reverb Sitegen. Run from the package root:

    python3 -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import reverb_sitegen as rs


class TestInline(unittest.TestCase):
    def test_bold_and_italic(self):
        self.assertEqual(rs.render_inline("a **bold** word"), "a <strong>bold</strong> word")
        self.assertEqual(rs.render_inline("an *italic* word"), "an <em>italic</em> word")
        self.assertEqual(rs.render_inline("an _italic_ word"), "an <em>italic</em> word")

    def test_link_and_image(self):
        self.assertEqual(
            rs.render_inline("see [Example](https://example.com)"),
            'see <a href="https://example.com">Example</a>',
        )
        self.assertEqual(
            rs.render_inline("![Alt text](pic.png)"),
            '<img src="pic.png" alt="Alt text">',
        )

    def test_code_span(self):
        self.assertEqual(rs.render_inline("run `make test` now"), "run <code>make test</code> now")

    def test_code_span_protects_markup(self):
        self.assertEqual(rs.render_inline("`**not bold**`"), "<code>**not bold**</code>")

    def test_html_is_escaped(self):
        self.assertEqual(
            rs.render_inline("<script>alert(1)</script>"),
            "&lt;script&gt;alert(1)&lt;/script&gt;",
        )


class TestBlocks(unittest.TestCase):
    def test_headings(self):
        self.assertEqual(rs.render_markdown("# Top"), "<h1>Top</h1>")
        self.assertEqual(rs.render_markdown("### Deep"), "<h3>Deep</h3>")

    def test_paragraph(self):
        self.assertEqual(rs.render_markdown("Hello world."), "<p>Hello world.</p>")

    def test_unordered_list(self):
        out = rs.render_markdown("- one\n- two")
        self.assertEqual(out, "<ul><li>one</li><li>two</li></ul>")

    def test_ordered_list(self):
        out = rs.render_markdown("1. first\n2. second")
        self.assertEqual(out, "<ol><li>first</li><li>second</li></ol>")

    def test_code_block_escapes_html(self):
        out = rs.render_markdown("```\n<b>not bold</b>\n```")
        self.assertEqual(out, "<pre><code>&lt;b&gt;not bold&lt;/b&gt;</code></pre>")

    def test_blockquote(self):
        out = rs.render_markdown("> wise words")
        self.assertEqual(out, "<blockquote><p>wise words</p></blockquote>")

    def test_mixed_document(self):
        out = rs.render_markdown("# Title\n\nSome **text**.\n\n- a\n- b")
        self.assertIn("<h1>Title</h1>", out)
        self.assertIn("<p>Some <strong>text</strong>.</p>", out)
        self.assertIn("<ul><li>a</li><li>b</li></ul>", out)


class TestFrontMatter(unittest.TestCase):
    def test_parses_title_and_date(self):
        meta, body = rs.parse_front_matter("---\ntitle: Hello\ndate: 2026-01-15\n---\nBody here.")
        self.assertEqual(meta["title"], "Hello")
        self.assertEqual(meta["date"], "2026-01-15")
        self.assertEqual(body, "Body here.")

    def test_no_front_matter(self):
        meta, body = rs.parse_front_matter("# Just a heading\n\nText.")
        self.assertEqual(meta, {})
        self.assertEqual(body, "# Just a heading\n\nText.")

    def test_parse_date(self):
        import datetime

        self.assertEqual(rs.parse_date("2026-01-15"), datetime.date(2026, 1, 15))
        self.assertIsNone(rs.parse_date("not a date"))
        self.assertIsNone(rs.parse_date(""))


FIXTURES = {
    "first-post.md": "---\ntitle: First Post\ndate: 2026-01-05\n---\n\n# First Post\n\nThe **earliest** entry.\n",
    "second-post.md": "---\ntitle: Second Post\ndate: 2026-02-10\n---\n\n# Second Post\n\nA [link](https://example.com) inside.\n",
    "third-post.md": "---\ntitle: Third Post\ndate: 2026-03-20\n---\n\n# Third Post\n\n- newest\n- post\n",
}

TEMPLATE = (
    "<html><head><title>{{title}}</title></head>"
    "<body><nav>{{nav}}</nav><main>{{content}}</main></body></html>"
)


class TestBuildEndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.content = os.path.join(self.tmp.name, "content")
        self.output = os.path.join(self.tmp.name, "site")
        os.makedirs(self.content)
        for name, text in FIXTURES.items():
            with open(os.path.join(self.content, name), "w", encoding="utf-8") as fh:
                fh.write(text)

    def test_full_build_with_custom_template(self):
        with open(os.path.join(self.content, "template.html"), "w", encoding="utf-8") as fh:
            fh.write(TEMPLATE)

        posts = rs.build(self.content, self.output, site_title="Fixture Site")
        self.assertEqual(len(posts), 3)

        for expected in ("index.html", "feed.xml", "sitemap.xml",
                         "first-post.html", "second-post.html", "third-post.html"):
            self.assertTrue(os.path.isfile(os.path.join(self.output, expected)), expected)

        with open(os.path.join(self.output, "index.html"), encoding="utf-8") as fh:
            index = fh.read()
        # All titles present, newest first.
        for title in ("First Post", "Second Post", "Third Post"):
            self.assertIn(title, index)
        self.assertLess(index.index("Third Post"), index.index("Second Post"))
        self.assertLess(index.index("Second Post"), index.index("First Post"))
        # Relative links.
        self.assertIn('href="third-post.html"', index)

        # Feed is valid XML and carries every title.
        feed_path = os.path.join(self.output, "feed.xml")
        with open(feed_path, encoding="utf-8") as fh:
            feed_text = fh.read()
        ET.parse(feed_path)
        for title in ("First Post", "Second Post", "Third Post"):
            self.assertIn(title, feed_text)

        # Sitemap is valid XML and lists every page.
        sitemap_path = os.path.join(self.output, "sitemap.xml")
        with open(sitemap_path, encoding="utf-8") as fh:
            sitemap_text = fh.read()
        ET.parse(sitemap_path)
        for page in ("index.html", "first-post.html", "second-post.html", "third-post.html"):
            self.assertIn(page, sitemap_text)

        # A post page renders Markdown and the nav.
        with open(os.path.join(self.output, "first-post.html"), encoding="utf-8") as fh:
            post_page = fh.read()
        self.assertIn("<strong>earliest</strong>", post_page)
        self.assertIn('href="index.html"', post_page)

    def test_build_without_template_uses_default(self):
        rs.build(self.content, self.output, site_title="Fixture Site")
        with open(os.path.join(self.output, "index.html"), encoding="utf-8") as fh:
            index = fh.read()
        self.assertIn("<!DOCTYPE html>", index)
        self.assertIn("Fixture Site", index)

    def test_cli_build(self):
        out_dir = os.path.join(self.tmp.name, "cli-site")
        rc = rs.main(["build", self.content, out_dir, "--title", "CLI Site"])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(os.path.join(out_dir, "index.html")))


if __name__ == "__main__":
    unittest.main()
