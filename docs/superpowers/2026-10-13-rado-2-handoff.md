# Rado-2 Feedback Round — Handoff (2026-10-13)

Status: **implementation complete, reviewed, fixes applied. Branch NOT merged.**
Next step: decide what to do with the branch (merge to `main` / push + PR / keep).

## Where things are

| What | Where |
|---|---|
| Branch | `rado-2-feedback` (12 commits on top of `main` @ `cb90892`), last commit `206e45c` |
| Spec | `docs/superpowers/specs/2026-10-13-rado-2-feedback-design.md` |
| Plan | `docs/superpowers/plans/2026-10-13-rado-2-feedback.md` |
| Client inputs (untracked, never commit) | `Rado-2.xlsx`, `OPG COMMON FINDINGS (1).docx` in repo root |
| Tests | `cd /workspace/development/frappe-bench && bench --site dental_opg-test.localhost run-tests --app dental_opg` → 54 tests, OK |
| Frontend build | `cd frontend && yarn build` — built bundle (`dental_opg/public/frontend/**`, `dental_opg/www/dental_opg.html`) is committed; always rebuild + commit it after Vue changes |
| Sites | `dental_opg-test.localhost` (tests), `dev.localhost` (human-used) — both migrated, dev has 41 active tooth findings |

## What was delivered (all 18 sheet items)

**Findings data**
- Tooth findings replaced with the 41 findings from the Word doc (typos fixed; Coronally / Radicularly / Periapically on separate lines). The old 21 are kept and updated by slug, 20 are new.
- `irt tooth number 16` → `irt 16`; a patch also fixes copies already in the DB.
- "Partial complement… missing irt X" adds **PARTIALLY EDENTULOUS irt X** to Radiologic Impression, merged across both jaws.
- New impression options: Chronic generalized periodontitis; Localized periodontitis irt (teeth).
- Custom findings are still saved to the master list (helper text now says so); custom tooth findings get separate name and description boxes.

**Editor**
- Search box + A–Z order on every finding list.
- Per-patient "edit" / "reset to standard text" on section findings. Side/tooth/level are locked while the text is edited.
- Multi-select tooth chart shows and edits every selected tooth's findings; bigger text boxes.
- `(tooth number)` in a finding is filled in with the selected teeth.
- 140-character limit removed (tooth finding names, section custom findings).
- Children's chart: Adult / Child / Mixed toggle (FDI 51–85); deciduous teeth go to the correct jaw.
- Patient name / age / sex / reg no shown on the reporting page.
- Reported by / Verified by offer previously used names.
- Times New Roman across the app.

**Annotations:** Polyline, Landmark (crosshair + label), Curve (smooth). Shown in the viewer and baked into the print/DOCX image. An unfinished path is kept on Save, Generate or tool switch.

**Word export / print:** no blank gaps, all text black Times New Roman, multi-line findings, plain centred two-column footer. Letterhead header unchanged.

## Decisions made on the user's behalf
- Footer layout is a guess (two equal centred columns, black, no fill), because the "model report" file was never supplied. **Ask the clinic for it; adjust if different.**
- "Freehand curve tool" was read as click-points → smooth curve (plain freehand already existed).
- Non-tooth findings (tonsillolith, sialolith, Ryle's tube…) stay under the tooth chart.
- The jaw is always derived from the tooth number (the old "only if empty" check never fired because the Select field pre-fills "Maxillary").
- The `bench serve` dev server returned "page not found" for `/dental_opg` on every site, though the app works when run in-process. The browser check used `frappe.app.application` run via werkzeug `run_simple` on :8000 instead. Not investigated further.

## Deferred minor issues (from the final review — not fixed)
1. Double-click to finish a Curve can occasionally leave a tiny kink at the end (duplicate-point threshold is image-relative, ~1.8 screen px).
2. A Landmark can't be placed without a label.
3. Multi-select `(tooth number)` fill: if one tooth's finding is removed later, the other teeth's text still lists it.
4. The print format doesn't HTML-escape finding text (pre-existing). Safer: `{{ (line | e).replace("\n", "<br>") }}`.
5. Old API-created rows with a wrong stored jaw only correct on the next save (no backfill patch).
6. `get_signatory_suggestions` scans up to 500 rows per field instead of using DISTINCT (performance only).

## To resume
1. `git checkout rado-2-feedback`, then run the tests (command above).
2. Choose: merge to `main` locally, or push + PR, or keep.
3. Optionally tackle the deferred minors or the footer once the model report arrives.
