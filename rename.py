"""Filename/path template rendering and duplicate detection for audiobooks."""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from books import group_rows, normalize_author, normalize_title

ILLEGAL = '<>:"/\\|?*'
RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}


def _slug_component(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).strip()
    for ch in ILLEGAL:
        s = s.replace(ch, " ")
    # collapse whitespace
    s = re.sub(r"\s+", " ", s).strip(" .")
    if not s or not re.search(r"[A-Za-z0-9]", s):
        return ""
    # Windows reserved names
    stem = s.split(".")[0].upper()
    if stem in RESERVED:
        s = s + "_"
    if len(s) > 120:
        s = s[:120].rstrip(" .")
    return s


def split_author(author: str) -> tuple[str, str]:
    author = (author or "").strip()
    if not author:
        return "", ""
    if "," in author:
        last, _, first = author.partition(",")
        return last.strip(), first.strip()
    parts = author.split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[-1], " ".join(parts[:-1])


def _field_value(rec: dict[str, Any], key: str, original_name: str) -> str:
    if key == "author_last":
        return split_author(rec.get("author", ""))[0]
    if key == "author_first":
        return split_author(rec.get("author", ""))[1]
    if key == "filename":
        return original_name
    if key == "stem":
        return os.path.splitext(original_name)[0]
    if key == "ext":
        return os.path.splitext(original_name)[1].lstrip(".")
    if key in ("title", "book_title", "album"):
        # In ABS terms the book title is the album tag; `title` is the
        # per-file track/chapter title.
        v = str(rec.get("album") or rec.get("title") or "").strip()
    elif key == "track_title":
        v = str(rec.get("title") or "").strip()
    else:
        v = str(rec.get(key, "") or "").strip()
    return v.replace("/", " ").replace("\\", " ")


# Conditional bracket groups: text inside [...] is emitted only if every
# placeholder inside it resolves to a non-empty value.
_BRACKET_RE = re.compile(r"\[([^\[\]]*)\]")
_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_]+)\}")


def _render_brackets(template: str, rec: dict[str, Any], original_name: str, depth: int = 0) -> str:
    # Resolve innermost brackets first.
    prev = None
    cur = template
    # iterate until no brackets remain
    while True:
        m = _BRACKET_RE.search(cur)
        if not m:
            break
        inner = m.group(1)
        # render placeholders in inner to check emptiness
        vals = {}
        for pm in _PLACEHOLDER_RE.finditer(inner):
            k = pm.group(1)
            vals[k] = _field_value(rec, k, original_name)
        # if any placeholder empty -> drop whole bracket
        if any(v == "" for v in vals.values()) and vals:
            replacement = ""
        else:
            replacement = _PLACEHOLDER_RE.sub(lambda mm: vals.get(mm.group(1), _field_value(rec, mm.group(1), original_name)), inner)
        cur = cur[:m.start()] + replacement + cur[m.end():]
    # render remaining placeholders
    def repl(mm):
        return _field_value(rec, mm.group(1), original_name)
    cur = _PLACEHOLDER_RE.sub(repl, cur)
    return cur


def render_template(template: str, rec: dict[str, Any], original_name: str = "") -> str:
    """Render a template into a relative path string (with '/' separators)."""
    rendered = _render_brackets(template, rec, original_name)
    # sanitize each path component
    parts = rendered.split("/")
    out = []
    for part in parts:
        # allow multiple components separated by / only; backslashes -> /
        # sanitize
        s = _slug_component(part)
        if s:
            out.append(s)
    # drop empty trailing
    return "/".join(out)


# Built-in presets (name, template)
BUILTIN_TEMPLATES: list[tuple[str, str]] = [
    ("Author Last, First / Series / Num - Title",
     "{author_last}, {author_first}/[{series}/][{series_num} - ]{title}"),
    ("Author / Title",
     "{author}/{title}"),
    ("Series / Num - Title",
     "[{series}/][{series_num} - ]{title}"),
    ("Author Last, First / Title",
     "{author_last}, {author_first}/{title}"),
    ("Keep filename (no rename)",
     "{filename}"),
]


def duplicate_key(rec: dict[str, Any]) -> str:
    t = normalize_title(rec.get("title", ""))
    a = normalize_author(rec.get("author", ""))
    s = normalize_title(rec.get("series", ""))
    n = str(rec.get("series_num", "") or "").strip()
    # include duration bucket to distinguish editions
    dur = rec.get("duration", 0) or 0
    bucket = int(round(dur / 60.0)) if dur else 0
    return f"{t}|{a}|{s}|{n}|{bucket}"


def find_duplicates(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        if r.get("error"):
            continue
        groups.setdefault(duplicate_key(r), []).append(r)
    return [g for g in groups.values() if len(g) > 1]


@dataclass
class RenamePlan:
    src: str
    dst: str
    is_dir_move: bool = False


def rename_normalize_title(t: str) -> str:
    return normalize_title(t)


def _natkey(s: str):
    """Natural sort key so ``book 2`` sorts before ``book 10``."""
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", s)]


# Explicit part markers in a title or filename. Deliberately excludes "book N":
# that is usually the book number, not the part number.
_PART_WORD_RE = re.compile(
    r"\b(?:part|pt|disc|disk|cd|track|chapter|ch|volume|vol)\s*[-_.:]?\s*(\d{1,4})\b",
    re.I,
)


def _part_number(rec: dict[str, Any], original: str, index: int) -> int:
    """Best guess at this file's part ordinal within a multi-file book."""
    stem = os.path.splitext(original or "")[0]
    # Prefer explicit markers such as "Part 2" in the track title or filename.
    for text in (str(rec.get("title") or ""), stem):
        m = _PART_WORD_RE.search(text)
        if m:
            return int(m.group(1))
    m = re.search(r"\((\d{1,3})\)\s*$", stem)
    if m:
        return int(m.group(1))
    m = re.search(r"[-_.]\s*(\d{1,4})\s*$", stem)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d{1,4})\s*$", stem)
    if m:
        return int(m.group(1))
    return index


def _ends_with_part(stem: str, part: int) -> bool:
    """True when ``stem`` already ends with this part number."""
    return bool(re.search(rf"(?:^|[^0-9])0*{part}\s*$", stem))


def _split_dst(dst: str) -> tuple[str, str]:
    if "/" in dst:
        folder, name = dst.rsplit("/", 1)
        return folder, name
    return "", dst


def build_rename_plan(root: Path, rows: list[dict[str, Any]], template: str,
                      selected: set[str] | None = None, group_books: bool = True) -> list[RenamePlan]:
    """Build a deterministic rename plan.

    Part numbers are applied only to files that resolve to the *same*
    destination file, i.e. records that really are parts of one book.  A folder
    that happens to hold several standalone books (an old ``Author/Series``
    layout) must not gain spurious ``- 1`` / ``- 2`` suffixes.
    """
    groups = group_rows(rows)
    selected_paths = selected if selected is not None else {r["path"] for r in rows if not r.get("error")}

    work: dict[str, dict[str, Any]] = {}
    for gk in sorted(groups):
        grp = [r for r in groups[gk] if not r.get("error")]
        if not grp or not any(r["path"] in selected_paths for r in grp):
            continue
        if group_books:
            # Move every file of a multi-file book together.
            use = grp
        else:
            use = [r for r in grp if r["path"] in selected_paths]
        for r in use:
            work[r["path"]] = r

    raw: list[tuple[dict[str, Any], str, str]] = []
    for path in sorted(work, key=_natkey):
        r = work[path]
        original = r.get("name") or path.rsplit("/", 1)[-1]
        dst_rel = render_template(template, r, original)
        if not dst_rel or dst_rel == path:
            continue
        # ensure extension preserved if template omitted ext
        last = dst_rel.rsplit("/", 1)[-1]
        if "." not in last and "." in original:
            dst_rel += os.path.splitext(original)[1]
        if dst_rel == path:
            continue  # already in the target layout (idempotent re-runs)
        raw.append((r, dst_rel, original))

    # Group by destination file first. Only real collisions/parts are numbered.
    by_dst: dict[str, list[tuple[dict[str, Any], str, str]]] = {}
    for item in raw:
        by_dst.setdefault(item[1].casefold(), []).append(item)

    plans: list[RenamePlan] = []
    for key in sorted(by_dst):
        items = by_dst[key]
        if len(items) == 1:
            r, dst_rel, _ = items[0]
            plans.append(RenamePlan(src=r["path"], dst=dst_rel))
            continue
        ordered = sorted(items, key=lambda x: _natkey(x[0]["path"]))
        for idx, (r, dst_rel, original) in enumerate(ordered, start=1):
            folder, fname = _split_dst(dst_rel)
            stem, ext = os.path.splitext(fname)
            part = _part_number(r, original, idx)
            if not _ends_with_part(stem, part):
                stem = f"{stem} - {part}"
            dst_rel = f"{folder}/{stem}{ext}" if folder else f"{stem}{ext}"
            if dst_rel == r["path"]:
                continue  # already in the target layout
            plans.append(RenamePlan(src=r["path"], dst=dst_rel))

    plans.sort(key=lambda p: _natkey(p.src))
    return plans


def resolve_collisions(plans: list[RenamePlan], root: Path) -> list[RenamePlan]:
    seen: set[str] = set()
    out: list[RenamePlan] = []
    for pl in plans:
        dst = pl.dst
        # avoid collisions with other planned dsts and existing files
        base_folder, fname = (dst.rsplit("/", 1) + [""])[:2] if "/" in dst else ("", dst)
        stem, ext = os.path.splitext(fname)
        counter = 1
        candidate = dst
        while candidate in seen or (root / candidate).exists():
            counter += 1
            new_fname = f"{stem} ({counter}){ext}"
            candidate = f"{base_folder}/{new_fname}" if base_folder else new_fname
        seen.add(candidate)
        out.append(RenamePlan(src=pl.src, dst=candidate, is_dir_move=pl.is_dir_move))
    return out
