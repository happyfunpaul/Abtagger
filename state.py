"""Mutable server state, save/undo orchestration."""

from __future__ import annotations

import json
import secrets
import threading
import time
from pathlib import Path
from typing import Any

from tags import FIELDS, clean_value
from files import locate, read_record

UNDO_KEEP = 50
MAX_ITEMS = 5000


class State:
    def __init__(self, root: Path, token: str, state_dir: Path, read_only: bool, loopback: bool,
                 abs_client=None):
        self.root, self.token, self.state_dir = root, token, state_dir
        self.read_only, self.loopback = read_only, loopback
        self.abs_client = abs_client
        self.lock = threading.Lock()


STATE: "State | None" = None


def _state() -> State:
    # Prefer this module's own state, but fall back to abtagger.STATE for
    # backwards compatibility with callers/tests that set the global there.
    if STATE is not None:
        return STATE
    import sys
    ab = sys.modules.get("abtagger")
    if ab is not None and getattr(ab, "STATE", None) is not None:
        return ab.STATE
    raise RuntimeError("server state not initialised")


def apply_changes(item: dict[str, Any], *, restore: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    """Write one file's changes. Returns (new_record, undo_entry). Raises ValueError."""
    st = _state()
    root = st.root
    path = locate(root, item.get("path"))
    ch = item.get("changes")
    if not isinstance(ch, dict) or not ch:
        raise ValueError("no changes given")
    new, old = {}, {}
    for f, pair in ch.items():
        if f not in FIELDS or not isinstance(pair, dict):
            raise ValueError(f"unknown field {f!r}")
        new[f] = clean_value(f, pair.get("new"), strict=not restore)
        if not isinstance(pair.get("old"), str):
            raise ValueError("missing previous value")
        old[f] = pair["old"]
    cur = read_record(path, root)
    if cur["error"]:
        raise ValueError("cannot edit: " + cur["error"])
    for f in new:
        if cur[f] != old[f]:
            raise ValueError(f"{f} changed on disk since it was loaded; reload and try again")
    new = {f: v for f, v in new.items() if v != cur[f]}
    if not new:
        return cur, {}
    from tags import WRITERS, EXT_KIND
    WRITERS[EXT_KIND[path.suffix.lower()]](path, new)
    after = read_record(path, root)
    if after["error"]:
        raise ValueError("file unreadable after write: " + after["error"])
    bad = [f for f, v in new.items() if after[f] != v]
    if bad:
        raise ValueError("written, but reads back differently: " + ", ".join(bad))
    entry = {"path": item["path"], "changes": {f: {"old": cur[f], "new": new[f]} for f in new}}
    return after, entry


def save_undo(entries: list[dict[str, Any]]) -> None:
    if not entries:
        return
    st = _state()
    st.state_dir.mkdir(parents=True, exist_ok=True)
    name = time.strftime("undo-%Y%m%d-%H%M%S-") + secrets.token_hex(2) + ".json"
    (st.state_dir / name).write_text(
        json.dumps({"saved": time.strftime("%Y-%m-%d %H:%M:%S"), "root": str(st.root),
                    "entries": entries}, indent=1), encoding="utf-8")
    logs = sorted(st.state_dir.glob("undo-*.json"))
    for old in logs[:-UNDO_KEEP]:
        old.unlink(missing_ok=True)


def do_save(items) -> dict[str, Any]:
    st = _state()
    if not isinstance(items, list) or len(items) > MAX_ITEMS:
        raise ValueError("bad request")
    results, entries = [], []
    with st.lock:
        for it in items:
            rel = it.get("path") if isinstance(it, dict) else None
            try:
                rec, entry = apply_changes(it)
                results.append({"path": rel, "ok": True, "row": rec})
                if entry:
                    entries.append(entry)
            except (ValueError, OSError) as e:
                results.append({"path": rel, "ok": False, "error": str(e)})
        save_undo(entries)
    return {"results": results}


def do_undo() -> dict[str, Any]:
    st = _state()
    with st.lock:
        logs = sorted(st.state_dir.glob("undo-*.json")) if st.state_dir.is_dir() else []
        if not logs:
            raise ValueError("nothing to undo")
        log = logs[-1]
        data = json.loads(log.read_text(encoding="utf-8"))
        if data.get("root") != str(st.root):
            raise ValueError("the latest undo log belongs to a different folder")
        results = []
        for e in data["entries"]:
            item = {"path": e["path"],
                    "changes": {f: {"old": v["new"], "new": v["old"]} for f, v in e["changes"].items()}}
            try:
                rec, _ = apply_changes(item, restore=True)
                results.append({"path": e["path"], "ok": True, "row": rec})
            except (ValueError, OSError) as ex:
                results.append({"path": e["path"], "ok": False, "error": str(ex)})
        log.rename(log.with_suffix(".undone"))
    return {"results": results}
