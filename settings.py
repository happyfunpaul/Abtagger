"""Persistent settings (ABS config, rename template, etc.) in ~/.abtagger/config.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_PATH = Path.home() / ".abtagger" / "config.json"

# The documented default (see README.md): one folder per book, matching the
# layout Audiobookshelf uses for its book identity.
DEFAULT_RENAME_TEMPLATE = "{author_last}, {author_first}/[{series}/][{series_num} - ]{title}/{title}"

DEFAULTS = {
    "abs_url": "",
    "abs_token": "",
    "abs_library_ids": [],
    "rename_template": DEFAULT_RENAME_TEMPLATE,
    "title_from_filename_cleanup": True,
}


def load() -> dict[str, Any]:
    out = dict(DEFAULTS)
    if CONFIG_PATH.is_file():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                out.update({k: data.get(k, out[k]) for k in DEFAULTS if k in data})
        except (OSError, json.JSONDecodeError):
            pass
    # A blank/whitespace template means "not set"; fall back to the default so
    # the settings pane never shows an empty or lost rename format.
    if not str(out.get("rename_template") or "").strip():
        out["rename_template"] = DEFAULT_RENAME_TEMPLATE
    return out


def save(data: dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    cur = load()
    for k in DEFAULTS:
        if k in data:
            cur[k] = data[k]
    if not str(cur.get("rename_template") or "").strip():
        cur["rename_template"] = DEFAULT_RENAME_TEMPLATE
    CONFIG_PATH.write_text(json.dumps(cur, indent=2), encoding="utf-8")
