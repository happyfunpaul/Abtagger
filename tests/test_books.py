import unittest

import books


def row(name, **kw):
    rec = {"path": (kw.pop("dir", "") + "/" + name).lstrip("/"), "dir": kw.pop("dir", ""),
           "name": name, "title": "", "album": "", "author": "", "error": ""}
    rec.update(kw)
    return rec


class TestTitleBase(unittest.TestCase):
    def test_strips_prefix(self):
        self.assertEqual(books.title_base("01 - The Way of Kings"), "the way of kings")
        self.assertEqual(books.title_base("Chapter 3 - The Way of Kings"), "the way of kings")

    def test_strips_suffix(self):
        self.assertEqual(books.title_base("The Way of Kings - 03"), "the way of kings")
        self.assertEqual(books.title_base("The Way of Kings (Part 2)"), "the way of kings")

    def test_part_only_title_is_empty(self):
        self.assertEqual(books.title_base("Chapter 3"), "")
        self.assertEqual(books.title_base("02"), "")

    def test_hyphenated_number_is_kept(self):
        self.assertEqual(books.title_base("Catch-22"), "catch 22")


class TestGroupDir(unittest.TestCase):
    def test_disc_folders_fold_into_parent(self):
        self.assertEqual(books.group_dir("Author/Book/CD1"), "Author/Book")
        self.assertEqual(books.group_dir("Author/Book/Disc 2"), "Author/Book")
        self.assertEqual(books.group_dir("Author/Book/Part_3"), "Author/Book")

    def test_normal_folder_kept(self):
        self.assertEqual(books.group_dir("Author/Book"), "Author/Book")


class TestBookKey(unittest.TestCase):
    def test_album_groups_chapters(self):
        rows = [
            row("Christmas_Carol_01.mp3", dir="Dickens", title="Preface and Stave 1",
                album="A Christmas Carol", author="Charles Dickens"),
            row("Christmas_Carol_02.mp3", dir="Dickens", title="Stave 2",
                album="A Christmas Carol", author="Charles Dickens"),
        ]
        self.assertEqual(books.book_key(rows[0]), books.book_key(rows[1]))

    def test_disc_folders_share_a_book(self):
        rows = [
            row("01.mp3", dir="Book/CD1", title="Chapter 1", album="Book", author="A"),
            row("01.mp3", dir="Book/Disc 2", title="Chapter 1", album="Book", author="A"),
        ]
        self.assertEqual(books.book_key(rows[0]), books.book_key(rows[1]))

    def test_part_filenames_group_without_album(self):
        rows = [
            row("Book - 01.mp3", dir="A", title="", author="A"),
            row("Book - 02.mp3", dir="A", title="", author="A"),
        ]
        self.assertEqual(books.book_key(rows[0]), books.book_key(rows[1]))

    def test_different_albums_do_not_group(self):
        rows = [
            row("a.mp3", dir="flat", title="A", album="Book A", author="A"),
            row("b.mp3", dir="flat", title="B", album="Book B", author="A"),
        ]
        self.assertNotEqual(books.book_key(rows[0]), books.book_key(rows[1]))

    def test_same_title_and_author_group(self):
        rows = [
            row("a.mp3", dir="A", title="The Book", author="Author"),
            row("b.mp3", dir="A", title="The Book", author="Author"),
        ]
        self.assertEqual(books.book_key(rows[0]), books.book_key(rows[1]))

    def test_unreadable_files_never_group(self):
        rows = [
            row("a.mp3", dir="A", title="x", album="Same", error="boom"),
            row("b.mp3", dir="A", title="x", album="Same", error="boom"),
        ]
        self.assertNotEqual(books.book_key(rows[0]), books.book_key(rows[1]))

    def test_group_rows_skips_errors(self):
        rows = [
            row("a.mp3", title="x", album="Same"),
            row("b.mp3", title="x", album="Same"),
            row("c.mp3", title="x", album="Same", error="boom"),
        ]
        groups = books.group_rows(rows)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(next(iter(groups.values()))), 2)


if __name__ == "__main__":
    unittest.main()
