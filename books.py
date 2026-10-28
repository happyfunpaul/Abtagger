"""Book identity: one book is one folder.

This deliberately mirrors Audiobookshelf's scanner rather than guessing from
tags:

1. a folder that directly contains audio files is one book;
2. an audio file loose in the library root is its own book;
3. trailing ``CD1`` / ``Disc 2`` subfolders fold into their parent.

Tags are metadata, not identity.  That means a bad ``album`` tag can no longer
merge two unrelated books, and a folder holding several standalone files is
shown the same way ABS shows it.  Rows that failed to read get a unique key so
they never disappear inside another book.

The title-normalisation helpers below are still used by rename planning and
duplicate detection; they are no longer part of the grouping key.
"""

from __future__ import annotations

import os
import re
from typing import Any

# ABS only folds disc-style directories into their parent:
# /^(cd|dis[ck])\s*\d{1,3}$/i
_DISC_DIR_RE = re.compile(r"^\s*(?:cd|dis[ck])\s*\d{1,3}\s*$", re.I)

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
    """Fold trailing ``CD1`` / ``Disc 2`` folders into their parent, like ABS."""
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
    """Stable grouping key for one scanned row, based on filesystem layout."""
    path = rec.get("path") or ""
    if rec.get("error"):
        # Never merge unreadable files into an editable book.
        return _KEY_SEP.join(("error", path))

    rel_dir = rec.get("dir")
    if rel_dir is None:
        rel_dir = path.rsplit("/", 1)[0] if "/" in path else ""
    folder = group_dir(str(rel_dir))

    if folder:
        return _KEY_SEP.join(("folder", folder))

    # A loose file in the library root is its own book, exactly like ABS.
    return _KEY_SEP.join(("file", path))


def group_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group rows by :func:`book_key`, skipping unreadable rows."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        if r.get("error"):
            continue
        groups.setdefault(r.get("book_key") or book_key(r), []).append(r)
    return groups
