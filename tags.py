"""Tag reading/writing backends for audiobook metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

try:
    from mutagen.id3 import (ID3, ID3NoHeaderError, MVIN, MVNM, TALB, TCOM,
                             TCON, TDRC, TIT2, TIT3, TPE1, TXXX)
    from mutagen.mp3 import MP3
    from mutagen.mp4 import MP4, AtomDataType, MP4Cover, MP4FreeForm
except ImportError:  # pragma: no cover
    raise

FIELDS_BASE = None

ITUNES = "----:com.apple.iTunes:"
TONE = "----:com.pilabor.tone:"
YEAR_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
NUM_RE = re.compile(r"^\d+(\.\d+)?$")


@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    max_len: int = 1000
    validator: Callable[[str], str] | None = None


def _v_year(v: str) -> str:
    return "" if not v or YEAR_RE.match(v) else "year must look like 2004 or 2004-03-15"


def _v_series_num(v: str) -> str:
    return "" if not v or NUM_RE.match(v) else "series number must be a number such as 2 or 1.5"


FIELD_SPECS: tuple[FieldSpec, ...] = (
    # ABS maps `album` (fallback `title`) to its Title, and `subtitle` to its
    # Subtitle. The raw `title` tag is the per-file track/chapter title.
    FieldSpec("album", "Title"),
    FieldSpec("subtitle", "Subtitle"),
    FieldSpec("title", "Track title"),
    FieldSpec("author", "Author"),
    FieldSpec("narrator", "Narrator"),
    FieldSpec("series", "Series"),
    FieldSpec("series_num", "Series #", validator=_v_series_num),
    FieldSpec("year", "Year", validator=_v_year),
    FieldSpec("genre", "Genre"),
)
FIELDS: tuple[str, ...] = tuple(s.key for s in FIELD_SPECS)
FIELD_LABELS: dict[str, str] = {s.key: s.label for s in FIELD_SPECS}

EXT_KIND = {".m4b": "mp4", ".m4a": "mp4", ".mp3": "mp3"}


def _spec(field: str) -> FieldSpec:
    for s in FIELD_SPECS:
        if s.key == field:
            return s
    raise ValueError(f"unknown field {field!r}")


def clean_value(field: str, value, *, strict: bool = True) -> str:
    if field not in FIELDS:
        raise ValueError(f"unknown field {field!r}")
    if not isinstance(value, str):
        raise ValueError(f"{field}: value must be text")
    v = value.strip()
    if strict:
        if any(ord(c) < 32 for c in v):
            raise ValueError(f"{field}: control characters are not allowed")
        spec = _spec(field)
        if len(v) > spec.max_len:
            raise ValueError(f"{field}: too long")
        if spec.validator is not None:
            msg = spec.validator(v)
            if msg:
                raise ValueError(msg)
    return v


def _mp4_text(tags, key: str) -> str:
    vals = tags.get(key) if tags is not None else None
    if not vals:
        return ""
    v = vals[0]
    if isinstance(v, (bytes, bytearray)):
        return bytes(v).decode("utf-8", "replace").strip()
    if isinstance(v, tuple):
        return str(v[0]).strip()
    return str(v).strip()


def _mp4_book_title(tags) -> str:
    """The title ABS displays: Audible/Libation `@sti`, then album, then title."""
    album = _mp4_text(tags, "\xa9alb")
    title = _mp4_text(tags, "\xa9nam")
    aud = _mp4_text(tags, "@sti")
    # `@sti` is an Audible/Libation custom atom. It normally extends the album
    # with the subtitle and "(Unabridged)"; occasionally it contains junk, so
    # only use it when it agrees with the album (or there is no album).
    extends_album = not album or aud.casefold().startswith(album.casefold())
    if aud and "http" not in aud.lower() and extends_album:
        return aud
    return album or title


def read_mp4(path: Path) -> dict[str, Any]:
    f = MP4(str(path))
    t = f.tags
    out = {
        "title": _mp4_text(t, "\xa9nam"),
        "album": _mp4_book_title(t),
        "subtitle": (_mp4_text(t, "\xa9st3") or _mp4_text(t, ITUNES + "SUBTITLE")
                     or _mp4_text(t, TONE + "SUBTITLE")),
        "author": _mp4_text(t, "\xa9ART"),
        "narrator": (_mp4_text(t, "\xa9wrt") or _mp4_text(t, ITUNES + "NARRATOR")
                     or _mp4_text(t, TONE + "NARRATOR")),
        # Audible/Soundbooth files sometimes put the series in the custom
        # SRNM/SRSQ atoms instead of the standard ones (DCC #7 does this).
        "series": (_mp4_text(t, ITUNES + "SERIES") or _mp4_text(t, "\xa9mvn")
                   or _mp4_text(t, TONE + "SERIES") or _mp4_text(t, "SRNM")),
        "series_num": (_mp4_text(t, ITUNES + "SERIES-PART") or _mp4_text(t, "\xa9mvi")
                       or _mp4_text(t, TONE + "SERIES_PART") or _mp4_text(t, "SRSQ")),
        "year": _mp4_text(t, "\xa9day"),
        "genre": _mp4_text(t, "\xa9gen"),
        "duration": round(float(f.info.length or 0), 1),
        "cover": bool(t is not None and "covr" in t),
    }
    try:
        out["chapters"] = len(f.chapters) if f.chapters else 0
    except Exception:
        out["chapters"] = 0
    return out


def write_mp4(path: Path, ch: dict[str, str]) -> None:
    f = MP4(str(path))
    if f.tags is None:
        f.add_tags()
    t = f.tags

    def put(key, val):
        if val:
            t[key] = [val]
        elif key in t:
            del t[key]

    def put_ff(key, val):
        if val:
            t[key] = [MP4FreeForm(val.encode("utf-8"), dataformat=AtomDataType.UTF8)]
        elif key in t:
            del t[key]

    if "title" in ch:
        put("\xa9nam", ch["title"])
    if "album" in ch:
        put("\xa9alb", ch["album"])
        # Keep the Audible/Libation display-title atom in step when it exists.
        if "@sti" in t:
            put("@sti", ch["album"])
    if "subtitle" in ch:
        put("\xa9st3", ch["subtitle"])
        put_ff(ITUNES + "SUBTITLE", ch["subtitle"])
        if TONE + "SUBTITLE" in t:
            put_ff(TONE + "SUBTITLE", ch["subtitle"])
    if "author" in ch:
        old, aart = _mp4_text(t, "\xa9ART"), _mp4_text(t, "aART")
        put("\xa9ART", ch["author"])
        if not aart or aart == old:
            put("aART", ch["author"])
    if "narrator" in ch:
        put("\xa9wrt", ch["narrator"])
        for k in (ITUNES + "NARRATOR", TONE + "NARRATOR"):
            if k in t:
                put_ff(k, ch["narrator"])
    if "series" in ch:
        put_ff(ITUNES + "SERIES", ch["series"])
        put("\xa9mvn", ch["series"])
        if TONE + "SERIES" in t:
            put_ff(TONE + "SERIES", ch["series"])
        if "SRNM" in t:
            put("SRNM", ch["series"])
    if "series_num" in ch:
        v = ch["series_num"]
        put_ff(ITUNES + "SERIES-PART", v)
        if v.isdigit():
            t["\xa9mvi"] = [int(v)]
        elif "\xa9mvi" in t:
            del t["\xa9mvi"]
        if TONE + "SERIES_PART" in t:
            put_ff(TONE + "SERIES_PART", v)
        if "SRSQ" in t:
            put("SRSQ", v)
    if "year" in ch:
        put("\xa9day", ch["year"])
    if "genre" in ch:
        put("\xa9gen", ch["genre"])
    f.save()


def read_mp3(path: Path) -> dict[str, Any]:
    f = MP3(str(path))
    t = f.tags if f.tags is not None else ID3()

    def one(fid):
        fr = t.get(fid)
        return str(fr.text[0]).strip() if fr is not None and getattr(fr, "text", None) else ""

    txxx = {fr.desc.upper(): str(fr.text[0]).strip() for fr in t.getall("TXXX") if fr.text}
    return {
        "title": one("TIT2"),
        # ABS displays album, falling back to title, as its book Title.
        "album": one("TALB") or one("TIT2"),
        "subtitle": one("TIT3") or txxx.get("SUBTITLE", ""),
        "author": one("TPE1"),
        "narrator": one("TCOM") or txxx.get("NARRATOR", ""),
        "series": txxx.get("SERIES") or one("MVNM"),
        "series_num": txxx.get("SERIES-PART") or txxx.get("SERIES_PART") or one("MVIN"),
        "year": one("TDRC"),
        "genre": one("TCON"),
        "duration": round(float(f.info.length or 0), 1),
        "cover": bool(t.getall("APIC")),
        "chapters": len(t.getall("CHAP")),
    }


def write_mp3(path: Path, ch: dict[str, str]) -> None:
    try:
        t = ID3(str(path))
    except ID3NoHeaderError:
        t = ID3()
    ver = 3 if tuple(t.version[:2]) == (2, 3) else 4

    def put(cls, fid, val):
        t.delall(fid)
        if val:
            t.add(cls(encoding=3, text=[val]))

    def put_txxx(desc, val):
        for fr in list(t.getall("TXXX")):
            if fr.desc.upper() == desc:
                t.delall("TXXX:" + fr.desc)
        if val:
            t.add(TXXX(encoding=3, desc=desc, text=[val]))

    if "title" in ch:
        put(TIT2, "TIT2", ch["title"])
    if "album" in ch:
        put(TALB, "TALB", ch["album"])
    if "subtitle" in ch:
        put(TIT3, "TIT3", ch["subtitle"])
        put_txxx("SUBTITLE", ch["subtitle"])
    if "author" in ch:
        put(TPE1, "TPE1", ch["author"])
    if "narrator" in ch:
        put(TCOM, "TCOM", ch["narrator"])
    if "series" in ch:
        put_txxx("SERIES", ch["series"])
        put(MVNM, "MVNM", ch["series"])
    if "series_num" in ch:
        put_txxx("SERIES-PART", ch["series_num"])
        put(MVIN, "MVIN", ch["series_num"])
    if "year" in ch:
        put(TDRC, "TDRC", ch["year"])
    if "genre" in ch:
        put(TCON, "TCON", ch["genre"])
    t.save(str(path), v2_version=ver)


def sniff_image_mime(data: bytes) -> str:
    """Best-effort MIME type for embedded cover bytes."""
    if not data:
        return "application/octet-stream"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"BM"):
        return "image/bmp"
    return "application/octet-stream"


def read_cover_mp4(path: Path) -> tuple[bytes, str] | None:
    """Return (image bytes, mime type) for an MP4/M4B's ``covr`` atom, or None."""
    f = MP4(str(path))
    covr = f.tags.get("covr") if f.tags is not None else None
    if not covr:
        return None
    cover = covr[0]
    data = bytes(cover)
    if not data:
        return None
    fmt = getattr(cover, "imageformat", None)
    if fmt == MP4Cover.FORMAT_PNG:
        return data, "image/png"
    if fmt == MP4Cover.FORMAT_JPEG:
        return data, "image/jpeg"
    return data, sniff_image_mime(data)


def read_cover_mp3(path: Path) -> tuple[bytes, str] | None:
    """Return (image bytes, mime type) for an MP3's front APIC frame, or None."""
    f = MP3(str(path))
    if f.tags is None:
        return None
    pics = f.tags.getall("APIC")
    if not pics:
        return None
    # Prefer the official front cover (APIC type 3); fall back to the first.
    pic = next((p for p in pics if getattr(p, "type", None) == 3), pics[0])
    data = bytes(pic.data)
    if not data:
        return None
    mime = getattr(pic, "mime", "") or ""
    if not mime.startswith("image/"):
        mime = sniff_image_mime(data)
    return data, mime


def read_cover(path: Path) -> tuple[bytes, str] | None:
    """Read embedded cover art for a supported audio file."""
    reader = COVER_READERS.get(EXT_KIND.get(path.suffix.lower()))
    return reader(path) if reader is not None else None


READERS = {"mp4": read_mp4, "mp3": read_mp3}
WRITERS = {"mp4": write_mp4, "mp3": write_mp3}
COVER_READERS = {"mp4": read_cover_mp4, "mp3": read_cover_mp3}
