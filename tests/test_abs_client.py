import unittest
from pathlib import Path
from unittest.mock import patch

from abs_client import AbsClient, AbsConfig


class FakeResponse:
    status = 200

    def __init__(self, body: bytes, content_type: str):
        self._body = body
        self.headers = {"Content-Type": content_type}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class TestFindLibraryForRoot(unittest.TestCase):
    def test_find_library_for_root(self):
        two_libs = [
            {"id": "a", "folders": [{"fullPath": "/audiobooks"}]},
            {"id": "b", "folders": [{"fullPath": "/other"}]},
        ]
        cases = [
            ("matches by path", two_libs, Path("/audiobooks"), "a"),
            ("does not guess with multiple libs", two_libs, Path(r"D:\Library"), None),
            ("single-library Docker fallback", [{"id": "a", "folders": [{"fullPath": "/audiobooks"}]}],
             Path(r"D:\Library"), "a"),
            ("single library without id", [{"folders": []}], Path(r"D:\Library"), None),
        ]
        for name, libs, root, expected in cases:
            with self.subTest(name=name):
                client = AbsClient(AbsConfig(url="http://example", token="token"))
                client.get_libraries = lambda: libs
                self.assertEqual(client.find_library_for_root(root), expected)


class TestRequestBodies(unittest.TestCase):
    def client(self):
        return AbsClient(AbsConfig(url="http://example", token="token"))

    @patch("abs_client.urllib.request.urlopen")
    def test_scan_accepts_plain_text_ok(self, urlopen):
        urlopen.return_value = FakeResponse(b"OK", "text/plain; charset=utf-8")
        self.assertEqual(self.client().scan_library("lib"), {"ok": True, "body": "OK"})

    @patch("abs_client.urllib.request.urlopen")
    def test_json_endpoints_still_parse(self, urlopen):
        urlopen.return_value = FakeResponse(b'{"libraries": []}', "application/json")
        self.assertEqual(self.client().get_libraries(), [])

    @patch("abs_client.urllib.request.urlopen")
    def test_bad_json_has_a_clear_error(self, urlopen):
        urlopen.return_value = FakeResponse(b"<html>login</html>", "text/html")
        with self.assertRaisesRegex(RuntimeError, "non-JSON"):
            self.client().get_libraries()


if __name__ == "__main__":
    unittest.main()
