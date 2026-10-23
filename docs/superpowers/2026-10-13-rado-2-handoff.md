# Rado-2 Feedback Round — Handoff (2026-10-13)

Status: **implementation complete, reviewed, fixes applied, deferred minors fixed (2026-10-23). Branch NOT merged.**
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

## Deferred minor issues — resolved (2026-10-23)
1. **Curve end kink** — the duplicate-point threshold is now 5 *screen* pixels (zoom- and image-size-aware) instead of an image-relative 0.002.
2. **Landmark without a label** — allowed; the crosshair is drawn alone. Text annotations still need a label.
3. **Multi-select `(tooth number)` fill** — removing one tooth's finding takes that tooth out of the sibling rows' text, as long as their text is still the untouched template fill (`dropToothNumber` in `findingText.js`). Hand-edited text is left alone.
4. **Print format escaping** — finding lines are rendered `{{ line | e | replace("\n", "<br>") }}`. (The originally suggested `(line | e).replace(...)` would escape the `<br>` too, since `Markup.replace` escapes its arguments.) Header/footer Data fields were left as-is: Frappe already sanitises them on save, so escaping again double-encodes `&`.
5. **Wrong stored jaw on old rows** — `patches/fix_tooth_finding_arch.py` backfills `arch` from the tooth number; `arch_for_tooth()` is shared with `OPGReport.validate`.
6. **`get_signatory_suggestions`** — one `GROUP BY TRIM(field)` query per field ordered by latest use, limited to 50; it now also checks read permission on OPG Report.

Tests: 57, OK (new: print-format escaping, arch backfill, whitespace-only signatory duplicates).

Still open: the footer layout — waiting on the clinic's model report.

Note: `bench serve` serves `/dental_opg` fine on a fresh v16 bench (redirects to `/dental_opg/login` when logged out), so the earlier "page not found" looks environment-specific.

## To resume
1. `git checkout rado-2-feedback`, then run the tests (command above).
2. Choose: merge to `main` locally, or push + PR, or keep.
3. Optionally tackle the deferred minors or the footer once the model report arrives.
