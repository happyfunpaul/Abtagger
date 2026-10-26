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

    def _request(self, method: str, path: str, body: Any = None) -> Any:
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
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"ABS HTTP {e.code}: {e.read().decode('utf-8', 'replace')}") from e

    def get_libraries(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/api/libraries")
        return data.get("libraries", [])

    def find_library_for_root(self, root: Path) -> str | None:
        """Best-effort: match our root to an ABS library folder path."""
        root_s = str(root).replace("\\", "/").rstrip("/")
        for lib in self.get_libraries():
            for folder in lib.get("folders", []):
                fp = str(folder.get("fullPath", "")).replace("\\", "/").rstrip("/")
                if fp and (root_s == fp or root_s.startswith(fp + "/")):
                    return lib["id"]
        return None

    def scan_library(self, library_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/libraries/{library_id}/scan")

    def scan_item(self, item_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/items/{item_id}/scan")

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
                    self._request("DELETE", f"/api/items/{it['id']}")
                    removed += 1
                except Exception:
                    pass
        return {"removed": removed}
