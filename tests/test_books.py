import unittest

import books


def row(name, **kw):
    d = kw.pop("dir", "")
    rec = {"path": (d + "/" + name).lstrip("/"), "dir": d,
           "name": name, "title": "", "album": "", "author": "", "error": ""}
    rec.update(kw)
    return rec


class TestTitleBase(unittest.TestCase):
    def test_title_base(self):
        cases = [
            ("01 - The Way of Kings", "the way of kings"),
            ("Chapter 3 - The Way of Kings", "the way of kings"),
            ("The Way of Kings - 03", "the way of kings"),
            ("The Way of Kings (Part 2)", "the way of kings"),
            ("Chapter 3", ""),
            ("02", ""),
            ("Catch-22", "catch 22"),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(books.title_base(text), expected)


class TestGroupDir(unittest.TestCase):
    def test_group_dir(self):
        cases = [
            # ABS folds CD/Disc folders into their parent...
            ("Author/Book/CD1", "Author/Book"),
            ("Author/Book/Disc 2", "Author/Book"),
            ("Author/Book/disk 10", "Author/Book"),
            # ...but other subfolders are their own library items.
            ("Author/Book/Part_3", "Author/Book/Part_3"),
            ("Author/Book/Volume 2", "Author/Book/Volume 2"),
            ("Author/Book", "Author/Book"),
        ]
        for rel_dir, expected in cases:
            with self.subTest(rel_dir=rel_dir):
                self.assertEqual(books.group_dir(rel_dir), expected)


class TestBookKey(unittest.TestCase):
    def test_folder_identity(self):
        cases = [
            ("same folder ignores tags", [
                row("a.mp3", dir="Author/Book", title="Chapter 1", album="Book", author="A"),
                row("b.mp3", dir="Author/Book", title="Chapter 2", album="Different", author="B"),
            ], True),
            ("loose root files are separate books", [
                row("a.m4b", title="Book A", album="Book A", author="A"),
                row("b.m4b", title="Book B", album="Book B", author="A"),
            ], False),
            ("different folders are separate books", [
                row("a.m4b", dir="Author/Book A", title="A", album="Same", author="A"),
                row("b.m4b", dir="Author/Book B", title="B", album="Same", author="A"),
            ], False),
            ("disc folders share a book", [
                row("01.mp3", dir="Book/CD1", title="Chapter 1", album="Book", author="A"),
                row("01.mp3", dir="Book/Disc 2", title="Chapter 1", album="Book", author="A"),
            ], True),
        ]
        for name, rows, same in cases:
            with self.subTest(name=name):
                left, right = books.book_key(rows[0]), books.book_key(rows[1])
                if same:
                    self.assertEqual(left, right)
                else:
                    self.assertNotEqual(left, right)

    def test_errors_never_group(self):
        errors = [
            row("a.mp3", dir="A", title="x", album="Same", error="boom"),
            row("b.mp3", dir="A", title="x", album="Same", error="boom"),
        ]
        self.assertNotEqual(books.book_key(errors[0]), books.book_key(errors[1]))

        rows = [
            row("a.mp3", dir="A", title="x", album="Same"),
            row("b.mp3", dir="A", title="y", album="Other"),
            row("c.mp3", dir="A", title="x", album="Same", error="boom"),
        ]
        groups = books.group_rows(rows)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(next(iter(groups.values()))), 2)


if __name__ == "__main__":
    unittest.main()
