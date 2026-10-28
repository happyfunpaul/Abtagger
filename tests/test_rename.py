import unittest
from pathlib import Path

import rename


class TestSplitAuthor(unittest.TestCase):
    def test_split_author(self):
        cases = [
            ("Tolkien, J.R.R.", ("Tolkien", "J.R.R.")),
            ("Brandon Sanderson", ("Sanderson", "Brandon")),
            ("Madonna", ("Madonna", "")),
            ("", ("", "")),
        ]
        for author, expected in cases:
            with self.subTest(author=author):
                self.assertEqual(rename.split_author(author), expected)


class TestRenderTemplate(unittest.TestCase):
    def rec(self, **kw):
        base = {"title": "The Way of Kings", "author": "Brandon Sanderson",
                "series": "Stormlight Archive", "series_num": "1",
                "year": "2010", "duration": 3600}
        base.update(kw)
        return base

    def test_series_and_standalone(self):
        template = "{author_last}, {author_first}/[{series}/][{series_num} - ]{title}"
        cases = [
            ({}, "Sanderson, Brandon/Stormlight Archive/1 - The Way of Kings"),
            ({"series": "", "series_num": ""}, "Sanderson, Brandon/The Way of Kings"),
        ]
        for overrides, expected in cases:
            with self.subTest(overrides=overrides):
                self.assertEqual(
                    rename.render_template(template, self.rec(**overrides), "book.m4b"),
                    expected,
                )

    def test_ext_preserved_by_plan(self):
        row = self.rec(path="x.m4b", name="x.m4b")
        plans = rename.build_rename_plan(Path("/tmp"), [row], "{title}")
        self.assertEqual(plans[0].dst, "The Way of Kings.m4b")

    def test_sanitize(self):
        out = rename.render_template("{title}", {"title": "a/b:c*"}, "x.m4b")
        self.assertNotIn(":", out)
        self.assertNotIn("*", out)

    def test_title_placeholders(self):
        rec = self.rec(title="Chapter 1", album="The Book", subtitle="A Subtitle")
        self.assertEqual(rename.render_template("{title}", rec, "x.m4b"), "The Book")
        self.assertEqual(rename.render_template("{track_title}", rec, "x.m4b"), "Chapter 1")
        self.assertEqual(rename.render_template("{subtitle}", rec, "x.m4b"), "A Subtitle")

    def test_group_rename(self):
        rows = [
            {"path": "Book/a.m4a", "dir": "Book", "name": "a.m4a",
             "title": "Foo", "album": "Foo", "author": "Bar",
             "series": "", "series_num": "", "duration": 100, "error": ""},
            {"path": "Book/b.m4a", "dir": "Book", "name": "b.m4a",
             "title": "Foo", "album": "Foo", "author": "Bar",
             "series": "", "series_num": "", "duration": 100, "error": ""},
        ]
        plans = rename.build_rename_plan(Path("/tmp"), rows, "Book/{title}", selected={"Book/a.m4a"}, group_books=True)
        self.assertEqual(len(plans), 2)
        self.assertTrue(all("Foo" in p.dst for p in plans))


class TestPartNumbering(unittest.TestCase):
    def row(self, path, **kw):
        rec = {"path": path, "dir": path.rsplit("/", 1)[0] if "/" in path else "",
               "name": path.rsplit("/", 1)[-1], "title": "", "album": "The Book",
               "author": "A", "series": "", "series_num": "", "duration": 1, "error": ""}
        rec.update(kw)
        return rec

    def test_parts_are_numbered(self):
        cases = [
            (
                "same destination gets part numbers",
                [
                    self.row("Book/The Book.m4b", title="The Book Part 1"),
                    self.row("Book/The Book (2).m4b", title="The Book Part 2"),
                    self.row("Book/The Book (3).m4b", title="The Book Part 3"),
                ],
                "Author/{title}/{title}",
                sorted([
                    "Author/The Book/The Book - 1.m4b",
                    "Author/The Book/The Book - 2.m4b",
                    "Author/The Book/The Book - 3.m4b",
                ]),
            ),
            (
                "distinct books in one folder get no suffix",
                [
                    self.row("Series/Book A.m4b", album="Book A", title="Book A"),
                    self.row("Series/Book B.m4b", album="Book B", title="Book B"),
                    self.row("Series/Book C.m4b", album="Book C", title="Book C"),
                ],
                "Author/Series/{title}/{title}",
                sorted([
                    "Author/Series/Book A/Book A.m4b",
                    "Author/Series/Book B/Book B.m4b",
                    "Author/Series/Book C/Book C.m4b",
                ]),
            ),
            (
                "part number comes from title/parenthetical",
                [
                    self.row("Book/Title.m4b", title="Title Part 1"),
                    self.row("Book/Title (2).m4b", title="Title Part 2"),
                ],
                "{title}/{title}",
                sorted([
                    "The Book/The Book - 1.m4b",
                    "The Book/The Book - 2.m4b",
                ]),
            ),
        ]
        for name, rows, template, expected in cases:
            with self.subTest(name=name):
                plans = rename.build_rename_plan(Path("/tmp"), rows, template)
                self.assertEqual(sorted(p.dst for p in plans), expected)

    def test_already_in_place_is_a_noop(self):
        cases = [
            [self.row("The Book/The Book.m4b", title="The Book")],
            [self.row(f"The Book/The Book - {i}.m4b", title=f"The Book, Part {i}") for i in (1, 2, 3)],
        ]
        for rows in cases:
            with self.subTest(paths=[r["path"] for r in rows]):
                self.assertEqual(rename.build_rename_plan(Path("/tmp"), rows, "{title}/{title}"), [])

    def test_plan_order_is_deterministic(self):
        rows = [
            self.row("Book/b.m4b", album="B", title="B"),
            self.row("Book/a.m4b", album="A", title="A"),
        ]
        first = [p.dst for p in rename.build_rename_plan(Path("/tmp"), rows, "{title}")]
        second = [p.dst for p in rename.build_rename_plan(Path("/tmp"), list(reversed(rows)), "{title}")]
        self.assertEqual(first, second)


class TestNormalizeTitle(unittest.TestCase):
    def test_normalize_title(self):
        cases = [
            ("Foo (Unabridged)", "foo"),
            ("Hello, World!", "hello world"),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(rename.normalize_title(text), expected)


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
