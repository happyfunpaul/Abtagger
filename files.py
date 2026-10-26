"""Filesystem helpers: safe path resolution and scanning."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from tags import EXT_KIND, FIELDS, READERS


def _natkey(s: str):
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", s)]


def locate(root: Path, rel) -> Path:
    """Map a client-supplied relative path to a file strictly inside root."""
    if not isinstance(rel, str) or not rel or "\x00" in rel or rel.startswith("/"):
        raise ValueError("bad path")
    if os.sep != "/" and "\\" in rel:
        raise ValueError("bad path")
    parts = rel.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise ValueError("bad path")
    logical = root.joinpath(*parts)
    if logical.suffix.lower() not in EXT_KIND:
        raise ValueError("unsupported file type")
    try:
        real = logical.resolve(strict=True)
    except OSError:
        raise ValueError("file not found") from None
    try:
        real.relative_to(root)
    except ValueError:
        raise ValueError("path escapes the library folder") from None
    if not real.is_file():
        raise ValueError("not a file")
    return logical


def read_record(path: Path, root: Path) -> dict[str, Any]:
    rel = path.relative_to(root).as_posix()
    st = path.stat()
    rec = {
        "path": rel,
        "dir": rel.rsplit("/", 1)[0] if "/" in rel else "",
        "name": path.name,
        "kind": path.suffix.lower().lstrip("."),
        "size": st.st_size,
        "mtime": int(st.st_mtime),
        "duration": 0, "chapters": 0, "cover": False, "error": "",
    }
    rec.update({f: "" for f in FIELDS})
    try:
        rec.update(READERS[EXT_KIND[path.suffix.lower()]](path))
    except Exception as e:  # unreadable / corrupt file: show it, but do not allow edits
        rec["error"] = f"{type(e).__name__}: {e}"
    return rec


def scan(root: Path) -> list[dict[str, Any]]:
    paths = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in filenames:
            if fn.startswith("."):
                continue
            if os.path.splitext(fn)[1].lower() in EXT_KIND:
                p = Path(dirpath) / fn
                try:
                    p.resolve(strict=True).relative_to(root)
                except (OSError, ValueError):
                    continue  # broken link, or a link that points outside the folder
                paths.append(p)
    paths.sort(key=lambda p: _natkey(p.relative_to(root).as_posix()))
    return [read_record(p, root) for p in paths]
