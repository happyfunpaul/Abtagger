"""Book-level grouping heuristics.

One "book" can be several audio files (a multi-part rip, or one file per disc).
The grouping key is deliberately metadata-first and path-second:

1. album + author, inside the same (disc-stripped) folder;
2. a filename part marker such as ``Book - 03.mp3`` or ``Book (Part 2).mp3``;
3. normalized title + author, inside the same folder;
4. the filename stem, then the folder as a last resort.

All comparisons are normalized, so case and punctuation do not matter.  Folder
names such as ``CD1`` / ``Disc 2`` are treated as part of their parent so a
multi-disc book collapses into one row.  Rows that failed to read get a unique
key so they never disappear inside another book.
"""

from __future__ import annotations

import os
import re
from typing import Any

_DISC_DIR_RE = re.compile(
    r"^\s*(?:cd|disc|disk|dvd|part|pt|vol(?:ume)?)\s*[-_.]?\s*\d+\s*$", re.I
)

# Leading track/chapter markers: "01 - ", "Chapter 3 ", "Disc 1 - ".
_PART_PREFIX_RE = re.compile(
    r"""^\s*(?:
        (?:cd|disc|disk|volume|vol)\s*\d+\s*[-_.:]\s*
      | (?:part|pt|track|chapter|ch|stave)\s*\d+\s*[-_.:]?\s*
      | \d{1,4}\s*[-_.:]\s*
    )""",
    re.I | re.X,
)

# Trailing part markers: " - 03", "_02", " (Part 3)", " (3)".
# Require a space around a hyphen so titles like "Catch-22" survive.
_PART_SUFFIX_RE = re.compile(
    r"""\s*(?:
        \s+[-–—]\s+(?:part|pt|track|chapter|ch|stave|disc|cd)?\s*\d{1,4}
      | [_.:]\s*(?:part|pt|track|chapter|ch|stave|disc|cd)?\s*\d{1,4}
      | \s+[-–—]\s*(?:part|pt|track|chapter|ch|stave|disc|cd)\s*\d{1,4}
      | [\[(]\s*(?:part|pt|track|chapter|ch|stave|disc|cd)\s*\d+\s*[\])]
      | [\[(]\s*\d{1,4}\s*[\])]
    )\s*$""",
    re.I | re.X,
)

_PART_ONLY_RE = re.compile(
    r"^\s*(?:(?:cd|disc|disk|part|pt|track|chapter|ch|stave)\s*)?\d{1,3}\s*$", re.I
)

_KEY_SEP = "\x1f"


def normalize_title(title: str) -> str:
    t = (title or "").lower()
    # strip common audiobook suffixes
    t = re.sub(r"\((un)?abridged\)", "", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def normalize_author(author: str) -> str:
    a = (author or "").lower()
    a = re.sub(r"[^a-z0-9]+", " ", a)
    return re.sub(r"\s+", " ", a).strip()


def strip_part_markers(text: str) -> str:
    """Remove obvious track/chapter/disc markers from a title or filename stem."""
    s = (text or "").strip()
    prev = None
    while s and s != prev:
        prev = s
        s = _PART_SUFFIX_RE.sub("", s).strip(" -–—_.:")
        s = _PART_PREFIX_RE.sub("", s).strip(" -–—_.:")
    return s


def title_base(title: str) -> str:
    """Normalized title with part markers removed; empty if nothing useful remains."""
    b = strip_part_markers(title)
    if not re.search(r"[A-Za-z0-9]", b) or _PART_ONLY_RE.match(b):
        return ""
    return normalize_title(b)


def group_dir(rel_dir: str) -> str:
    """Fold trailing ``CD1`` / ``Disc 2`` / ``Part 3`` folders into their parent."""
    parts = (rel_dir or "").split("/") if rel_dir else []
    while parts and _DISC_DIR_RE.match(parts[-1]):
        parts.pop()
    return "/".join(parts)


def _filename_base(name: str) -> tuple[str, bool]:
    """Return (normalized stem base, had a part marker)."""
    stem = os.path.splitext(name or "")[0]
    stripped = strip_part_markers(stem)
    if _PART_ONLY_RE.match(stripped):
        return "", True
    return normalize_title(stripped), stripped.strip() != stem.strip()


def book_key(rec: dict[str, Any]) -> str:
    """Stable grouping key for one scanned row."""
    path = rec.get("path") or ""
    if rec.get("error"):
        # Never merge unreadable files into an editable book.
        return _KEY_SEP.join(("error", path))

    rel_dir = rec.get("dir")
    if rel_dir is None:
        rel_dir = path.rsplit("/", 1)[0] if "/" in path else ""
    folder = group_dir(str(rel_dir))

    name = rec.get("name") or (path.rsplit("/", 1)[-1] if path else "")
    author = normalize_author(rec.get("author", "") or "")
    album = normalize_title(rec.get("album", "") or "")

    if album:
        return _KEY_SEP.join((folder, "album", album, author))

    stem_base, has_part_marker = _filename_base(name)
    if has_part_marker and stem_base:
        return _KEY_SEP.join((folder, "file", stem_base, author))

    base = title_base(rec.get("title", "") or "")
    if base:
        return _KEY_SEP.join((folder, "title", base, author))

    if stem_base:
        return _KEY_SEP.join((folder, "file", stem_base, author))

    return _KEY_SEP.join((folder, "folder"))


def group_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group rows by :func:`book_key`, skipping unreadable rows."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        if r.get("error"):
            continue
        groups.setdefault(r.get("book_key") or book_key(r), []).append(r)
    return groups
