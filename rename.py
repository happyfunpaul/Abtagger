"""Filename/path template rendering and duplicate detection for audiobooks."""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ILLEGAL = '<>:"/\\|?*'
RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}


def _slug_component(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).strip()
    for ch in ILLEGAL:
        s = s.replace(ch, " ")
    # collapse whitespace
    s = re.sub(r"\s+", " ", s).strip(" .")
    if not s:
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


def normalize_title(title: str) -> str:
    t = (title or "").lower()
    # strip common audiobook suffixes
    t = re.sub(r"\((un)?abridged\)", "", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def normalize_author(author: str) -> str:
    a = (author or "").lower()
    a = re.sub(r"[^a-z0-9]+", " ", a)
    a = re.sub(r"\s+", " ", a).strip()
    return a


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


def build_rename_plan(root: Path, rows: list[dict[str, Any]], template: str,
                      selected: set[str] | None = None) -> list[RenamePlan]:
    plans = []
    for r in rows:
        if r.get("error"):
            continue
        if selected is not None and r.get("path") not in selected:
            continue
        original = r.get("name") or r["path"].rsplit("/", 1)[-1]
        dst_rel = render_template(template, r, original)
        if not dst_rel or dst_rel == r["path"]:
            continue
        # ensure extension preserved if template omitted ext
        if "." not in dst_rel.rsplit("/", 1)[-1] and "." in original:
            dst_rel = dst_rel + os.path.splitext(original)[1]
        plans.append(RenamePlan(src=r["path"], dst=dst_rel))
    return plans
