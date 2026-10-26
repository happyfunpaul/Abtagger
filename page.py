PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>abtagger</title>
<style>
:root{--bg:#f6f6f3;--panel:#fff;--ink:#1c1c1a;--dim:#6c6c66;--line:#dcdcd5;--accent:#2457c5;--accent-ink:#fff;
--dirty:#fff1bd;--dirty-line:#d6a100;--bad:#b3261e;--badbg:#fde7e5;--sel:#e7eefb;--hover:#f0f0ec}
@media (prefers-color-scheme:dark){:root{--bg:#151514;--panel:#1e1e1c;--ink:#ecece7;--dim:#9b9b93;--line:#35352f;
--accent:#7ba3ff;--accent-ink:#0b1633;--dirty:#463c10;--dirty-line:#e0b400;--bad:#ff9189;--badbg:#4a1f1b;--sel:#1f2d49;--hover:#272724}}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif;display:flex;flex-direction:column}
header,.bulk{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:10px 16px;background:var(--panel);border-bottom:1px solid var(--line)}
header .title{display:flex;gap:10px;align-items:baseline;min-width:0}
header .title #root{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:40vw;direction:rtl;text-align:left}
.spacer{flex:1}
.dim{color:var(--dim)}
button,select,input[type=search],.bulk input[type=text]{font:inherit;color:inherit;background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:5px 10px}
button{cursor:pointer}
button:hover:not(:disabled){background:var(--hover)}
button:disabled{opacity:.5;cursor:default}
button.primary{background:var(--accent);color:var(--accent-ink);border-color:var(--accent);font-weight:600}
button.primary:hover:not(:disabled){filter:brightness(1.08);background:var(--accent)}
:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.bulk{font-size:13px}
.bulk .grp{display:flex;gap:6px;align-items:center;flex-wrap:wrap;padding-right:14px;margin-right:6px;border-right:1px solid var(--line)}
.bulk .grp:last-child{border-right:0}
.bulk input[type=text]{width:11rem}
.bulk label.chk{display:flex;gap:4px;align-items:center}
#status{padding:6px 16px;min-height:2rem;font-size:13px;color:var(--dim)}
#status.bad{color:var(--bad)}
#status.good{color:var(--ink)}
.wrap{flex:1;overflow:auto;border-top:1px solid var(--line)}
table{border-collapse:separate;border-spacing:0;width:100%;background:var(--panel)}
thead th{position:sticky;top:0;z-index:2;background:var(--panel);text-align:left;font-weight:600;padding:7px 8px;border-bottom:1px solid var(--line);white-space:nowrap;user-select:none;cursor:pointer}
thead th.nosort{cursor:default}
thead th:hover:not(.nosort){background:var(--hover)}
tbody td{padding:0;border-bottom:1px solid var(--line);vertical-align:middle}
tbody tr.sel td{background:var(--sel)}
tbody tr.err td{background:var(--badbg)}
td.cb,th.cb{width:34px;text-align:center;padding:0 6px}
td.path{padding:4px 8px;min-width:16rem;max-width:26rem}
td.path .name{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
td.path .dir{display:block;font-size:12px;color:var(--dim);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;direction:rtl;text-align:left}
td.path .msg{display:block;font-size:12px;color:var(--bad);white-space:normal}
td input[type=text]{width:100%;border:0;background:transparent;color:inherit;font:inherit;padding:7px 8px;border-radius:0;min-width:3rem}
td input[type=text]:focus{outline:2px solid var(--accent);outline-offset:-2px;background:var(--panel)}
td input[type=text]:disabled{color:var(--dim)}
td.dirty{background:var(--dirty);box-shadow:inset 3px 0 0 var(--dirty-line)}
td.invalid{background:var(--badbg);box-shadow:inset 3px 0 0 var(--bad)}
td.info{padding:4px 8px;color:var(--dim);white-space:nowrap;font-variant-numeric:tabular-nums;font-size:13px}
.busy .wrap{pointer-events:none;opacity:.6}
@media (max-width:700px){header .title #root{display:none}}
</style>
</head>
<body>
<header>
  <div class="title"><strong>abtagger</strong><span id="root" class="dim"></span></div>
  <div class="spacer"></div>
  <input id="filter" type="search" placeholder="Filter rows..." aria-label="Filter rows" autocomplete="off">
  <button id="reload" type="button">Reload</button>
  <button id="undo" type="button" title="Restore the tags overwritten by the previous save">Undo last save</button>
  <button id="save" type="button" class="primary" disabled>Save</button>
</header>
<section class="bulk" aria-label="Bulk edit selected rows">
  <div class="grp">
    <label for="bfield" class="dim">Field</label>
    <select id="bfield"></select>
  </div>
  <div class="grp">
    <input id="bvalue" type="text" placeholder="New value" aria-label="New value" autocomplete="off">
    <button id="bset" type="button">Set on selected</button>
  </div>
  <div class="grp">
    <input id="bfind" type="text" placeholder="Find" aria-label="Find" autocomplete="off">
    <input id="brepl" type="text" placeholder="Replace with" aria-label="Replace with" autocomplete="off">
    <label class="chk"><input id="bregex" type="checkbox"> regex</label>
    <button id="breplace" type="button">Replace in selected</button>
  </div>
  <div class="grp">
    <label for="bfrom" class="dim">Copy from</label>
    <select id="bfrom"></select>
    <button id="bcopy" type="button">Copy to field</button>
  </div>
  <div class="grp">
    <button id="brevsel" type="button">Revert selected</button>
    <button id="brevall" type="button">Revert all</button>
  </div>
</section>
<div id="status" role="status" aria-live="polite"></div>
<div class="wrap">
<table id="grid">
  <thead><tr id="head"></tr></thead>
  <tbody></tbody>
</table>
</div>
<script>
(() => {
"use strict";
const COLS = [
  {key:"title", label:"Title", w:260},
  {key:"album", label:"Album", w:220},
  {key:"author", label:"Author", w:170},
  {key:"narrator", label:"Narrator", w:150},
  {key:"series", label:"Series", w:190},
  {key:"series_num", label:"#", w:64},
  {key:"year", label:"Year", w:90},
  {key:"genre", label:"Genre", w:120},
];
const FIELDS = COLS.map(c => c.key);
const LABEL = Object.fromEntries(COLS.map(c => [c.key, c.label]));
const $ = (id) => document.getElementById(id);
const collator = new Intl.Collator(undefined, {numeric: true, sensitivity: "base"});
const S = {rows: [], vis: [], sortKey: "path", sortDir: 1, filter: "", last: null, readOnly: false, busy: false};

let token = "";
try {
  const m = /token=([^&]+)/.exec(location.hash);
  if (m) {
    token = decodeURIComponent(m[1]);
    sessionStorage.setItem("abtagger-token", token);
    history.replaceState(null, "", location.pathname);
  } else {
    token = sessionStorage.getItem("abtagger-token") || "";
  }
} catch (e) { /* storage unavailable: token stays in memory only */ }

async function api(path, body) {
  const opt = {headers: {"X-Token": token}, cache: "no-store"};
  if (body !== undefined) {
    opt.method = "POST";
    opt.headers["Content-Type"] = "application/json";
    opt.body = JSON.stringify(body);
  }
  const r = await fetch(path, opt);
  let data = {};
  try { data = await r.json(); } catch (e) { /* non-JSON error body */ }
  if (!r.ok) throw new Error(data.error || ("HTTP " + r.status));
  return data;
}

function status(msg, kind) {
  const el = $("status");
  el.textContent = msg || "";
  el.className = kind || "";
}

/* ---------- model ---------- */
function mkRow(rec) {
  const cur = {};
  FIELDS.forEach(f => { cur[f] = rec[f] || ""; });
  return {rec, cur, sel: false, msg: ""};
}
const isDirtyField = (r, f) => r.cur[f] !== (r.rec[f] || "");
const dirtyFields = (r) => FIELDS.filter(f => isDirtyField(r, f));

function problem(f, v) {
  const t = v.trim();
  if (/[\u0000-\u001f]/.test(t)) return "control characters are not allowed";
  if (t.length > 1000) return "too long";
  if (f === "year" && t && !/^\d{4}(-\d{2}(-\d{2})?)?$/.test(t)) return "year must look like 2004 or 2004-03-15";
  if (f === "series_num" && t && !/^\d+(\.\d+)?$/.test(t)) return "series number must be a number such as 2 or 1.5";
  return "";
}
const rowProblems = (r) => dirtyFields(r).filter(f => problem(f, r.cur[f]));

function fmtDur(s) {
  s = Math.round(s || 0);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60;
  return h + ":" + String(m).padStart(2, "0") + ":" + String(x).padStart(2, "0");
}

/* ---------- view ---------- */
function visible() {
  const q = S.filter.trim().toLowerCase();
  let rows = S.rows;
  if (q) rows = rows.filter(r => (r.rec.path + "\n" + FIELDS.map(f => r.cur[f]).join("\n")).toLowerCase().includes(q));
  const k = S.sortKey, d = S.sortDir;
  const val = (r) => k === "path" ? r.rec.path : (k === "duration" ? r.rec.duration : r.cur[k]);
  return rows.slice().sort((a, b) => {
    const x = val(a), y = val(b);
    if (typeof x === "number") return (x - y) * d || collator.compare(a.rec.path, b.rec.path);
    if (x === "" && y !== "") return 1;
    if (y === "" && x !== "") return -1;
    return collator.compare(x, y) * d || collator.compare(a.rec.path, b.rec.path);
  });
}

function buildHead() {
  const tr = $("head");
  tr.textContent = "";
  const mk = (label, key, cls, w) => {
    const th = document.createElement("th");
    th.textContent = label;
    if (cls) th.className = cls;
    if (w) th.style.minWidth = w + "px";
    if (key) { th.dataset.k = key; th.tabIndex = 0; th.setAttribute("role", "columnheader"); }
    tr.appendChild(th);
    return th;
  };
  const cb = mk("", null, "cb nosort");
  const all = document.createElement("input");
  all.type = "checkbox"; all.id = "selall"; all.setAttribute("aria-label", "Select all visible rows");
  cb.appendChild(all);
  mk("File", "path", "", 260);
  COLS.forEach(c => mk(c.label, c.key, "", c.w));
  mk("Length", "duration", "", 80);
  mk("Chapters", null, "nosort", 70);
  mk("Cover", null, "nosort", 60);
}

function updateHead() {
  document.querySelectorAll("#head th[data-k]").forEach(th => {
    const on = th.dataset.k === S.sortKey;
    const base = th.dataset.base || (th.dataset.base = th.textContent);
    th.textContent = base + (on ? (S.sortDir > 0 ? " ▲" : " ▼") : "");
    th.setAttribute("aria-sort", on ? (S.sortDir > 0 ? "ascending" : "descending") : "none");
  });
  const all = $("selall");
  if (all) {
    const v = S.vis.filter(r => !r.rec.error);
    all.checked = v.length > 0 && v.every(r => r.sel);
  }
}

function td(cls) {
  const el = document.createElement("td");
  if (cls) el.className = cls;
  return el;
}

function rowEl(r, i) {
  const tr = document.createElement("tr");
  tr._row = r;
  tr.className = (r.sel ? "sel " : "") + (r.rec.error || r.msg ? "err " : "");
  const c0 = td("cb");
  const cb = document.createElement("input");
  cb.type = "checkbox"; cb.checked = r.sel; cb.dataset.act = "sel";
  cb.disabled = !!r.rec.error;
  cb.setAttribute("aria-label", "Select " + r.rec.name);
  c0.appendChild(cb);
  tr.appendChild(c0);

  const cp = td("path");
  const n = document.createElement("span"); n.className = "name"; n.textContent = r.rec.name;
  cp.title = r.rec.path;
  cp.appendChild(n);
  if (r.rec.dir) {
    const d = document.createElement("span"); d.className = "dir"; d.textContent = r.rec.dir;
    cp.appendChild(d);
  }
  const msg = r.rec.error ? ("Unreadable: " + r.rec.error) : r.msg;
  if (msg) {
    const m = document.createElement("span"); m.className = "msg"; m.textContent = msg;
    cp.appendChild(m);
  }
  tr.appendChild(cp);

  COLS.forEach(c => {
    const cell = td();
    const inp = document.createElement("input");
    inp.type = "text"; inp.value = r.cur[c.key]; inp.dataset.f = c.key;
    inp.spellcheck = false; inp.autocomplete = "off";
    inp.disabled = !!r.rec.error || S.readOnly;
    inp.setAttribute("aria-label", c.label + ": " + r.rec.name);
    if (isDirtyField(r, c.key)) cell.classList.add("dirty");
    if (isDirtyField(r, c.key) && problem(c.key, r.cur[c.key])) { cell.classList.add("invalid"); cell.title = problem(c.key, r.cur[c.key]); }
    cell.appendChild(inp);
    tr.appendChild(cell);
  });

  const len = td("info"); len.textContent = fmtDur(r.rec.duration); tr.appendChild(len);
  const chp = td("info"); chp.textContent = r.rec.chapters ? String(r.rec.chapters) : "–"; tr.appendChild(chp);
  const cov = td("info"); cov.textContent = r.rec.cover ? "yes" : "–"; tr.appendChild(cov);
  return tr;
}

function render() {
  S.vis = visible();
  const tb = $("grid").tBodies[0];
  tb.textContent = "";
  const frag = document.createDocumentFragment();
  S.vis.forEach((r, i) => frag.appendChild(rowEl(r, i)));
  tb.appendChild(frag);
  updateHead();
  updateCounts();
}

function updateCounts() {
  const dirty = S.rows.filter(r => dirtyFields(r).length);
  const bad = S.rows.filter(r => rowProblems(r).length);
  const nfields = dirty.reduce((n, r) => n + dirtyFields(r).length, 0);
  const sel = S.vis.filter(r => r.sel).length;
  const save = $("save");
  save.textContent = dirty.length ? ("Save " + dirty.length + (dirty.length === 1 ? " file" : " files")) : "Save";
  save.disabled = S.busy || S.readOnly || !dirty.length || bad.length > 0;
  save.title = bad.length ? "Fix the highlighted invalid cells first" : (nfields + " changed value" + (nfields === 1 ? "" : "s"));
  $("undo").disabled = S.busy || S.readOnly;
  $("bset").disabled = $("breplace").disabled = $("bcopy").disabled = $("brevsel").disabled = S.readOnly || sel === 0;
  $("brevall").disabled = S.readOnly || dirty.length === 0;
  const parts = [S.vis.length + (S.vis.length === S.rows.length ? "" : " of " + S.rows.length) + " files"];
  if (sel) parts.push(sel + " selected");
  if (dirty.length) parts.push(dirty.length + " unsaved");
  $("count").textContent = parts.join(" · ");
}

/* ---------- editing ---------- */
const tbody = () => $("grid").tBodies[0];

function onCellChange(inp) {
  const tr = inp.closest("tr"), r = tr._row, f = inp.dataset.f;
  r.cur[f] = inp.value;
  const cell = inp.parentElement;
  const dirty = isDirtyField(r, f), p = dirty ? problem(f, r.cur[f]) : "";
  cell.classList.toggle("dirty", dirty && !p);
  cell.classList.toggle("invalid", !!p);
  cell.title = p;
  updateCounts();
}

function refreshRowCells(tr) {
  const r = tr._row;
  tr.querySelectorAll("input[data-f]").forEach(inp => {
    inp.value = r.cur[inp.dataset.f];
    const f = inp.dataset.f, cell = inp.parentElement;
    const dirty = isDirtyField(r, f), p = dirty ? problem(f, r.cur[f]) : "";
    cell.classList.toggle("dirty", dirty && !p);
    cell.classList.toggle("invalid", !!p);
    cell.title = p;
  });
}

function wireTable() {
  const tb = tbody();
  tb.addEventListener("input", (e) => {
    const inp = e.target;
    if (inp instanceof HTMLInputElement && inp.dataset.f) onCellChange(inp);
  });
  tb.addEventListener("change", (e) => {
    const inp = e.target;
    if (inp instanceof HTMLInputElement && inp.dataset.f && inp.value !== inp.value.trim()) {
      inp.value = inp.value.trim();
      onCellChange(inp);
    }
  });
  tb.addEventListener("keydown", (e) => {
    const inp = e.target;
    if (!(inp instanceof HTMLInputElement) || !inp.dataset.f) return;
    const tr = inp.closest("tr");
    let step = 0;
    if (e.key === "ArrowDown" || (e.key === "Enter" && !e.shiftKey)) step = 1;
    else if (e.key === "ArrowUp" || (e.key === "Enter" && e.shiftKey)) step = -1;
    else if (e.key === "Escape") {
      inp.value = tr._row.rec[inp.dataset.f] || "";
      onCellChange(inp);
      return;
    }
    if (!step) return;
    e.preventDefault();
    const next = tb.rows[tr.sectionRowIndex + step];
    if (!next) return;
    const t = next.querySelector('input[data-f="' + inp.dataset.f + '"]');
    if (t && !t.disabled) { t.focus(); t.select(); }
  });
  tb.addEventListener("click", (e) => {
    const cb = e.target;
    if (!(cb instanceof HTMLInputElement) || cb.dataset.act !== "sel") return;
    const tr = cb.closest("tr"), idx = tr.sectionRowIndex;
    if (e.shiftKey && S.last !== null && S.last < S.vis.length) {
      const [a, b] = [Math.min(S.last, idx), Math.max(S.last, idx)];
      for (let i = a; i <= b; i++) {
        if (S.vis[i].rec.error) continue;
        S.vis[i].sel = cb.checked;
        const row = tb.rows[i];
        row.classList.toggle("sel", cb.checked);
        row.querySelector('input[data-act="sel"]').checked = cb.checked;
      }
    } else {
      tr._row.sel = cb.checked;
      tr.classList.toggle("sel", cb.checked);
    }
    S.last = idx;
    updateHead();
    updateCounts();
  });
  $("head").addEventListener("click", (e) => {
    if (e.target.id === "selall") {
      const on = e.target.checked;
      S.vis.forEach(r => { if (!r.rec.error) r.sel = on; });
      render();
      return;
    }
    const th = e.target.closest("th[data-k]");
    if (!th) return;
    if (S.sortKey === th.dataset.k) S.sortDir = -S.sortDir; else { S.sortKey = th.dataset.k; S.sortDir = 1; }
    render();
  });
  $("head").addEventListener("keydown", (e) => {
    if ((e.key === "Enter" || e.key === " ") && e.target.matches("th[data-k]")) { e.preventDefault(); e.target.click(); }
  });
}

/* ---------- bulk tools ---------- */
const targets = () => S.vis.filter(r => r.sel && !r.rec.error);

function bulkApply(fn, doneMsg) {
  const ts = targets();
  if (!ts.length) { status("Select some rows first (checkboxes, shift-click for a range).", ""); return; }
  let n = 0;
  ts.forEach(r => { if (fn(r)) n++; });
  const sortAffected = S.sortKey === $("bfield").value;
  if (sortAffected) render(); else ts.forEach(r => { const i = S.vis.indexOf(r); if (i >= 0) refreshRowCells(tbody().rows[i]); });
  updateCounts();
  status(doneMsg(n, ts.length), n ? "good" : "");
}

function wireBulk() {
  const opts = (sel) => COLS.forEach(c => { const o = document.createElement("option"); o.value = c.key; o.textContent = c.label; sel.appendChild(o); });
  opts($("bfield")); opts($("bfrom"));
  $("bfrom").value = "title"; $("bfield").value = "album";

  $("bset").onclick = () => {
    const f = $("bfield").value, v = $("bvalue").value.trim();
    bulkApply(r => { if (r.cur[f] === v) return false; r.cur[f] = v; return true; },
              (n, t) => LABEL[f] + " set on " + n + " of " + t + " selected files.");
  };
  $("breplace").onclick = () => {
    const f = $("bfield").value, find = $("bfind").value, rep = $("brepl").value;
    if (!find) { status("Enter the text to find.", ""); return; }
    let re;
    try {
      re = $("bregex").checked ? new RegExp(find, "g") : new RegExp(find.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "g");
    } catch (err) { status("Bad regular expression: " + err.message, "bad"); return; }
    const literal = !$("bregex").checked;
    bulkApply(r => {
      const nv = literal ? r.cur[f].replace(re, () => rep) : r.cur[f].replace(re, rep);
      if (nv === r.cur[f]) return false;
      r.cur[f] = nv.trim();
      return true;
    }, (n, t) => LABEL[f] + ": replaced in " + n + " of " + t + " selected files.");
  };
  $("bcopy").onclick = () => {
    const f = $("bfield").value, from = $("bfrom").value;
    if (f === from) { status("Choose a different source field.", ""); return; }
    bulkApply(r => { const v = r.cur[from]; if (r.cur[f] === v) return false; r.cur[f] = v; return true; },
              (n, t) => "Copied " + LABEL[from] + " into " + LABEL[f] + " on " + n + " of " + t + " selected files.");
  };
  const revert = (rows) => {
    rows.forEach(r => FIELDS.forEach(f => { r.cur[f] = r.rec[f] || ""; }));
    render();
  };
  $("brevsel").onclick = () => { revert(targets()); status("Reverted selected rows.", ""); };
  $("brevall").onclick = () => {
    if (confirm("Discard all unsaved changes?")) { revert(S.rows); status("Reverted all unsaved changes.", ""); }
  };
}

/* ---------- load / save / undo ---------- */
function setBusy(b) {
  S.busy = b;
  document.body.classList.toggle("busy", b);
  updateCounts();
}

const anyDirty = () => S.rows.some(r => dirtyFields(r).length);

async function load() {
  setBusy(true);
  status("Scanning...", "");
  try {
    const data = await api("/api/scan");
    S.readOnly = !!data.read_only;
    $("root").textContent = data.root;
    $("root").title = data.root;
    S.rows = data.rows.map(mkRow);
    S.last = null;
    render();
    const errs = S.rows.filter(r => r.rec.error).length;
    status(S.rows.length + " audio files found" + (errs ? (", " + errs + " unreadable") : "") +
           (S.readOnly ? " (read-only mode)." : ". Click a cell to edit; Enter moves down."), errs ? "bad" : "");
  } catch (e) {
    S.rows = []; render();
    status(String(e.message || e), "bad");
  } finally {
    setBusy(false);
  }
}

function applyResults(results) {
  const byPath = new Map(S.rows.map(r => [r.rec.path, r]));
  let ok = 0, bad = 0;
  for (const x of results) {
    const r = byPath.get(x.path);
    if (!r) continue;
    if (x.ok) {
      r.rec = x.row;
      FIELDS.forEach(f => { r.cur[f] = x.row[f] || ""; });
      r.msg = ""; ok++;
    } else {
      r.msg = x.error || "failed"; bad++;
    }
  }
  return {ok, bad};
}

async function save() {
  const items = [];
  for (const r of S.rows) {
    const df = dirtyFields(r);
    if (!df.length) continue;
    const changes = {};
    df.forEach(f => { changes[f] = {old: r.rec[f] || "", new: r.cur[f]}; });
    items.push({path: r.rec.path, changes});
  }
  if (!items.length) return;
  setBusy(true);
  status("Saving " + items.length + (items.length === 1 ? " file..." : " files..."), "");
  try {
    S.rows.forEach(r => { r.msg = ""; });
    const res = await api("/api/save", {items});
    const {ok, bad} = applyResults(res.results);
    render();
    status("Saved " + ok + (ok === 1 ? " file" : " files") + (bad ? (". " + bad + " failed - see the red rows.") : "."), bad ? "bad" : "good");
  } catch (e) {
    status("Save failed: " + (e.message || e), "bad");
  } finally {
    setBusy(false);
  }
}

async function undo() {
  if (anyDirty() && !confirm("You have unsaved edits. Undoing the last save will not touch them, but they may no longer apply. Continue?")) return;
  if (!confirm("Restore the tags that the previous save overwrote?")) return;
  setBusy(true);
  try {
    const res = await api("/api/undo", {});
    const {ok, bad} = applyResults(res.results);
    render();
    status("Undid " + ok + (ok === 1 ? " file" : " files") + (bad ? (". " + bad + " could not be restored (changed since) - see the red rows.") : "."), bad ? "bad" : "good");
  } catch (e) {
    status("Undo failed: " + (e.message || e), "bad");
  } finally {
    setBusy(false);
  }
}

/* ---------- start ---------- */
(function addCount() {
  const c = document.createElement("span");
  c.id = "count"; c.className = "dim";
  $("filter").before(c);
})();
buildHead();
wireTable();
wireBulk();
let ft = null;
$("filter").addEventListener("input", (e) => {
  clearTimeout(ft);
  ft = setTimeout(() => { S.filter = e.target.value; render(); }, 120);
});
$("save").onclick = save;
$("undo").onclick = undo;
$("reload").onclick = () => { if (!anyDirty() || confirm("Discard unsaved changes and rescan?")) load(); };
window.addEventListener("beforeunload", (e) => { if (anyDirty()) { e.preventDefault(); e.returnValue = ""; } });
load();
})();
</script>
</body>
</html>
"""
