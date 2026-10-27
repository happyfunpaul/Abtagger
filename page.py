from settings import DEFAULT_RENAME_TEMPLATE

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
label.chk{display:flex;gap:4px;align-items:center;white-space:nowrap}
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
td.path{padding:4px 8px;min-width:16rem;max-width:26rem;overflow:hidden}
td.path .name{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
td.path .dir{display:block;font-size:12px;color:var(--dim);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;direction:rtl;text-align:left}
td.path .msg{display:block;font-size:12px;color:var(--bad);white-space:normal}
td input[type=text]{width:100%;border:0;background:transparent;color:inherit;font:inherit;padding:7px 8px;border-radius:0;min-width:3rem}
td input[type=text]:focus{outline:2px solid var(--accent);outline-offset:-2px;background:var(--panel)}
td input[type=text]:disabled{color:var(--dim)}
td.dirty{background:var(--dirty);box-shadow:inset 3px 0 0 var(--dirty-line)}
td.invalid{background:var(--badbg);box-shadow:inset 3px 0 0 var(--bad)}
td.info{padding:4px 8px;color:var(--dim);white-space:nowrap;font-variant-numeric:tabular-nums;font-size:13px}
td input[type=text].mixed{color:var(--dim);font-style:italic}
.badge{display:inline-block;margin-left:6px;padding:0 6px;border:1px solid var(--line);border-radius:9px;background:var(--sel);font-size:11px;font-weight:600;line-height:1.5;vertical-align:1px}
.expander{border:0;background:transparent;padding:0 5px 0 0;color:var(--dim);font-size:12px;line-height:1;cursor:pointer}
.expander:hover:not(:disabled){background:transparent;color:var(--ink)}
tr.book td.path .bookline{display:flex;align-items:center;min-width:0}
tr.book td.path .bookline .name{flex:0 1 auto;min-width:0}
tr.book td.path .bookline .expander,tr.book td.path .bookline .badge{flex:0 0 auto}
tr.child td.path{padding-left:2.6rem;position:relative}
tr.child td.path::before{content:"↳";position:absolute;left:1.05rem;color:var(--dim)}
tr.child td.path .dir{display:none}
.busy .wrap{pointer-events:none;opacity:.6}
@media (max-width:700px){header .title #root{display:none}}
</style>
</head>
<body>
<header>
  <div class="title"><strong>abtagger</strong><span id="root" class="dim"></span></div>
  <div class="spacer"></div>
  <label class="chk" title="One row per book; expand a book to edit its individual files"><input id="groupbooks" type="checkbox"> Book view</label>
  <input id="filter" type="search" placeholder="Filter rows..." aria-label="Filter rows" autocomplete="off">
  <button id="reload" type="button">Reload</button>
  <button id="undo" type="button" title="Restore the tags overwritten by the previous save">Undo last save</button>
  <button id="settings" type="button" title="Settings">Settings</button>
  <button id="help" type="button" title="Template help">?</button>
  <button id="absscan" type="button" title="Trigger an Audiobookshelf library scan for this folder">Scan ABS</button>
  <button id="absclean" type="button" title="Remove Audiobookshelf items marked missing for this folder">Clean missing (ABS)</button>
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
    <button id="bdelete" type="button" style="color:var(--bad)">Delete selected</button>
    <button id="brename" type="button">Rename selected</button>
    <button id="btitlefn" type="button">Title from filename</button>
  </div>
</section>
<div id="status" role="status" aria-live="polite"></div>
<div id="helpmodal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:10;align-items:center;justify-content:center">
  <div style="background:var(--panel);padding:16px;border-radius:8px;max-width:36rem;width:90%;max-height:80vh;overflow:auto;font-size:13px">
    <h3 style="margin:0 0 8px">Rename template language</h3>
    <p>Placeholders in <code>{ }</code> are replaced with the tag value. Wrap optional parts in <code>[ ]</code>: a bracket is emitted only if every placeholder inside it is non-empty.</p>
    <p><strong>Fields:</strong> {title} (book title), {subtitle}, {track_title} (per-file title), {album} (alias for book title), {author}, {author_first}, {author_last}, {narrator}, {series}, {series_num}, {year}, {genre}, {filename}, {stem}, {ext}</p>
    <p>In the grid, the <strong>Title</strong> column shows the book title in book rows and the per-file track title in expanded/file rows.</p>
    <p><strong>Examples:</strong></p>
    <pre style="background:var(--bg);padding:8px;border-radius:4px;overflow:auto">{author_last}, {author_first}/[{series}/][{series_num} - ]{title}</pre>
    <p>Standalone book (no series) becomes <code>James, Aaron/Assholes.m4b</code>; a series book becomes <code>James, Aaron/Stormlight Archive/1 - The Way of Kings.m4b</code>.</p>
    <pre style="background:var(--bg);padding:8px;border-radius:4px;overflow:auto">{author_last}, {author_first}/[{series}/][{series_num} - ]{title}/{title}</pre>
    <p>Adds a folder per book (last component is the filename).</p>
    <p>Use <code>/</code> to create folders. Illegal filename characters are sanitized.</p>
    <div style="display:flex;justify-content:flex-end"><button id="h_close" type="button">Close</button></div>
  </div>
</div>
<div id="modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:10;align-items:center;justify-content:center">
  <div style="background:var(--panel);padding:16px;border-radius:8px;max-width:32rem;width:90%;max-height:80vh;overflow:auto">
    <h3 style="margin:0 0 8px">Settings</h3>
    <label>ABS URL<br><input id="s_abs_url" type="text" autocomplete="off" spellcheck="false" style="width:100%"></label><br><br>
    <label>ABS token<br><input id="s_abs_token" type="text" autocomplete="off" spellcheck="false" style="width:100%"></label><br><br>
    <label>ABS library id (optional)<br><input id="s_abs_lib" type="text" autocomplete="off" spellcheck="false" style="width:100%"></label><br><br>
    <label>Rename template (see ? for fields)<br><input id="s_template" type="text" autocomplete="off" spellcheck="false" style="width:100%"></label><br>
    <button id="s_default" type="button" title="Restore the built-in rename format">Use default</button><br><br>
    <div style="display:flex;gap:8px;justify-content:flex-end">
      <button id="s_cancel" type="button">Cancel</button>
      <button id="s_save" type="button" class="primary">Save</button>
    </div>
  </div>
</div>
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
  {key:"title", label:"Title", w:240, bookField:"album", fileField:"title",
   hint:"Book title in book rows; per-file track title in expanded/file rows"},
  {key:"subtitle", label:"Subtitle", w:180},
  {key:"author", label:"Author", w:170},
  {key:"narrator", label:"Narrator", w:150},
  {key:"series", label:"Series", w:190},
  {key:"series_num", label:"#", w:64},
  {key:"year", label:"Year", w:90},
  {key:"genre", label:"Genre", w:120},
];
const BULK_FIELDS = [
  {key:"album", label:"Book title"},
  {key:"subtitle", label:"Subtitle"},
  {key:"title", label:"Track title"},
  {key:"author", label:"Author"},
  {key:"narrator", label:"Narrator"},
  {key:"series", label:"Series"},
  {key:"series_num", label:"Series #"},
  {key:"year", label:"Year"},
  {key:"genre", label:"Genre"},
];
const FIELDS = BULK_FIELDS.map(f => f.key);
const LABEL = Object.fromEntries(BULK_FIELDS.map(f => [f.key, f.label]));
const $ = (id) => document.getElementById(id);
const collator = new Intl.Collator(undefined, {numeric: true, sensitivity: "base"});
const DEFAULT_TEMPLATE = "__DEFAULT_RENAME_TEMPLATE__";
const S = {rows: [], vis: [], books: [], visBooks: [], sortKey: "path", sortDir: 1,
           filter: "", last: null, lastBook: null, readOnly: false, busy: false,
           view: "books", expanded: new Set()};
try {
  const storedView = localStorage.getItem("abtagger-view");
  if (storedView === "files" || storedView === "books") S.view = storedView;
} catch (e) { /* storage unavailable */ }

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

/* ---------- book grouping ---------- */
function mkBook(rows) {
  const id = rows[0].rec.path;
  return {id, rows, count: rows.length, expanded: S.expanded.has(id)};
}

function buildBooks() {
  const groups = new Map();
  for (const r of S.rows) {
    const k = r.rec.book_key || ("path:" + r.rec.path);
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(r);
  }
  S.books = [...groups.values()].map(mkBook);
  S.lastBook = null;
}

function commonField(book, f) {
  let v = null, mixed = false;
  for (const r of book.rows) {
    const x = r.cur[f] || "";
    if (v === null) v = x;
    else if (x !== v) { mixed = true; break; }
  }
  return {value: mixed ? "" : (v || ""), mixed};
}

function commonDir(book) {
  const dirs = book.rows.map(r => r.rec.dir);
  if (!dirs.length) return "";
  let prefix = dirs[0];
  for (const d of dirs.slice(1)) {
    while (prefix && d !== prefix && !d.startsWith(prefix + "/")) {
      prefix = prefix.includes("/") ? prefix.slice(0, prefix.lastIndexOf("/")) : "";
    }
  }
  return prefix;
}

function bookTitle(book) {
  if (book.count === 1) return book.rows[0].rec.name;
  const album = commonField(book, "album");
  if (!album.mixed && album.value) return album.value;
  const title = commonField(book, "title");
  if (!title.mixed && title.value) return title.value;
  const dir = commonDir(book);
  if (dir) return dir.split("/").pop();
  return "Untitled book";
}

function bookState(book, f) {
  let dirty = false, invalid = false, msg = "";
  for (const r of book.rows) {
    if (!isDirtyField(r, f)) continue;
    dirty = true;
    const p = problem(f, r.cur[f]);
    if (p) { invalid = true; if (!msg) msg = p; }
  }
  return {dirty, invalid, msg};
}

function bookValue(book, k) {
  if (k === "path") return bookTitle(book);
  if (k === "title") k = "album";  // book rows show the book title in the Title column
  if (k === "duration") return book.rows.reduce((n, r) => n + (r.rec.duration || 0), 0);
  const c = commonField(book, k);
  return c.mixed ? "" : c.value;
}

function visibleBooks() {
  const q = S.filter.trim().toLowerCase();
  let books = S.books;
  if (q) books = books.filter(b => b.rows.some(r =>
    (r.rec.path + "\n" + FIELDS.map(f => r.cur[f]).join("\n")).toLowerCase().includes(q)));
  const k = S.sortKey, d = S.sortDir;
  return books.slice().sort((a, b) => {
    const x = bookValue(a, k), y = bookValue(b, k);
    if (typeof x === "number") return (x - y) * d || collator.compare(a.rows[0].rec.path, b.rows[0].rec.path);
    if (x === "" && y !== "") return 1;
    if (y === "" && x !== "") return -1;
    return collator.compare(x, y) * d || collator.compare(a.rows[0].rec.path, b.rows[0].rec.path);
  });
}

function refreshBookPath(tr, book) {
  const cp = tr.querySelector("td.path");
  if (!cp) return;
  const n = cp.querySelector(".name");
  if (n) n.textContent = bookTitle(book);
  cp.title = book.rows.map(r => r.rec.path).join("\n") +
    (book.count > 1 ? "\n\nEdits here apply to all " + book.count + " files." : "");
}

function refreshBookCells(tr, book) {
  tr.querySelectorAll("input[data-bf]").forEach(inp => {
    const f = inp.dataset.bf, c = commonField(book, f), st = bookState(book, f);
    inp.value = c.value;
    inp.classList.toggle("mixed", c.mixed);
    inp.placeholder = c.mixed ? "— mixed —" : "";
    const cell = inp.parentElement;
    cell.classList.toggle("dirty", st.dirty && !st.invalid);
    cell.classList.toggle("invalid", st.invalid);
    cell.title = st.msg;
  });
  refreshBookPath(tr, book);
}

function onBookChange(inp) {
  const tr = inp.closest("tr"), book = tr._book, f = inp.dataset.bf;
  for (const r of book.rows) if (!r.rec.error) r.cur[f] = inp.value;
  inp.classList.remove("mixed");
  inp.placeholder = "";
  const st = bookState(book, f), cell = inp.parentElement;
  cell.classList.toggle("dirty", st.dirty && !st.invalid);
  cell.classList.toggle("invalid", st.invalid);
  cell.title = st.msg;
  let sib = tr.nextElementSibling;
  while (sib && sib.classList.contains("child")) {
    if (sib._row) refreshRowCells(sib);
    sib = sib.nextElementSibling;
  }
  refreshBookPath(tr, book);
  updateCounts();
}

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
  COLS.forEach(c => {
    const th = mk(c.label, c.key, "", c.w);
    if (c.hint) th.title = c.hint;
  });
  mk("Length", "duration", "", 80);
  mk("Chapters", null, "nosort", 70);
  mk("Cover", null, "nosort", 60);
}

function updateHead() {
  const pathTh = document.querySelector('#head th[data-k="path"]');
  if (pathTh) pathTh.dataset.base = S.view === "books" ? "Book" : "File";
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

function rowEl(r, i, child) {
  const tr = document.createElement("tr");
  tr._row = r;
  tr.className = (child ? "child " : "") + (r.sel ? "sel " : "") + (r.rec.error || r.msg ? "err " : "");
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
    const f = c.fileField || c.key;
    const cell = td();
    const inp = document.createElement("input");
    inp.type = "text"; inp.value = r.cur[f]; inp.dataset.f = f;
    inp.spellcheck = false; inp.autocomplete = "off";
    inp.disabled = !!r.rec.error || S.readOnly;
    inp.setAttribute("aria-label", c.label + ": " + r.rec.name);
    if (isDirtyField(r, f)) cell.classList.add("dirty");
    if (isDirtyField(r, f) && problem(f, r.cur[f])) { cell.classList.add("invalid"); cell.title = problem(f, r.cur[f]); }
    cell.appendChild(inp);
    tr.appendChild(cell);
  });

  const len = td("info"); len.textContent = fmtDur(r.rec.duration); tr.appendChild(len);
  const chp = td("info"); chp.textContent = r.rec.chapters ? String(r.rec.chapters) : "–"; tr.appendChild(chp);
  const cov = td("info"); cov.textContent = r.rec.cover ? "yes" : "–"; tr.appendChild(cov);
  return tr;
}

function bookEl(book, i) {
  const tr = document.createElement("tr");
  tr._book = book;
  tr.className = "book";
  const selectable = book.rows.filter(r => !r.rec.error);
  const allSel = selectable.length > 0 && selectable.every(r => r.sel);
  const someSel = selectable.some(r => r.sel);
  const errCount = book.rows.length - selectable.length;
  const msgs = book.rows.map(r => r.msg).filter(Boolean);
  if (allSel) tr.classList.add("sel");
  if (errCount || msgs.length) tr.classList.add("err");

  const c0 = td("cb");
  const cb = document.createElement("input");
  cb.type = "checkbox"; cb.checked = allSel; cb.indeterminate = someSel && !allSel;
  cb.dataset.act = "bsel";
  cb.disabled = book.rows.every(r => r.rec.error);
  cb.setAttribute("aria-label", "Select book " + bookTitle(book));
  c0.appendChild(cb);
  tr.appendChild(c0);

  const cp = td("path");
  const paths = book.rows.map(r => r.rec.path);
  cp.title = paths.join("\n") + (book.count > 1 ? "\n\nEdits here apply to all " + book.count + " files." : "");
  const line = document.createElement("div");
  line.className = "bookline";
  if (book.count > 1) {
    const ex = document.createElement("button");
    ex.type = "button"; ex.className = "expander"; ex.dataset.act = "expand";
    ex.textContent = book.expanded ? "▾" : "▸";
    ex.setAttribute("aria-expanded", String(book.expanded));
    ex.title = book.expanded ? "Hide individual files" : "Show individual files";
    ex.setAttribute("aria-label", (book.expanded ? "Collapse " : "Expand ") + book.count + " files in " + bookTitle(book));
    line.appendChild(ex);
  }
  const n = document.createElement("span"); n.className = "name"; n.textContent = bookTitle(book);
  line.appendChild(n);
  if (book.count > 1) {
    const badge = document.createElement("span");
    badge.className = "badge"; badge.textContent = book.count + " files";
    line.appendChild(badge);
  }
  cp.appendChild(line);
  const dir = book.count === 1 ? book.rows[0].rec.dir : commonDir(book);
  if (dir) {
    const d = document.createElement("span"); d.className = "dir"; d.textContent = dir;
    cp.appendChild(d);
  }
  const msgParts = [];
  if (errCount) msgParts.push(errCount + " unreadable file" + (errCount === 1 ? "" : "s") +
                             (book.count > errCount ? " - expand to edit the rest" : ""));
  if (msgs.length) msgParts.push(msgs[0]);
  if (msgParts.length) {
    const m = document.createElement("span"); m.className = "msg"; m.textContent = msgParts.join("; ");
    cp.appendChild(m);
  }
  tr.appendChild(cp);

  const canEditBook = book.rows.length > 0 && !S.readOnly && book.rows.every(r => !r.rec.error);
  COLS.forEach(c => {
    const f = c.bookField || c.key;
    const cell = td();
    const common = commonField(book, f);
    const st = bookState(book, f);
    const inp = document.createElement("input");
    inp.type = "text"; inp.value = common.value; inp.dataset.bf = f;
    inp.spellcheck = false; inp.autocomplete = "off";
    inp.disabled = !canEditBook;
    inp.classList.toggle("mixed", common.mixed);
    if (common.mixed) inp.placeholder = "— mixed —";
    if (st.dirty) cell.classList.add("dirty");
    if (st.invalid) { cell.classList.add("invalid"); cell.title = st.msg; }
    inp.setAttribute("aria-label", c.label + " for book " + bookTitle(book) +
                     (common.mixed ? " (files have different values)" : ""));
    if (common.mixed) inp.title = "Files have different values; typing here sets all " + book.count + " files";
    cell.appendChild(inp);
    tr.appendChild(cell);
  });

  const len = td("info");
  len.textContent = fmtDur(book.rows.reduce((sum, r) => sum + (r.rec.duration || 0), 0));
  tr.appendChild(len);
  const chp = td("info");
  const chapters = book.rows.reduce((sum, r) => sum + (r.rec.chapters || 0), 0);
  chp.textContent = chapters ? String(chapters) : "–";
  tr.appendChild(chp);
  const cov = td("info");
  cov.textContent = book.rows.some(r => r.rec.cover) ? "yes" : "–";
  tr.appendChild(cov);
  return tr;
}

function render() {
  if (S.view === "books") {
    S.visBooks = visibleBooks();
    S.vis = S.visBooks.flatMap(b => b.rows);
  } else {
    S.visBooks = [];
    S.vis = visible();
  }
  const tb = $("grid").tBodies[0];
  tb.textContent = "";
  const frag = document.createDocumentFragment();
  if (S.view === "books") {
    S.visBooks.forEach((book, i) => {
      frag.appendChild(bookEl(book, i));
      if (book.expanded && book.count > 1) {
        book.rows.forEach(r => frag.appendChild(rowEl(r, i, true)));
      }
    });
  } else {
    S.vis.forEach((r, i) => frag.appendChild(rowEl(r, i)));
  }
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
  $("bset").disabled = $("breplace").disabled = $("bcopy").disabled = $("brevsel").disabled = $("bdelete").disabled = $("brename").disabled = $("btitlefn").disabled = S.readOnly || sel === 0;
  $("brevall").disabled = S.readOnly || dirty.length === 0;
  const parts = [];
  if (S.view === "books") {
    const shown = S.visBooks.length;
    const total = S.books.length;
    parts.push((shown === total ? total : shown + " of " + total) + " books");
  }
  parts.push(S.vis.length + (S.vis.length === S.rows.length ? "" : " of " + S.rows.length) + " files");
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
  if (S.view === "books" && tr.classList.contains("child")) {
    let p = tr.previousElementSibling;
    while (p && !p._book) p = p.previousElementSibling;
    if (p) refreshBookCells(p, p._book);
  }
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
    if (!(inp instanceof HTMLInputElement)) return;
    if (inp.dataset.bf) onBookChange(inp);
    else if (inp.dataset.f) onCellChange(inp);
  });
  tb.addEventListener("change", (e) => {
    const inp = e.target;
    if (!(inp instanceof HTMLInputElement)) return;
    if ((inp.dataset.f || inp.dataset.bf) && inp.value !== inp.value.trim()) {
      inp.value = inp.value.trim();
      if (inp.dataset.bf) onBookChange(inp); else onCellChange(inp);
    }
  });
  tb.addEventListener("keydown", (e) => {
    const inp = e.target;
    if (!(inp instanceof HTMLInputElement)) return;
    const f = inp.dataset.bf || inp.dataset.f;
    if (!f) return;
    const attr = inp.dataset.bf ? "bf" : "f";
    const tr = inp.closest("tr");
    let step = 0;
    if (e.key === "ArrowDown" || (e.key === "Enter" && !e.shiftKey)) step = 1;
    else if (e.key === "ArrowUp" || (e.key === "Enter" && e.shiftKey)) step = -1;
    else if (e.key === "Escape") {
      if (inp.dataset.bf) {
        const book = tr._book;
        book.rows.forEach(r => { r.cur[f] = r.rec[f] || ""; });
        render();
      } else {
        inp.value = tr._row.rec[f] || "";
        onCellChange(inp);
      }
      return;
    }
    if (!step) return;
    e.preventDefault();
    const rows = [...tb.rows], start = rows.indexOf(tr);
    for (let j = start + step; j >= 0 && j < rows.length; j += step) {
      const t = rows[j].querySelector('input[data-' + attr + '="' + f + '"]');
      if (t && !t.disabled) { t.focus(); t.select(); return; }
    }
  });
  tb.addEventListener("click", (e) => {
    const ex = e.target.closest && e.target.closest('button[data-act="expand"]');
    if (ex) {
      const book = ex.closest("tr")._book;
      if (S.expanded.has(book.id)) S.expanded.delete(book.id); else S.expanded.add(book.id);
      book.expanded = !book.expanded;
      render();
      return;
    }
    const cb = e.target;
    if (!(cb instanceof HTMLInputElement)) return;
    if (cb.dataset.act === "bsel") {
      const tr = cb.closest("tr"), book = tr._book;
      if (!book) return;
      const idx = S.visBooks.indexOf(book);
      if (e.shiftKey && S.lastBook !== null && S.lastBook < S.visBooks.length) {
        const [a, b] = [Math.min(S.lastBook, idx), Math.max(S.lastBook, idx)];
        for (let i = a; i <= b; i++) {
          S.visBooks[i].rows.forEach(r => { if (!r.rec.error) r.sel = cb.checked; });
        }
      } else {
        book.rows.forEach(r => { if (!r.rec.error) r.sel = cb.checked; });
      }
      S.lastBook = idx;
      render();
      return;
    }
    if (cb.dataset.act !== "sel") return;
    const tr = cb.closest("tr"), idx = tr.sectionRowIndex;
    if (S.view === "books") {
      tr._row.sel = cb.checked;
      S.lastBook = null;
      render();
      return;
    }
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
    S.last = null; S.lastBook = null;
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
  render();
  status(doneMsg(n, ts.length), n ? "good" : "");
}

function wireBulk() {
  const opts = (sel) => BULK_FIELDS.forEach(f => { const o = document.createElement("option"); o.value = f.key; o.textContent = f.label; sel.appendChild(o); });
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
  $("bdelete").onclick = async () => {
    const ts = targets();
    if (!ts.length) { status("Select some rows first.", ""); return; }
    if (!confirm("Permanently delete " + ts.length + " file(s) from disk? This cannot be undone.")) return;
    setBusy(true);
    try {
      const res = await api("/api/delete", {items: ts.map(r => ({path: r.rec.path}))});
      const bad = res.results.filter(x => !x.ok).length;
      await load();
      status("Deleted " + (ts.length - bad) + " file(s)." + (bad ? (" " + bad + " failed.") : ""), bad ? "bad" : "good");
    } catch (e) { status("Delete failed: " + (e.message || e), "bad"); }
    finally { setBusy(false); }
  };
  $("btitlefn").onclick = async () => {
    const ts = targets();
    if (!ts.length) { status("Select some rows first.", ""); return; }
    if (!confirm("Derive title from filename for " + ts.length + " selected file(s)?")) return;
    setBusy(true);
    try {
      const res = await api("/api/title-from-filename", {selected: ts.map(r => r.rec.path)});
      const bad = res.results.filter(x => !x.ok).length;
      await load();
      status("Derived titles for " + (res.results.length - bad) + " file(s)." + (bad ? (" " + bad + " failed.") : ""), bad ? "bad" : "good");
    } catch (e) { status("Failed: " + (e.message || e), "bad"); }
    finally { setBusy(false); }
  };
  $("brename").onclick = async (ev) => {
    const ts = targets();
    if (!ts.length) { status("Select some rows first.", ""); return; }
    let tmpl = (S.template || "");
    if (ev.shiftKey || !tmpl) {
      const p = prompt("Rename template (use {field}, [...] optional groups):", tmpl || DEFAULT_TEMPLATE);
      if (p === null) return;
      tmpl = p;
    }
    setBusy(true);
    try {
      const res = await api("/api/rename/plan", {template: tmpl, selected: ts.map(r => r.rec.path)});
      if (!res.items.length) { status("Nothing to rename.", ""); return; }
      const shown = res.items.slice(0, 6);
      const preview = shown.map((x, i) =>
        (i + 1) + ". " + x.src + "\n   -> " + x.dst
      ).join("\n");
      const more = res.items.length > shown.length
        ? "\n\n...and " + (res.items.length - shown.length) + " more"
        : "";
      const noun = res.items.length === 1 ? "file" : "files";
      if (!confirm("Rename " + res.items.length + " " + noun + "?\n\n" + preview + more)) return;
      const r2 = await api("/api/rename/apply", {items: res.items});
      const bad = r2.results.filter(x => !x.ok).length;
      await load();
      status("Renamed " + (res.items.length - bad) + " file(s)." + (bad ? (" " + bad + " failed.") : ""), bad ? "bad" : "good");
    } catch (e) { status("Rename failed: " + (e.message || e), "bad"); }
    finally { setBusy(false); }
  };
}

/* ---------- load / save / undo ---------- */
function setBusy(b) {
  S.busy = b;
  document.body.classList.toggle("busy", b);
  updateCounts();
}

const anyDirty = () => S.rows.some(r => dirtyFields(r).length);

function applySettings(s) {
  $("s_abs_url").value = s.abs_url || "";
  $("s_abs_token").value = s.abs_token || "";
  $("s_abs_lib").value = (s.abs_library_ids || []).join(",");
  const tmpl = (s.rename_template || "").trim() || DEFAULT_TEMPLATE;
  $("s_template").value = tmpl;
  S.template = tmpl;
}

async function refreshSettings() {
  try { applySettings(await api("/api/settings")); } catch (e) { /* ignore */ }
}

async function load() {
  setBusy(true);
  status("Scanning...", "");
  try {
    const data = await api("/api/scan");
    S.readOnly = !!data.read_only;
     $("absscan").disabled = !data.abs_configured;
     $("absclean").disabled = !data.abs_configured;
     await refreshSettings();
    $("root").textContent = data.root;
    $("root").title = data.root;
    S.rows = data.rows.map(mkRow);
    S.last = null;
    buildBooks();
    render();
    const errs = S.rows.filter(r => r.rec.error).length;
    const multi = S.books.filter(b => b.count > 1).length;
    const grouped = multi ? (" in " + S.books.length + " books (" + multi + " multi-file)") : "";
    status(S.rows.length + " audio files found" + grouped + (errs ? (", " + errs + " unreadable") : "") +
           (S.readOnly ? " (read-only mode)." : ". Click a cell to edit; Enter moves down."), errs ? "bad" : "");
  } catch (e) {
    S.rows = []; buildBooks(); render();
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
    buildBooks();
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
    buildBooks();
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
$("s_template").placeholder = DEFAULT_TEMPLATE;
$("groupbooks").checked = S.view === "books";
$("groupbooks").onchange = (e) => {
  S.view = e.target.checked ? "books" : "files";
  S.last = null; S.lastBook = null;
  try { localStorage.setItem("abtagger-view", S.view); } catch (err) { /* ignore */ }
  render();
  status(S.view === "books"
    ? "Book view: Title is the book title. Expand a row to edit per-file track titles."
    : "File view: one row per audio file. Title is that file's track title.", "");
};
$("settings").onclick = async () => {
  $("modal").style.display = "flex";
  await refreshSettings();
};
$("s_default").onclick = () => {
  $("s_template").value = DEFAULT_TEMPLATE;
  $("s_template").focus();
};
$("help").onclick = () => { $("helpmodal").style.display = "flex"; };
$("h_close").onclick = () => { $("helpmodal").style.display = "none"; };
$("s_cancel").onclick = () => { $("modal").style.display = "none"; };
$("s_save").onclick = async () => {
  setBusy(true);
  try {
    const payload = {
      abs_url: $("s_abs_url").value.trim(),
      abs_token: $("s_abs_token").value.trim(),
      abs_library_ids: $("s_abs_lib").value.split(",").map(s => s.trim()).filter(Boolean),
      rename_template: $("s_template").value.trim()
    };
    const s = await api("/api/settings", payload);
    applySettings(s);
    $("modal").style.display = "none";
    await load();
    status("Settings saved.", "good");
  } catch (e) { status("Settings save failed: " + (e.message || e), "bad"); }
  finally { setBusy(false); }
};
let ft = null;
$("filter").addEventListener("input", (e) => {
  clearTimeout(ft);
  ft = setTimeout(() => { S.filter = e.target.value; S.last = null; S.lastBook = null; render(); }, 120);
});
$("save").onclick = save;
$("undo").onclick = undo;
$("absscan").onclick = async () => {
  if (!confirm("Trigger an Audiobookshelf library scan for this folder?")) return;
  setBusy(true);
  try {
    const res = await api("/api/abs/scan", {});
    status("ABS scan triggered for library " + res.library_id + ".", "good");
  } catch (e) { status("ABS scan failed: " + (e.message || e), "bad"); }
  finally { setBusy(false); }
};
$("absclean").onclick = async () => {
  if (!confirm("Remove ABS items marked missing for this folder?")) return;
  setBusy(true);
  try {
    const res = await api("/api/abs/clean-missing", {});
    status("Removed " + (res.result.removed || 0) + " missing ABS item(s).", "good");
  } catch (e) { status("Clean failed: " + (e.message || e), "bad"); }
  finally { setBusy(false); }
};
$("reload").onclick = () => { if (!anyDirty() || confirm("Discard unsaved changes and rescan?")) load(); };
window.addEventListener("beforeunload", (e) => { if (anyDirty()) { e.preventDefault(); e.returnValue = ""; } });
load();
})();
</script>
</body>
</html>
"""

# Keep the UI's fallback in sync with settings.DEFAULT_RENAME_TEMPLATE.
PAGE = PAGE.replace("__DEFAULT_RENAME_TEMPLATE__", DEFAULT_RENAME_TEMPLATE)
