# DOCX Export — Design

## Purpose

The clinic's original report template is a `.docx` file with specific Word-native
formatting (a chevron-pattern letterhead banner, themed table borders/shading,
Bahnschrift/Times New Roman fonts) that the existing PDF print format already
replicates in HTML/CSS. Some users want the report as an actual editable `.docx`
file, not just PDF/print — e.g. to hand-edit a report after generation, or because
a downstream system expects Word format.

## Scope

In scope: exporting one `OPG Report` as a `.docx` file that visually matches the
clinic's original letterhead as closely as practical, triggered from the Vue
reporting screen.

Out of scope: annotation overlays baked into the exported image (matches the
existing PDF print format's scope — raw image only, confirmed with the user);
Desk-side export button (Vue screen only, confirmed with the user); exact
floating/anchored image positioning (inline image accepted as a deliberate
simplification, confirmed with the user).

## Why "docx-as-template", not build-from-scratch or pandoc conversion

The app already has the actual clinic `.docx` file (used earlier to build the PDF
print format pixel-for-pixel). Using it as a literal template — replacing its
patient/finding placeholders with tokens once, filling them in per report at
generation time — guarantees the exported file's static branding (logo, chevron
banner, department name, table border colors `#9CC2E5`/`#DEEAF6`, footer bars)
is byte-identical to the original, because it IS the original file, unlike:

- **Build from scratch with python-docx primitives**: re-implementing tables,
  borders, headers/footers via python-docx's API risks visual drift from the
  original (the same class of risk that caused three rounds of correction on
  the PDF print format, where XML-derived exact colors/fonts turned out
  different from initial guesses).
- **Pandoc HTML→docx conversion** of the existing print format HTML: table
  borders, cell shading, and precise fonts commonly don't survive this
  conversion path cleanly.

## Why template prep is simpler than generic docx templating

Generic docx-templating libraries (e.g. `docxtpl`) exist specifically to handle
the hard case: a placeholder like `{{ patient_name }}` typed into Word often gets
split across multiple XML `<w:r>` runs (because Word tracks spelling/grammar
markers, autocorrect, etc. mid-typing), so naive text search-and-replace on a
single run silently fails to find the full token.

This project sidesteps that problem entirely: the *fields needing tokens* were
inspected via raw XML during the PDF print format work (see the 2026-07-24
session), and are already known to be simple:

- `PATIENT NAME`, `AGE / SEX`, `REGISTRATION NO`, `DATE`, `REFERRED BY`,
  `CLINICAL DIAGNOSIS` are blank in the original (label + colon, no sample
  value) — inserting a token means appending clean text to an already-simple
  run, not replacing text split across several runs. `RADIOGRAPHIC
  PROJECTION` already has a literal `OPG` value in its own single run
  (confirmed via the same earlier XML inspection) — same single-run
  replacement, just swapping existing text instead of appending to blank.
- `Dr. CATHERINE(PG)` / `Dr. NAMRATHA` in the footer are each their own single
  run (confirmed via the earlier `word/footer1.xml` XML inspection).

Because the template is prepared once, by hand/script, with full control over
the result, each token is verified to live in exactly one run before being
committed — no generic run-splitting-safe replacement algorithm is needed at
runtime.

## Template preparation (one-time, not part of the runtime code path)

Produces a tracked template file from the original `printformat.docx`:

1. Insert tokens into the blank metadata slots: `{{patient_name}}`, `{{age}}`,
   `{{sex}}`, `{{registration_no}}`, `{{report_date}}`, `{{referred_by}}`,
   `{{radiographic_projection}}`, `{{clinical_diagnosis}}`.
2. Replace the footer's `Dr. CATHERINE(PG)` → `{{reported_by}}` and
   `Dr. NAMRATHA` → `{{verified_by}}`.
3. Delete the sample OPG X-ray image (the anchored picture near the "REPORT"
   heading), replace with a single marker paragraph `{{OPG_IMAGE}}`.
4. Under each of the 7 section headings, delete all example finding
   option-lines and the "In pro version..." floating note box (already agreed
   to skip). Replace with one marker paragraph per section:
   `{{FINDINGS:CONDYLAR_MORPHOLOGY}}`, `{{FINDINGS:STYLOID_PROCESS}}`,
   `{{FINDINGS:MAXILLARY_SINUS}}`, `{{FINDINGS:INFERIOR_BORDER_OF_MANDIBLE}}`,
   `{{FINDINGS:MAXILLARY_ARCH}}`, `{{FINDINGS:MANDIBULAR_ARCH}}`,
   `{{FINDINGS:RADIOLOGIC_IMPRESSION}}`. The two arch section markers use the
   original docx's bulleted-list paragraph style; the other five use its plain
   paragraph style — matching the same bullet/plain distinction the PDF print
   format already has (`build_report_sections` + the print format's
   `MAXILLARY ARCH`/`MANDIBULAR ARCH` special-case).
5. Section headings themselves (`CONDYLAR MORPHOLOGY:` etc.) stay in the
   template as normal paragraphs — deleted at runtime only if that section
   ends up with no findings for a given report (see below).

Deliverables: the template file itself (tracked binary,
`apps/dental_opg/dental_opg/dental_opg_reporting/templates/opg_report_template.docx`),
plus the prep script used to produce it, so the letterhead can be regenerated
if the clinic ever changes it. `python-docx` is added as a dependency
(`pyproject.toml`) and installed in the bench environment for both the prep
script and the runtime export function to use.

## Runtime export

New module-level function `export_report_docx(name)` in
`opg_report.py` — a "doctype-level function" (per this app's existing `api.md`
convention: module-root functions, not doc methods, for logic that doesn't
need `self`), whitelisted for `GET`, mirroring how Frappe's own
`download_pdf` works (sets `frappe.response.filecontent`/`filename`/`type`
directly, plain link, not a JSON-returning `run_doc_method` call):

1. Load the `OPG Report` doc and open a fresh copy of the template
   (`python_docx.Document(template_path)`).
2. Fill each metadata token via a single controlled text-replace per run
   (safe, per the reasoning above — each token is known to live in one run).
3. Call the existing `build_report_sections(report)` (already used by
   `generate_report`/the PDF print format — single source of truth for both
   output formats, no duplicated finding-assembly logic) to get the same
   structured `{name, lines}` list per non-empty section.
4. For each section: if it has lines, replace the marker paragraph's text
   with the first line, then insert sibling paragraphs (cloned from the
   marker's paragraph style — bullet or plain, matching step 4 of template
   prep) for the remaining lines. If a section has zero lines, delete both
   its heading paragraph and its marker paragraph.
5. Locate the `{{OPG_IMAGE}}` marker paragraph, clear its text, and insert the
   report's `opg_image` file inline at that position (read via Frappe's file
   utilities, not a raw filesystem path assumption).
6. Save to an in-memory buffer, return as a downloadable `.docx` (same
   response pattern as Frappe's own PDF download).

## Frontend

One more plain `<a>` link in `ReportEditor.vue`'s header button row, next to
the existing Print/Get PDF, pointing at
`/api/method/dental_opg.dental_opg_reporting.doctype.opg_report.opg_report.export_report_docx?name=<report>`
— same pattern as the existing links (browser-driven download, no JS fetch
needed).

## Error handling

- If `opg_image` is empty (no X-ray uploaded yet), skip the image insertion
  step and leave the marker paragraph's text cleared but empty — matches the
  PDF print format's `{% if doc.opg_image %}` conditional behavior.
- If the template file is missing or fails to open, the whitelisted function
  lets the resulting exception surface as a normal Frappe error response (no
  special handling needed — this would only happen from a broken deployment,
  not user input, so a generic 500 with the traceback in logs is adequate,
  consistent with how the rest of this app handles unexpected file/IO errors).
- No new validation needed on `OPG Report` itself — this is a read-only export
  of already-validated, already-saved data.

## Testing

- A test verifying the template file exists and can be opened with
  `python-docx` without raising (catches a corrupted/missing template file
  before it reaches production).
- A test calling `export_report_docx` for a report with a mix of populated and
  empty sections, asserting: populated sections' finding text appears
  somewhere in the resulting document's paragraph text, and at least one
  known-empty section's heading text does NOT appear (proves the
  delete-when-empty behavior, not just "the function ran without crashing").
- Manual verification: open the actual exported `.docx` in a real viewer
  (LibreOffice, already installed in this dev environment from the earlier
  PDF verification work) and visually compare against the PDF print format
  for the same report, the same way the PDF was verified against the
  original clinic docx.
