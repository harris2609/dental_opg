# Rado-2 Feedback Round — Design

## Purpose

Address the 18 change requests in the clinic's `Rado-2.xlsx` feedback sheet and
replace the tooth-finding master list with the revised `OPG COMMON FINDINGS (1).docx`.
Success = a dentist can report an OPG (adult or child) without retyping names,
fixing export formatting by hand, or deleting stray text after export.

All open questions were answered "use defaults"; typos in the Word doc are fixed.

## Scope

Five work areas, one spec, one plan (areas are independent and can ship task by task):

| Area | Sheet items |
|---|---|
| A. Findings data + report assembly | Findings (revised list), Interpretation of findings, Findings arrangement, finding search, exported "irt tooth number" mistake, Partially edentulous, Radiologic impression |
| B. Editor UI | Multiple tooth selecting, Tooth finding text box, Text entry limit, Teeth chart (children), Reported/Verified by memory, Name and age, Findings edit/individualize |
| C. Annotation tools | Polyline / Landmark / Curve |
| D. DOCX export | Unwanted spaces, blue text, footer alignment |
| E. Font | Times New Roman everywhere |

Out of scope: the letterhead header (logo, department title — kept as is),
incidental findings, login, report list.

---

## A. Findings data + report assembly

### A1. Replace tooth-finding master list

Source: `OPG COMMON FINDINGS (1).docx`. New `dental_opg/fixtures/opg_tooth_finding.json`
holds every finding in the doc (duplicates PARTIALLY EDENTULOUS and PERIODONTITIS
collapse to the later, "(tooth number)" version).

- `finding_name`: Title Case of the doc heading (e.g. "Dental Caries Involving Pulp").
- `description_template`: doc body lines joined with `\n` — Coronally / Radicularly /
  Periapically each on its own line, as in the doc.
- `name`: slug of `finding_name`. Findings that already exist keep their current slug
  so existing report rows keep linking.
- Typos fixed: Stapels→Staples, Decidouos→Deciduous, inscisal→incisal,
  adjascent→adjacent, "it's long axis"→"its long axis", "Ryle's" apostrophe
  normalized, stray double spaces collapsed.
- All 21 currently shipped findings appear in the new doc, so nothing is retired;
  fixture sync updates them in place by `name`. 20 findings are new (41 total).
- PARTIALLY EDENTULOUS body gets a trailing `(tooth number)` so A2 auto-fills it.

### A2. Placeholder auto-fill

Doc text contains `(tooth number)`. When a tooth finding is added, the UI replaces
`(tooth number)` in the description with the selected tooth/teeth (`41, 31`).
Other placeholders (`– to –`, `----`, `______`) stay literal for the dentist to edit.

### A3. Alphabetical order + search

- Section-finding chips and tooth-finding chips sorted A–Z, case-insensitive,
  client-side (`localeCompare`), regardless of server order.
- Each chip list gets a search input above it; filters chips by substring
  (case-insensitive) on label. Empty search = all chips.

### A4. "irt tooth number" export bug

Standard finding templates read `... irt tooth number {tooth_number}`. Change to
`... irt {tooth_number}` in fixtures, plus patch `fix_irt_tooth_number_templates`
updating existing `OPG Standard Finding` rows whose template contains
`irt tooth number {tooth_number}` (covers non-fixture copies).

### A5. Partially edentulous → Radiologic Impression

New field `impression_label` (Data) on `OPG Standard Finding`. When a report row's
master has `impression_label` and the row has `tooth_number`, the builder adds
`{impression_label} irt {tooth_numbers}` to Radiologic Impression. Rows sharing the same
label merge into one line, tooth numbers in first-seen order (maxillary + mandibular
combined: `PARTIALLY EDENTULOUS irt 16, 17, 36`).

Fixture: both "Partial complement set, missing tooth" findings get
`impression_label = "PARTIALLY EDENTULOUS"`.

### A6. New Radiologic Impression options

Added to standard-finding fixture (section Radiologic Impression):
- "Chronic generalized periodontitis" — template `Chronic generalized periodontitis`.
- "Localized periodontitis" — `allow_tooth = 1`, template `Localized periodontitis irt {tooth_number}`.

### A7. Manual interpretation saved permanently

Already implemented: custom findings are promoted to master lists on save
(`_promote_custom_findings_to_master_lists`). Changes:
- Tooth chart custom form gets two inputs: **name** (single line) and **description**
  (multi-line textarea). Today one text box fills both.
- Helper text under both custom forms: "Saved to the list for future reports."

### A8. Individualize a section finding (per patient)

New field `edited_text` (Small Text) on `OPG Report Finding`. Builder uses
`edited_text` when non-empty, else renders the template as today. The master is
never changed.

UI: each standard-finding row in `SectionCard` gets an "edit" button; it opens a
textarea prefilled with the client-side rendering of the template (side / tooth /
level substituted) so the dentist edits real text. "reset" clears `edited_text`.
`get_reporting_setup_data` returns `finding_template` so the client can render.

Tooth findings are already individualized via their per-row `description`.

---

## B. Editor UI

### B1. Multi-select shows and edits findings

In multi-select mode the panel lists, for every selected tooth, that tooth's rows
(heading "Tooth 16", rows beneath) with the same editable description textarea and
remove button as single mode. Adding a finding still adds one row per selected tooth.

### B2. Bigger text box

Tooth description textarea: `rows="5"`, `resize-y`, full width, `text-sm`.
Section edit textarea (A8): same.

### B3. 140-character limit

Cause: `OPG Tooth Finding Entry.finding_name` and `OPG Tooth Finding.finding_name`
are `Data` (varchar 140); custom text lands there. Change both to `Small Text`.
`description` / `description_template` / `custom_text` / `edited_text` are already
`Small Text` (no 140 limit). No textarea gets a `maxlength`.

### B4. Children tooth chart

Chart mode toggle per arch card: **Adult** (current FDI 11–48) / **Child**
(deciduous 51–55, 61–65 upper; 81–85, 71–75 lower) / **Mixed** (both rows).
Default Adult; auto-switches to Mixed on load when the report already has deciduous
rows. UI-only state, not saved.

`OPGReport.validate` arch derivation: first digit in `1 2 5 6` → Maxillary,
otherwise Mandibular (today only `1 2`).

### B5. Reported by / Verified by memory

New whitelisted `get_signatory_suggestions()` returns distinct non-empty
`reported_by` and `verified_by` values from `OPG Report`, most recent first,
max 50 each. Inputs use `<datalist>` so the dentist picks or types a new name.
A name is remembered once any report is saved with it.

### B6. Patient name and age in editor

Report Details shows Patient Name, Age / Sex, Registration No (read-only),
fetched from `OPG Patient` alongside the report. Also shown in the top bar next
to the report ID.

---

## C. Annotation tools

`OPG Annotation.annotation_type` gains `Polyline`, `Landmark`, `Curve`.

- **Polyline**: click to add vertices; double-click or Enter finishes; Esc cancels.
  Stored in `path_data` (same JSON point list as Freehand). Drawn as straight segments.
- **Landmark**: click a spot, type a label (free text) — stored in `x`, `y`,
  `label_text`. Drawn as a crosshair marker with label beside it.
- **Curve**: click control points, double-click/Enter finishes; drawn as a smooth
  Catmull-Rom spline through the points. Stored in `path_data`.

Rendering in both the Vue viewer (SVG) and `image_utils.py` (PIL, for print/DOCX).
Curve sampling is a shared pure function in `image_utils.py` (Python) and mirrored in
the viewer (JS).

---

## D. DOCX export

### D1. Unwanted spaces

The template has hardcoded empty paragraphs between sections (indices 8, 11, 14–17,
20, 23–26, 29–31). The template's source file is not in the repo (contains PHI), so
the exporter removes them at export time: every empty body paragraph after
"PANORAMIC RADIOGRAPH SHOWS" (except ones holding a drawing or section break) is
dropped, and each section heading gets `space_before = 6pt` instead.

### D2. Everything black, Times New Roman

After filling, the exporter walks every run in body paragraphs, body tables and
footer and sets `font.name = "Times New Roman"` (incl. `w:eastAsia`) and
`font.color.rgb = 000000`. Normal style is also set to Times New Roman black so
new paragraphs inherit it. Letterhead header part is left untouched.

### D3. Footer alignment

No model report file was supplied; default = footer table (restyled at export time) with two equal-width
columns spanning the page width, each cell text centered horizontally and vertically,
black bold Times New Roman, no colored fill; email line centered below. Same layout in
the print format footer.

### D4. Multi-line tooth descriptions

Description `\n` becomes separate lines inside the same bullet (DOCX line breaks
`w:br`, print format `<br>`), so Coronally / Radicularly / Periapically each start
on a new line.

---

## E. Font

- Vue app: Tailwind `fontFamily.sans` = `['"Times New Roman"', 'Times', 'serif']`.
- Print format: already Times New Roman — verify every element incl. footer.
- DOCX: D2.

---

## Data changes summary

| DocType | Change |
|---|---|
| OPG Tooth Finding | `finding_name` Data → Small Text |
| OPG Tooth Finding Entry | `finding_name` Data → Small Text |
| OPG Standard Finding | + `impression_label` (Data) |
| OPG Report Finding | + `edited_text` (Small Text) |
| OPG Annotation | `annotation_type` + Polyline, Landmark, Curve |

Patch: `fix_irt_tooth_number_templates`.

## Testing

- `report_builder`: edited_text override; impression_label merge across arches;
  multi-line descriptions; `irt` without "tooth number".
- `opg_report.validate`: arch for 51–85.
- `docx_export`: no empty paragraphs between sections; all runs black + Times New
  Roman; `w:br` in multi-line description; footer cells centered.
- `image_utils`: Polyline, Landmark, Curve draw without error; spline passes through
  control points.
- Patch: old `irt tooth number` templates fixed.
- API: `get_signatory_suggestions` distinct + ordered.
- Frontend: built and checked manually in the browser (multi-select edit, child chart,
  search, edit/reset, new annotation tools, patient header).
