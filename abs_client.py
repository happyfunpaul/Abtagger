"""Thin client for the Audiobookshelf HTTP API."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AbsConfig:
    url: str = ""
    token: str = ""
    library_ids: list[str] = field(default_factory=list)


def load_config() -> AbsConfig:
    from settings import load as load_settings
    s = load_settings()
    cfg = AbsConfig()
    cfg.url = os.environ.get("ABTAGGER_ABS_URL", s.get("abs_url", "")) or ""
    cfg.token = os.environ.get("ABTAGGER_ABS_TOKEN", s.get("abs_token", "")) or ""
    cfg.library_ids = s.get("abs_library_ids", []) or []
    return cfg


class AbsClient:
    def __init__(self, cfg: AbsConfig):
        self.cfg = cfg

    def _request(self, method: str, path: str, body: Any = None, *,
                 expect_json: bool = True) -> Any:
        if not self.cfg.url or not self.cfg.token:
            raise RuntimeError("ABS not configured (set abs_url/abs_token in ~/.abtagger/config.json or env)")
        url = self.cfg.url.rstrip("/") + path
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", "Bearer " + self.cfg.token)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                ctype = resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"ABS HTTP {e.code}: {e.read().decode('utf-8', 'replace')}") from e
        if not raw:
            return {}
        if not expect_json:
            # ABS's scan/delete endpoints return 200 with text/plain "OK" (or an
            # empty body), not JSON.
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"ok": True, "body": raw.decode("utf-8", "replace").strip()}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"ABS returned non-JSON from {method} {path} ({ctype}): {raw[:200]!r}"
            ) from e

    def get_libraries(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/api/libraries")
        return data.get("libraries", [])

    def find_library_for_root(self, root: Path) -> str | None:
        """Best-effort: match our root to an ABS library folder path.

        If ABS runs in Docker, its folder path (``/audiobooks``) will not match
        the host path (``M:\\Audiobooks``). When there is exactly one library,
        using it is unambiguous, so fall back to it instead of forcing the user
        to copy the library id into config.
        """
        root_s = str(root).replace("\\", "/").rstrip("/")
        libs = self.get_libraries()
        for lib in libs:
            for folder in lib.get("folders", []):
                fp = str(folder.get("fullPath", "")).replace("\\", "/").rstrip("/")
                if fp and (root_s == fp or root_s.startswith(fp + "/")):
                    return lib.get("id")
        if len(libs) == 1:
            return libs[0].get("id")
        return None

    def scan_library(self, library_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/libraries/{library_id}/scan", expect_json=False)

    def scan_item(self, item_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/items/{item_id}/scan", expect_json=False)

    def get_library_items(self, library_id: str, limit: int = 0) -> list[dict[str, Any]]:
        data = self._request("GET", f"/api/libraries/{library_id}/items?limit={limit}")
        return data.get("results", [])

    def find_items_by_path(self, library_id: str, path: str) -> list[dict[str, Any]]:
        target = path.replace("\\", "/")
        out = []
        for it in self.get_library_items(library_id):
            p = str(it.get("path", "")).replace("\\", "/")
            if p == target or p.endswith("/" + target) or target in p:
                out.append(it)
        return out

    def clean_missing_items(self, library_id: str) -> dict[str, Any]:
        removed = 0
        for it in self.get_library_items(library_id):
            if it.get("isMissing"):
                try:
                    self._request("DELETE", f"/api/items/{it['id']}", expect_json=False)
                    removed += 1
                except Exception:
                    pass
        return {"removed": removed}
