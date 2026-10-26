import unittest

import rename


class TestSplitAuthor(unittest.TestCase):
    def test_comma(self):
        self.assertEqual(rename.split_author("Tolkien, J.R.R."), ("Tolkien", "J.R.R."))
    def test_space(self):
        self.assertEqual(rename.split_author("Brandon Sanderson"), ("Sanderson", "Brandon"))
    def test_single(self):
        self.assertEqual(rename.split_author("Madonna"), ("Madonna", ""))
    def test_empty(self):
        self.assertEqual(rename.split_author(""), ("", ""))


class TestRenderTemplate(unittest.TestCase):
    def rec(self, **kw):
        base = {"title": "The Way of Kings", "author": "Brandon Sanderson", "series": "Stormlight Archive", "series_num": "1", "year": "2010", "duration": 3600}
        base.update(kw)
        return base

    def test_basic_with_series(self):
        t = "{author_last}, {author_first}/[{series}/][{series_num} - ]{title}"
        out = rename.render_template(t, self.rec(), "book.m4b")
        self.assertEqual(out, "Sanderson, Brandon/Stormlight Archive/1 - The Way of Kings")

    def test_standalone_skips_series(self):
        t = "{author_last}, {author_first}/[{series}/][{series_num} - ]{title}"
        out = rename.render_template(t, self.rec(series="", series_num=""), "book.m4b")
        self.assertEqual(out, "Sanderson, Brandon/The Way of Kings")

    def test_ext_preserved_by_plan(self):
        plans = rename.build_rename_plan(__import__("pathlib").Path("/tmp"), [self.rec(path="x.m4b", name="x.m4b")], "{title}")
        self.assertEqual(plans[0].dst, "The Way of Kings.m4b")

    def test_sanitize(self):
        out = rename.render_template("{title}", {"title": "a/b:c*"}, "x.m4b")
        self.assertNotIn(":", out)
        self.assertNotIn("*", out)

    def test_builtin_list(self):
        self.assertTrue(len(rename.BUILTIN_TEMPLATES) >= 4)


class TestNormalizeTitle(unittest.TestCase):
    def test_suffix(self):
        self.assertEqual(rename.normalize_title("Foo (Unabridged)"), "foo")
    def test_punct(self):
        self.assertEqual(rename.normalize_title("Hello, World!"), "hello world")


class TestDuplicates(unittest.TestCase):
    def test_finds_dup(self):
        rows = [
            {"path": "a.mp3", "title": "Foo", "author": "Bar", "series": "", "series_num": "", "duration": 100, "error": ""},
            {"path": "b.mp3", "title": "Foo", "author": "Bar", "series": "", "series_num": "", "duration": 105, "error": ""},
            {"path": "c.mp3", "title": "Other", "author": "Baz", "series": "", "series_num": "", "duration": 50, "error": ""},
        ]
        groups = rename.find_duplicates(rows)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 2)


if __name__ == "__main__":
    unittest.main()