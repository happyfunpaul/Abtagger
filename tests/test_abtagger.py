import shutil
import tempfile
import unittest
from pathlib import Path

import abtagger
import settings


class TestCleanValue(unittest.TestCase):
    def test_clean_value(self):
        cases = [
            ("year", "2004", "2004"),
            ("year", "2004-03-15", "2004-03-15"),
            ("year", "2004-9", ValueError),
            ("series_num", "1.5", "1.5"),
            ("series_num", "abc", ValueError),
            ("title", "  hi  ", "hi"),
            ("title", "a\x01b", ValueError),
            ("nope", "x", ValueError),
        ]
        for field, value, expected in cases:
            with self.subTest(field=field, value=value):
                if expected is ValueError:
                    with self.assertRaises(ValueError):
                        abtagger.clean_value(field, value)
                else:
                    self.assertEqual(abtagger.clean_value(field, value), expected)

    def test_restore_skips_validation(self):
        self.assertEqual(abtagger.clean_value("year", "bad", strict=False), "bad")


class TestLocate(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.root = self.d / "lib"
        self.root.mkdir()
        (self.root / "a.mp3").write_bytes(b"")
        (self.root / "x.txt").write_text("hi")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_resolves_safe_path(self):
        self.assertEqual(abtagger.locate(self.root, "a.mp3").name, "a.mp3")

    def test_rejects_bad_paths(self):
        for rel in ("../x.mp3", "sub/../../x.mp3", "x.txt", "nope.mp3"):
            with self.subTest(rel=rel):
                with self.assertRaises(ValueError):
                    abtagger.locate(self.root, rel)


class TestAbsConfigRefresh(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.root = self.d / "lib"
        self.root.mkdir()
        self._old_config = settings.CONFIG_PATH
        settings.CONFIG_PATH = self.d / "config.json"
        st = abtagger.State(self.root, "tok", self.d / "state", False, True)
        abtagger._set_state(st)

    def tearDown(self):
        settings.CONFIG_PATH = self._old_config
        shutil.rmtree(self.d, ignore_errors=True)

    def test_settings_save_refreshes_client(self):
        abtagger.do_settings_save({"abs_url": "http://example", "abs_token": "tok"})
        self.assertIsNotNone(abtagger._state().abs_client)
        abtagger.do_settings_save({"abs_url": "", "abs_token": ""})
        self.assertIsNone(abtagger._state().abs_client)


class TestRoundTrip(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.root = self.d / "lib"
        self.root.mkdir()
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
        st = abtagger.State(self.root, "tok", self.d / "state", False, True)
        abtagger._set_state(st)
        rec = abtagger.read_record(self.root / "book.mp3", self.root)
        self.assertEqual(rec["error"], "")
        item = {"path": "book.mp3", "changes": {
            "title": {"old": rec["title"], "new": "RT Track"},
            "subtitle": {"old": rec["subtitle"], "new": "RT Subtitle"},
            "album": {"old": rec["album"], "new": "RT Book"},
            "author": {"old": rec["author"], "new": "RT Author"},
        }}
        new, _ = abtagger.apply_changes(item)
        self.assertEqual(new["title"], "RT Track")
        self.assertEqual(new["subtitle"], "RT Subtitle")
        self.assertEqual(new["album"], "RT Book")
        self.assertEqual(new["author"], "RT Author")
        rec2 = abtagger.read_record(self.root / "book.mp3", self.root)
        self.assertEqual(rec2["title"], "RT Track")
        self.assertEqual(rec2["subtitle"], "RT Subtitle")
        self.assertEqual(rec2["album"], "RT Book")
        self.assertEqual(rec2["author"], "RT Author")

    def test_mp3_album_falls_back_to_title(self):
        if not self.has_mp3:
            self.skipTest("no sample mp3")
        from mutagen.id3 import ID3, TIT2
        p = self.root / "book.mp3"
        t = ID3(str(p))
        t.delall("TALB")
        t.delall("TIT2")
        t.add(TIT2(encoding=3, text=["Only A Title"]))
        t.save(str(p))
        rec = abtagger.read_record(p, self.root)
        self.assertEqual(rec["album"], "Only A Title")  # what ABS displays
        self.assertEqual(rec["title"], "Only A Title")

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
        new, _ = abtagger.apply_changes(item)
        self.assertEqual(new["album"], "Dark Tower I (Revised)")
        self.assertEqual(new["subtitle"], "The Revised Gunslinger")

        f2 = MP4(str(p))
        self.assertEqual(f2.tags["@sti"], ["Dark Tower I (Revised)"])
        tone = bytes(f2.tags[TONE + "SUBTITLE"][0]).decode("utf-8")
        self.assertEqual(tone, "The Revised Gunslinger")

    def test_m4a_audible_srnm_srsq(self):
        if not self.has_m4a:
            self.skipTest("no sample m4a")
        from mutagen.mp4 import MP4
        p = self.root / "book.m4a"
        f = MP4(str(p))
        if f.tags is None:
            f.add_tags()
        f.tags["SRNM"] = ["Dungeon Crawler Carl"]
        f.tags["SRSQ"] = ["7"]
        f.save()
        rec = abtagger.read_record(p, self.root)
        self.assertEqual(rec["series"], "Dungeon Crawler Carl")
        self.assertEqual(rec["series_num"], "7")

        st = abtagger.State(self.root, "tok", self.d / "state", False, True)
        abtagger._set_state(st)
        item = {"path": "book.m4a", "changes": {
            "series": {"old": rec["series"], "new": "DCC"},
            "series_num": {"old": rec["series_num"], "new": "8"},
        }}
        abtagger.apply_changes(item)
        f2 = MP4(str(p))
        self.assertEqual(f2.tags["SRNM"], ["DCC"])
        self.assertEqual(f2.tags["SRSQ"], ["8"])

    def test_m4a_roundtrip(self):
        if not self.has_m4a:
            self.skipTest("no sample m4a")
        st = abtagger.State(self.root, "tok", self.d / "state", False, True)
        abtagger._set_state(st)
        rec = abtagger.read_record(self.root / "book.m4a", self.root)
        self.assertEqual(rec["error"], "")
        item = {"path": "book.m4a", "changes": {
            "title": {"old": rec["title"], "new": "RT Track"},
            "subtitle": {"old": rec["subtitle"], "new": "RT Subtitle"},
            "album": {"old": rec["album"], "new": "RT Book"},
            "series": {"old": rec["series"], "new": "RT Series"},
            "series_num": {"old": rec["series_num"], "new": "3.5"},
        }}
        new, _ = abtagger.apply_changes(item)
        self.assertEqual(new["title"], "RT Track")
        self.assertEqual(new["subtitle"], "RT Subtitle")
        self.assertEqual(new["album"], "RT Book")
        self.assertEqual(new["series"], "RT Series")
        self.assertEqual(new["series_num"], "3.5")
        rec2 = abtagger.read_record(self.root / "book.m4a", self.root)
        self.assertEqual(rec2["subtitle"], "RT Subtitle")
        self.assertEqual(rec2["album"], "RT Book")
        self.assertEqual(rec2["series"], "RT Series")


class TestCover(unittest.TestCase):
    src = Path(__file__).resolve().parents[1] / "testdata"

    def test_m4b_cover(self):
        p = self.src / "The_Raven.m4b"
        if not p.is_file():
            self.skipTest("no sample m4b")
        cover = abtagger.read_cover(p)
        self.assertIsNotNone(cover)
        data, mime = cover
        self.assertTrue(data)
        self.assertEqual(mime, "image/jpeg")
        self.assertTrue(data.startswith(b"\xff\xd8\xff"))

    def test_mp3_without_cover(self):
        p = self.src / "A_Modest_Proposal.mp3"
        if not p.is_file():
            self.skipTest("no sample mp3")
        self.assertIsNone(abtagger.read_cover(p))

    def test_sniff_image_mime(self):
        cases = [
            (b"\x89PNG\r\n\x1a\nxxxx", "image/png"),
            (b"\xff\xd8\xff\xe0", "image/jpeg"),
            (b"not an image", "application/octet-stream"),
        ]
        for data, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(abtagger.sniff_image_mime(data), expected)


if __name__ == "__main__":
    unittest.main()
