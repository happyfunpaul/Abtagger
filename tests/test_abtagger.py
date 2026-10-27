import shutil
import tempfile
import unittest
from pathlib import Path

import abtagger


class TestCleanValue(unittest.TestCase):
    def test_unknown_field(self):
        with self.assertRaises(ValueError):
            abtagger.clean_value("nope", "x")

    def test_control_chars(self):
        with self.assertRaises(ValueError):
            abtagger.clean_value("title", "a\x01b")

    def test_year_validation(self):
        self.assertEqual(abtagger.clean_value("year", "2004"), "2004")
        with self.assertRaises(ValueError):
            abtagger.clean_value("year", "2004-9")

    def test_series_num(self):
        self.assertEqual(abtagger.clean_value("series_num", "1.5"), "1.5")
        with self.assertRaises(ValueError):
            abtagger.clean_value("series_num", "abc")

    def test_strip(self):
        self.assertEqual(abtagger.clean_value("title", "  hi  "), "hi")

    def test_restore_skips_validation(self):
        # strict=False should not validate year format
        self.assertEqual(abtagger.clean_value("year", "bad", strict=False), "bad")


class TestLocate(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.root = self.d / "lib"
        self.root.mkdir()
        (self.root / "a.mp3").write_bytes(b"")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_ok(self):
        p = abtagger.locate(self.root, "a.mp3")
        self.assertEqual(p.name, "a.mp3")

    def test_traversal(self):
        with self.assertRaises(ValueError):
            abtagger.locate(self.root, "../x.mp3")
        with self.assertRaises(ValueError):
            abtagger.locate(self.root, "sub/../../x.mp3")

    def test_bad_suffix(self):
        (self.root / "x.txt").write_text("hi")
        with self.assertRaises(ValueError):
            abtagger.locate(self.root, "x.txt")

    def test_missing(self):
        with self.assertRaises(ValueError):
            abtagger.locate(self.root, "nope.mp3")


class TestRoundTrip(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.root = self.d / "lib"
        self.root.mkdir()
        # copy sample audio files from testdata if present
        src = Path(__file__).resolve().parents[1] / "testdata"
        self.has_mp3 = (src / "Gift_of_the_Magi.mp3").is_file()
        self.has_m4a = (src / "ding.m4a").is_file()
        if self.has_mp3:
            shutil.copy(src / "Gift_of_the_Magi.mp3", self.root / "book.mp3")
        if self.has_m4a:
            shutil.copy(src / "ding.m4a", self.root / "book.m4a")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_mp3_roundtrip(self):
        if not self.has_mp3:
            self.skipTest("no sample mp3")
        import abtagger
        st = abtagger.State(self.root, "tok", self.d / "state", False, True)
        abtagger._set_state(st)
        rec = abtagger.read_record(self.root / "book.mp3", self.root)
        self.assertEqual(rec["error"], "")
        # write
        item = {"path": "book.mp3", "changes": {"title": {"old": rec["title"], "new": "RT Track"},
                                                "subtitle": {"old": rec["subtitle"], "new": "RT Subtitle"},
                                                "album": {"old": rec["album"], "new": "RT Book"},
                                                "author": {"old": rec["author"], "new": "RT Author"}}}
        new, entry = abtagger.apply_changes(item)
        self.assertEqual(new["title"], "RT Track")
        self.assertEqual(new["subtitle"], "RT Subtitle")
        self.assertEqual(new["album"], "RT Book")
        self.assertEqual(new["author"], "RT Author")
        # read back
        rec2 = abtagger.read_record(self.root / "book.mp3", self.root)
        self.assertEqual(rec2["title"], "RT Track")
        self.assertEqual(rec2["subtitle"], "RT Subtitle")
        self.assertEqual(rec2["album"], "RT Book")
        self.assertEqual(rec2["author"], "RT Author")

    def test_m4a_audible_title_and_subtitle(self):
        if not self.has_m4a:
            self.skipTest("no sample m4a")
        from mutagen.mp4 import AtomDataType, MP4, MP4FreeForm
        from tags import TONE
        p = self.root / "book.m4a"
        f = MP4(str(p))
        if f.tags is None:
            f.add_tags()
        f.tags["\xa9alb"] = ["Dark Tower I"]
        f.tags["\xa9nam"] = ["Dark Tower I"]
        f.tags["@sti"] = ["Dark Tower I (Unabridged)"]
        f.tags[TONE + "SUBTITLE"] = [MP4FreeForm(b"The Gunslinger", dataformat=AtomDataType.UTF8)]
        f.save()
        rec = abtagger.read_record(p, self.root)
        self.assertEqual(rec["album"], "Dark Tower I (Unabridged)")
        self.assertEqual(rec["subtitle"], "The Gunslinger")
        self.assertEqual(rec["title"], "Dark Tower I")

        st = abtagger.State(self.root, "tok", self.d / "state", False, True)
        abtagger._set_state(st)
        item = {"path": "book.m4a", "changes": {
            "album": {"old": rec["album"], "new": "Dark Tower I (Revised)"},
            "subtitle": {"old": rec["subtitle"], "new": "The Revised Gunslinger"},
        }}
        new, entry = abtagger.apply_changes(item)
        self.assertEqual(new["album"], "Dark Tower I (Revised)")
        self.assertEqual(new["subtitle"], "The Revised Gunslinger")

        f2 = MP4(str(p))
        self.assertEqual(f2.tags["@sti"], ["Dark Tower I (Revised)"])
        tone = bytes(f2.tags[TONE + "SUBTITLE"][0]).decode("utf-8")
        self.assertEqual(tone, "The Revised Gunslinger")

    def test_m4a_roundtrip(self):
        if not self.has_m4a:
            self.skipTest("no sample m4a")
        import abtagger
        st = abtagger.State(self.root, "tok", self.d / "state", False, True)
        abtagger._set_state(st)
        rec = abtagger.read_record(self.root / "book.m4a", self.root)
        self.assertEqual(rec["error"], "")
        item = {"path": "book.m4a", "changes": {"title": {"old": rec["title"], "new": "RT Track"},
                                                "subtitle": {"old": rec["subtitle"], "new": "RT Subtitle"},
                                                "album": {"old": rec["album"], "new": "RT Book"},
                                                "series": {"old": rec["series"], "new": "RT Series"},
                                                "series_num": {"old": rec["series_num"], "new": "3.5"}}}
        new, entry = abtagger.apply_changes(item)
        self.assertEqual(new["title"], "RT Track")
        self.assertEqual(new["subtitle"], "RT Subtitle")
        self.assertEqual(new["album"], "RT Book")
        self.assertEqual(new["series"], "RT Series")
        self.assertEqual(new["series_num"], "3.5")
        rec2 = abtagger.read_record(self.root / "book.m4a", self.root)
        self.assertEqual(rec2["subtitle"], "RT Subtitle")
        self.assertEqual(rec2["album"], "RT Book")
        self.assertEqual(rec2["series"], "RT Series")


if __name__ == "__main__":
    unittest.main()