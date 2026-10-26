"""Tag reading/writing backends for audiobook metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

try:
    from mutagen.id3 import (ID3, ID3NoHeaderError, MVIN, MVNM, TALB, TCOM,
                             TCON, TDRC, TIT2, TPE1, TXXX)
    from mutagen.mp3 import MP3
    from mutagen.mp4 import MP4, AtomDataType, MP4FreeForm
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
    FieldSpec("title", "Title"),
    FieldSpec("album", "Album"),
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


def read_mp4(path: Path) -> dict[str, Any]:
    f = MP4(str(path))
    t = f.tags
    out = {
        "title": _mp4_text(t, "\xa9nam"),
        "album": _mp4_text(t, "\xa9alb"),
        "author": _mp4_text(t, "\xa9ART"),
        "narrator": (_mp4_text(t, "\xa9wrt") or _mp4_text(t, ITUNES + "NARRATOR")
                     or _mp4_text(t, TONE + "NARRATOR")),
        "series": (_mp4_text(t, ITUNES + "SERIES") or _mp4_text(t, "\xa9mvn")
                   or _mp4_text(t, TONE + "SERIES")),
        "series_num": (_mp4_text(t, ITUNES + "SERIES-PART") or _mp4_text(t, "\xa9mvi")
                       or _mp4_text(t, TONE + "SERIES_PART")),
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
    if "series_num" in ch:
        v = ch["series_num"]
        put_ff(ITUNES + "SERIES-PART", v)
        if v.isdigit():
            t["\xa9mvi"] = [int(v)]
        elif "\xa9mvi" in t:
            del t["\xa9mvi"]
        if TONE + "SERIES_PART" in t:
            put_ff(TONE + "SERIES_PART", v)
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
        "album": one("TALB"),
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


READERS = {"mp4": read_mp4, "mp3": read_mp3}
WRITERS = {"mp4": write_mp4, "mp3": write_mp3}
