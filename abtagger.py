#!/usr/bin/env python3
"""
abtagger - a small local web grid for viewing and editing audiobook tags.

    pip install mutagen
    python3 abtagger.py /path/to/audiobooks

See REVIEW.md for design notes, gotchas, and roadmap.
"""

from __future__ import annotations

import argparse
import hmac
import json
import os
import re
import secrets
from abs_client import AbsClient, load_config
from rename import build_rename_plan, resolve_collisions
import settings as settings_mod
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    # keep import side-effect: fail early with a helpful message
    import mutagen  # noqa: F401
except ImportError:  # pragma: no cover
    sys.exit("abtagger needs the 'mutagen' package:  pip install mutagen")

import state as _state_mod
from state import State, _state, do_save, do_undo, STATE as STATE_GLOBAL
from files import scan
from page import PAGE

# Re-export public API for backwards compatibility (tests / external callers).
from tags import (  # noqa: F401
    FIELDS, FIELD_SPECS, FIELD_LABELS, EXT_KIND, ITUNES, TONE,
    YEAR_RE, NUM_RE, clean_value, read_mp4, write_mp4, read_mp3, write_mp3,
    READERS, WRITERS,
)
from files import locate, read_record  # noqa: F401
from state import apply_changes, save_undo  # noqa: F401

MAX_BODY = 8 * 1024 * 1024
MAX_ITEMS = 5000


def do_delete(items) -> dict:
    st = _state()
    if st.read_only:
        raise ValueError("server was started with --read-only")
    if not isinstance(items, list) or not items or len(items) > MAX_ITEMS:
        raise ValueError("bad request")
    results = []
    with st.lock:
        for it in items:
            rel = it.get("path") if isinstance(it, dict) else None
            try:
                path = locate(st.root, rel)
                path.unlink()
                results.append({"path": rel, "ok": True})
            except (ValueError, OSError) as e:
                results.append({"path": rel, "ok": False, "error": str(e)})
    return {"results": results}


def do_abs_scan() -> dict:
    st = _state()
    client = st.abs_client
    if client is None:
        raise ValueError("ABS is not configured (set --abs-url/--abs-token or ~/.abtagger/config.json)")
    lib_id = None
    # prefer configured library ids
    if client.cfg.library_ids:
        lib_id = client.cfg.library_ids[0]
    else:
        lib_id = client.find_library_for_root(st.root)
    if not lib_id:
        raise ValueError("could not match this folder to an ABS library; set abs_library_ids in config")
    res = client.scan_library(lib_id)
    return {"library_id": lib_id, "result": res}


def do_settings_get() -> dict:
    return settings_mod.load()


def do_settings_save(data) -> dict:
    if not isinstance(data, dict):
        raise ValueError("bad request")
    settings_mod.save(data)
    return settings_mod.load()


def _clean_title_from_filename(name: str, author: str) -> str:
    stem = os.path.splitext(name)[0]
    # remove leading author if present
    a = (author or "").strip()
    if a and stem.lower().startswith(a.lower()):
        stem = stem[len(a):]
    # remove separators
    stem = stem.lstrip(" -_")
    # remove common suffixes
    stem = re.sub(r"\s*\((un)?abridged\)\s*$", "", stem, flags=re.I)
    # underscores -> spaces
    stem = stem.replace("_", " ")
    stem = re.sub(r"\s+", " ", stem).strip(" -_")
    return stem


def do_title_from_filename(selected: list[str] | None = None) -> dict:
    st = _state()
    if st.read_only:
        raise ValueError("server was started with --read-only")
    rows = scan(st.root)
    sel_set = set(selected) if selected else {r["path"] for r in rows if not r.get("error")}
    results = []
    with st.lock:
        for r in rows:
            if r.get("error") or r["path"] not in sel_set:
                continue
            new_title = _clean_title_from_filename(r.get("name", r["path"]), r.get("author", ""))
            if not new_title:
                results.append({"path": r["path"], "ok": False, "error": "could not derive title"})
                continue
            # build a change item and apply
            try:
                item = {"path": r["path"], "changes": {"title": {"old": r.get("title", ""), "new": new_title}}}
                rec, entry = apply_changes(item)
                results.append({"path": r["path"], "ok": True, "row": rec, "title": new_title})
            except (ValueError, OSError) as e:
                results.append({"path": r["path"], "ok": False, "error": str(e)})
    return {"results": results}


def do_abs_clean_missing() -> dict:
    st = _state()
    client = st.abs_client
    if client is None:
        raise ValueError("ABS is not configured")
    lib_id = client.cfg.library_ids[0] if client.cfg.library_ids else client.find_library_for_root(st.root)
    if not lib_id:
        raise ValueError("could not match this folder to an ABS library")
    res = client.clean_missing_items(lib_id)
    return {"library_id": lib_id, "result": res}


def do_rename_plan(template: str, selected: list[str] | None = None) -> dict:
    st = _state()
    sel_set = set(selected) if selected else None
    rows = scan(st.root)
    plans = build_rename_plan(st.root, rows, template, selected=sel_set, group_books=True)
    plans = resolve_collisions(plans, st.root)
    return {"items": [{"src": p.src, "dst": p.dst} for p in plans]}


def do_rename_apply(items) -> dict:
    st = _state()
    if st.read_only:
        raise ValueError("server was started with --read-only")
    if not isinstance(items, list) or not items:
        raise ValueError("bad request")
    results = []
    moved_srcs = []
    with st.lock:
        for it in items:
            src_rel = it.get("src")
            dst_rel = it.get("dst")
            try:
                src = locate(st.root, src_rel)
                # validate dst path safety
                if not isinstance(dst_rel, str) or not dst_rel:
                    raise ValueError("bad destination")
                parts = dst_rel.replace("\\", "/").split("/")
                if any(p in ("", ".", "..") for p in parts):
                    raise ValueError("bad destination")
                dst = st.root.joinpath(*parts)
                if dst.resolve().relative_to(st.root) is None:
                    pass
                dst.parent.mkdir(parents=True, exist_ok=True)
                # refuse overwrite
                if dst.exists():
                    raise ValueError("destination already exists")
                os.replace(str(src), str(dst))
                moved_srcs.append(src_rel)
                results.append({"src": src_rel, "dst": dst_rel, "ok": True})
            except (ValueError, OSError) as e:
                results.append({"src": src_rel, "dst": dst_rel, "ok": False, "error": str(e)})
        # clean empty source dirs
        for src_rel in moved_srcs:
            try:
                parent = st.root.joinpath(*src_rel.replace("\\", "/").split("/")[:-1])
                # remove empty dirs up to root
                cur = parent
                while cur != st.root and cur.is_dir():
                    try:
                        cur.rmdir()  # only succeeds if empty
                    except OSError:
                        break
                    cur = cur.parent
            except OSError:
                pass
    # trigger ABS scan if configured (rename is explicit, so auto-scan is ok)
    if st.abs_client is not None:
        try:
            lib_id = st.abs_client.cfg.library_ids[0] if st.abs_client.cfg.library_ids else st.abs_client.find_library_for_root(st.root)
            if lib_id:
                st.abs_client.scan_library(lib_id)
        except Exception:
            pass
    return {"results": results}

# alias module-level STATE for compatibility
STATE = None


def _set_state(s):
    global STATE
    STATE = s
    _state_mod.STATE = s


class Handler(BaseHTTPRequestHandler):
    server_version = "abtagger"
    protocol_version = "HTTP/1.1"

    def _send(self, status: int, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        if status >= 400:
            self.send_header("Connection", "close")
            self.close_connection = True
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                         "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, obj) -> None:
        self._send(status, json.dumps(obj).encode("utf-8"), "application/json; charset=utf-8")

    def _state(self):
        return _state()

    def _guard(self) -> bool:
        st = self._state()
        if st.loopback:
            host = self.headers.get("Host", "")
            name = host.rsplit(":", 1)[0].lower() if ":" in host else host.lower()
            if name not in ("localhost", "127.0.0.1"):
                self._json(403, {"error": "bad Host header"})
                return False
        return True

    def _authed(self) -> bool:
        st = self._state()
        if not hmac.compare_digest(self.headers.get("X-Token", ""), st.token):
            self._json(401, {"error": "missing or wrong token - open the URL printed in the terminal"})
            return False
        return True

    def do_GET(self):
        if not self._guard():
            return
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/api/settings":
            if not self._authed():
                return
            self._json(200, do_settings_get())
        elif path == "/api/scan":
            if not self._authed():
                return
            st = self._state()
            try:
                with st.lock:
                    rows = scan(st.root)
            except Exception as e:
                self.log_error("scan failed: %r", e)
                self._json(500, {"error": "scan failed: " + str(e)})
                return
            self._json(200, {"root": str(st.root), "rows": rows, "read_only": st.read_only,
                            "abs_configured": st.abs_client is not None})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if not self._guard() or not self._authed():
            return
        p = self.path.split("?", 1)[0]
        if p not in ("/api/save", "/api/undo", "/api/delete", "/api/abs/scan", "/api/abs/clean-missing",
                     "/api/rename/plan", "/api/rename/apply", "/api/settings", "/api/title-from-filename"):
            self._json(404, {"error": "not found"})
            return
        st = self._state()
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            n = -1
        if n < 0 or n > MAX_BODY:
            self._json(413, {"error": "request body too large"})
            return
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
            if p == "/api/save":
                if st.read_only:
                    raise ValueError("server was started with --read-only")
                out = do_save(body.get("items") if isinstance(body, dict) else None)
            elif p == "/api/undo":
                if st.read_only:
                    raise ValueError("server was started with --read-only")
                out = do_undo()
            elif p == "/api/delete":
                if st.read_only:
                    raise ValueError("server was started with --read-only")
                out = do_delete(body.get("items") if isinstance(body, dict) else None)
            elif p == "/api/rename/plan":
                out = do_rename_plan(body.get("template", "") if isinstance(body, dict) else "",
                                     body.get("selected") if isinstance(body, dict) else None)
            elif p == "/api/rename/apply":
                if st.read_only:
                    raise ValueError("server was started with --read-only")
                out = do_rename_apply(body.get("items") if isinstance(body, dict) else None)
            elif p == "/api/abs/scan":
                out = do_abs_scan()
            elif p == "/api/abs/clean-missing":
                out = do_abs_clean_missing()
            elif p == "/api/settings":
                out = do_settings_save(body if isinstance(body, dict) else {})
            elif p == "/api/title-from-filename":
                if st.read_only:
                    raise ValueError("server was started with --read-only")
                out = do_title_from_filename(body.get("selected") if isinstance(body, dict) else None)
            else:
                raise ValueError("not found")
            self._json(200, out)
        except (ValueError, json.JSONDecodeError) as e:
            self._json(400, {"error": str(e)})
        except Exception as e:
            self.log_error("request failed: %r", e)
            self._json(500, {"error": "internal error: " + str(e)})


def main() -> None:
    global STATE
    ap = argparse.ArgumentParser(description="Edit audiobook tags in a spreadsheet-style grid.")
    ap.add_argument("root", help="folder containing your audiobooks (scanned recursively)")
    ap.add_argument("--host", default="127.0.0.1",
                    help="address to listen on (default 127.0.0.1; use 0.0.0.0 inside Docker or to "
                         "reach it from another machine - the access token is then your only protection)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--token", help="use this access token instead of a random one")
    ap.add_argument("--state-dir", default=str(Path.home() / ".abtagger"),
                    help="where undo logs are kept (default ~/.abtagger)")
    ap.add_argument("--read-only", action="store_true", help="browse only; refuse all writes")
    ap.add_argument("--open", action="store_true", help="open the page in your browser")
    ap.add_argument("--abs-url", help="Audiobookshelf base URL, e.g. http://localhost:13378")
    ap.add_argument("--abs-token", help="Audiobookshelf API token")
    ap.add_argument("--abs-library", help="ABS library id to scan (optional; auto-detected from root)")
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        sys.exit(f"not a folder: {root}")
    token = args.token or secrets.token_urlsafe(18)
    cfg = load_config()
    if args.abs_url:
        cfg.url = args.abs_url
    if args.abs_token:
        cfg.token = args.abs_token
    if args.abs_library:
        cfg.library_ids = [args.abs_library]
    abs_client = AbsClient(cfg) if (cfg.url and cfg.token) else None
    st = State(root, token, Path(args.state_dir).expanduser(), args.read_only,
               loopback=args.host in ("127.0.0.1", "localhost"), abs_client=abs_client)
    _set_state(st)
    try:
        httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    except OSError as e:
        sys.exit(f"cannot listen on {args.host}:{args.port}: {e}")

    shown = "localhost" if args.host in ("127.0.0.1", "localhost", "0.0.0.0") else args.host
    url = f"http://{shown}:{args.port}/#token={token}"
    print(f"abtagger serving {root}" + ("  [read-only]" if args.read_only else ""))
    print(f"open: {url}")
    if args.host == "0.0.0.0":
        print("listening on all interfaces; from another machine use this computer's address instead of 'localhost'")
    if args.open:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
