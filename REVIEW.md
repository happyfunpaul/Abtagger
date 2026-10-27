# abtagger - review, gotchas, and roadmap notes

## What was changed in this pass

- Added a declarative `FieldSpec` / `FIELD_SPECS` registry so the editable field set,
  labels, length limits, and validators live in one place. `FIELDS` is now derived
  from it. Adding a field (publisher, ISBN, language, ...) is now a one-line change
  plus read/write entries in the format backends.
- Added type hints and docstrings throughout the backend; made the global `STATE`
  explicitly optional and accessed via `_state()` so functions are easier to test
  (tests inject a `State`).
- Scan now runs under the state lock, closing a read/write race.
- `clean_value` now rejects unknown fields and routes validation through `FieldSpec`.
- Added `tests/test_abtagger.py` (unittest) covering validation, path safety, and
  MP3/M4A tag round-trips.
- No behavioural changes to the UI or tag mapping.

## Gotchas and difficult decisions ahead

1. **Undo is value-based, not byte-based.** Undo restores previous *tag values*, not
   the original file bytes. It cannot restore cover art, chapters, or tags the grid
   does not show, and it refuses to run if the file no longer holds exactly what the
   save wrote. For tag-only edits this is cheap and good enough; for rename/move
   or any destructive operation it is not. Plan: keep value-based undo for tag
   edits, add an optional full-file snapshot (copy original bytes to the state dir)
   for destructive operations, with a retention cap.

2. **Undo identity is a path, not a file.** If a file is renamed or moved, the
   undo log still points at the old path and silently no-ops. The log also keys
   its `root` on the absolute folder string, so moving the library folder invalidates
   all undo logs. Future: key libraries by a stable id and track files by inode/
   (device, ino) where the OS supports it.

3. **Tag mapping is intentionally redundant.** Series is written to iTunes freeform
   `SERIES`, `(c)mvn`, `MVNM`, and (if present) the Tone freeform atom, because
   different consumers (ABS, Apple Books, Tone) read different atoms. Every writer
   must keep all of them in step; forgetting one is a silent data-loss bug. The
   read side applies the same precedence. Do not "simplify" this without checking
   every consumer.

4. **`aART` (album artist) is auto-synced to `author`** unless it was deliberately
   different. This is a policy decision baked into `write_mp4`; make it explicit
   and configurable before adding a "preserve album-artist" option.

5. **`series_num` is stored twice** (freeform string + `(c)mvi` int) and `(c)mvi`
   is only written when the value is a whole number. Fractional parts (1.5) live
   only in the freeform atom. Consumers that read `(c)mvi` will see nothing for
   fractional books.

6. **Frontend validation is duplicated** from the backend (`problem()`). They must
   be kept in sync; a shared schema (JSON Schema) generated from `FIELD_SPECS`
   would remove this. Not done yet because it adds a build step to a zero-build UI.

7. **Scan is O(files) and holds the lock.** Fine for thousands of files, painful
   for tens of thousands, and it blocks saves while running. Virtualise/paginate
   the grid and consider an incremental scan or a background rescan before scaling.

8. **Book view is a grouping heuristic, not an identity.** `books.py` groups by
   album+author first, then filename part markers, then title, and folds `CD1` /
   `Disc 2` folders into their parent. That handles the common multi-part layouts,
   but a flat folder with missing tags, or two editions of the same book, can still
   be grouped wrongly or split. The UI mitigates this by showing a file count and
   expandable per-file rows. Selection, undo, and writes remain file-based: a book
   row is only a view over one or more file rows, and book-row edits fan out to
   every file in the group.

9. **Filesystem operations are not transactional.** A rename/move pass that fails
   halfway leaves a partial layout. Any future "layout to ABS-recommended structure"
   feature needs a journal + rollback and must never run without an explicit preview
   and confirmation.

10. **ABS integration is a boundary, not a merge.** ABS owns its database and
    sidecar JSON; this tool owns the audio files. Integration should be an adapter
    that (a) triggers an ABS library scan/rescan after our changes and (b) optionally
    pushes metadata through ABS's REST API. Do not write into ABS's database or
    sidecar files directly.

11. **Metadata fetch is the riskiest feature.** Matching by title/author is fuzzy
    and wrong matches corrupt tags. It needs a preview/diff screen, per-field
    accept/reject, a confidence score, and undo. Providers (Audible has no public
    API; OpenLibrary/Google Books are book-oriented, not audiobook-oriented) will
    disagree on field names (narrator vs reader). Define a canonical provider result
    type before writing the first provider.

12. **M4B combining is out of scope for this codebase's muxing.** Building an
    audio muxer (chapters, cover, metadata, re-encoding) is a trap. Strongly
    recommend shelling out to `ffmpeg`/`m4b-tool` and treating this tool as the
    tagger that runs *after* combining. Dependency on an external binary is
    acceptable and vastly safer.

13. **Security model assumes a trusted local user.** The token is the only auth;
    binding to `0.0.0.0` exposes it. The Host-header check only runs in loopback
    mode. Anyone adding remote access should put it behind a real reverse proxy
    with TLS and auth, not rely on the token.

14. **No atomic writes.** Mutagen writes in place for some formats; a crash mid-save
    can corrupt a file. For a tagging tool this is low probability but real. Consider
    writing to a temp file and replacing (where the format library permits) and
    keeping the undo log's old values as a logical backup.

## Architectural recommendations (foundations)

- Keep the single-file entry point (`python abtagger.py`) but split implementation
  into modules (`tags.py`, `files.py`, `state.py`, `server.py`) once the second
  feature lands. Doing it now, before the APIs stabilise, risks churn; doing it
  after two features have accreted is too late. The `FieldSpec` registry is the
  first step.
- Introduce a `Track`/`Book` domain model above the current row-dicts, and a
  `Library` aggregate, so future features (grouping, rename templates, combining)
  operate on domain objects rather than ad-hoc dicts.
- Add a command/operation log: every mutating action becomes a command with a
  preview, an apply, and an undo. This unifies tag edits, renames, moves, and
  metadata fetches under one undo/redo and one "what will change" preview.
- Keep the UI zero-build (vanilla JS + stdlib server). The main cost is duplicated
  validation; mitigate by generating the JS validation from the same schema later.
- Treat ABS, metadata providers, and muxers as adapters behind interfaces; the
  core must not import them.

## Alternatives considered / argued against

- **"Just write tags via ABS's sidecars."** Rejected: sidecars are ABS-private and
  the whole point is portable, standalone files. Keep files authoritative.
- **"Build our own M4B muxer."** Argued against above: use ffmpeg/m4b-tool.
- **"Migrate UI to React/Vue."** Argued against for now: adds a build toolchain to
  a tool whose main value is "download one file, run it". Revisit only when the UI
  genuinely outgrows vanilla JS.
- **"Store undo as full file copies."** Partially: do it for destructive ops only;
  value-based undo is fine and far cheaper for routine tag edits.
- **"Group rows by book with no way back to files."** Rejected: grouping is a
  heuristic, so the book row stays expandable and every file remains individually
  editable. The file-level view is still one toggle away.
