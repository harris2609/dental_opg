# Tooth Findings Overhaul + Printed Annotations — Design

## Purpose

Three related changes to the reporting workflow:

1. Replace the invented tooth-finding master list (missing/caries/root stump/...)
   with the clinic's actual 21 named findings and their canned descriptions
   (`opgcommonfindings.docx`), each editable per use, assembled into the report
   as `irt {tooth_number} - {description}` with the finding's name also summarized
   under Radiologic Impression.
2. Make the generated report text editable (currently read-only).
3. Bake image annotations (point/arrow/freehand/text) into the actual image shown
   in the PDF print format and the docx export, not just the live Vue viewer.

## Scope

In scope: `OPG Tooth Finding` master data + schema, `OPG Tooth Finding Entry`
schema, the tooth-chart UI's per-tooth interaction, `report_builder.py`'s
tooth-finding assembly and Radiologic Impression summarization, the editable
report-text textarea, and a shared annotation-baking utility used by both the
print format and the docx export.

Out of scope: the 5 non-arch sections' standard findings (unchanged), the live
Vue annotation editor itself (unchanged - only what gets *exported/printed*
changes).

## 1. Master data: `OPG Tooth Finding`

### Source data (extracted from `opgcommonfindings.docx`)

21 findings. Multi-part findings (`Coronally-`/`Radicularly-`/`Periapically-`)
are joined into one text block (whitespace-normalized, one space between
parts) per the confirmed decision - single editable field, not three:

| # | `finding_name` | `description_template` |
|---|---|---|
| 1 | Dental Caries | Coronally- an ill-defined radiolucency involving enamel and dentin on the mesial aspect Radicularly-no changes appreciated Periapically- no changes appreciated |
| 2 | Dental Caries Involving Pulp | Coronally- an ill-defined radiolucency involving enamel dentin and approximating pulp on the mesial aspect Radicularly-no changes appreciated Periapically- no changes appreciated |
| 3 | Secondary Caries | Coronally-a well-defined radiopacity noted s/o restorative material beneath which ill defined radiolucency approximating pulp noted Radicularly-no changes appreciated Periapically- no changes appreciated. |
| 4 | Periapical Abscess | Coronally-an ill-defined radiolucency involving enamel dentin and approximating pulp on the mesioproximal aspect noted Radicularly- no changes appreciated Periapically - loss of lamina dura with ill defined hazy radiolucency noted |
| 5 | Chronic Apical Periodontitis | Coronally-an ill-defined radiolucency involving enamel dentin and approximating pulp on the mesioproximal aspect noted Radicularly- no changes appreciated Periapically – widening of pdl space noted |
| 6 | Grossly Decayed | Coronally- an ill-defined radiolucency involving enamel dentin and approximating pulp with partial loss of crown structure Radicularly-no changes appreciated Periapically- no changes appreciated |
| 7 | Root Stumps | Coronally- complete loss of crown structure Radicularly-no changes appreciated Periapically- no changes appreciated |
| 8 | Root Caries | Coronally- an ill-defined radiolucency involving enamel dentin and approximating pulp on the mesial aspect Radicularly- ill defined radiolucency noted on the cervical third approximating canals Periapically- no changes appreciated |
| 9 | Incompletely Endodontically Treated Tooth | Coronally- a well-defined radiopacity noted along with partial loss of crown structure; Radicularly - homogenous thin linear radiopacity noted involving the root canal s/o endodontic restorative material periapically - no changes appreciated. |
| 10 | Restoration | Coronally- a well-defined radiopacity involving enamel noted;s/o restorative material Radicularly-no changes appreciated Periapically- no changes appreciated |
| 11 | Prosthetic Crown | Coronally- a well-defined radiopacity noted;s/o prosthetic crown Radicularly-no changes appreciated Periapically- no changes appreciated |
| 12 | Incompletely Endodontically Treated Tooth With Rarefying Osteitis | Coronally- a well-defined radiopacity noted along with partial loss of crown structure; Radicularly - homogenous thin linear radiopacity which is 3-4mm short of apex involving the root canal s/o endodontic restorative material periapically - ill defined hazy radiolucency with loss of lamina dura noted |
| 13 | Mesioangular Impaction | A dense radiopaque structure with density and morphology similar to that of a tooth with it's long axis is mesially inclined to that of adjacent tooth,The mesial portion crown is at the level of cervical third of adjacent tooth.The root formation is incomplete.The apical third of roots are in close approximation to inferior alveolar nerve canal suggestive of mesioangular impaction. |
| 14 | Distoangular Impaction | A dense radiopaque structure with density and morphology similar to that of a tooth noted ,the crown at the level of cervical third with it's long axis distally oriented to that of adjacent tooth, root formation is incomplete ,suggestive of distoangular impaction. |
| 15 | Horizontal Impaction | A dense radiopaque structure with density and morphology similar to that of tooth a with it's long axis is perpendicular to that of adjacent tooth,The tooth is embedded inside the bone except the distal cusp which is at the level of occlusal third of adjacent tooth.The root formation is incomplete.The follicular space is increased .The tooth in close approximation to inferior alveolar nerve canal suggestive of horizontal impaction. |
| 16 | Vertical Impaction | A dense radiopaque structure with density and morphology similar to that of a tooth with it's long axis parallel to that of adjacent tooth noted.The crown is embedded inside the bone and is at the level of cervical third of adjacent tooth.The root formation is complete .The follicular space is increased .The apical third of roots are in close approximation to inferior alveolar nerve canal suggestive of vertical impaction. |
| 17 | Partially Edentulous | Partial complement set of permanent dentition noted, with missing wrt |
| 18 | Periodontitis | The crest of the alveolar ridge is at the level of middle third of the roots of all the teeth except wrt 41 31 which is at the apical third of the root |
| 19 | Generalised Attrition | Irt all teeth - coronally - flattening of inscisal edge and cusps involving enamel and dentin noted s/o attrition |
| 20 | Idiopathic Osteosclerosis | Ill defined hazy radiopacity noted between the apical region of 11 and 12 region s/o idiopathic osteosclerosis. |
| 21 | Soft Tissue Calcification | Wrt laryngeal cartilage region below the level of hyoid bone a discrete radiopacity and a linear radiopacity noted s/o soft tissue calcification. |

Confirmed with the user: all 21 apply uniformly to any tooth click, even
ones whose canned text already references specific/multiple teeth or non-tooth
structures - the description is editable per entry precisely so the dentist
can correct wording per case (e.g. change "except wrt 41 31" to the real teeth).

### Schema change

`OPG Tooth Finding` (master): rename `finding_template` → `description_template`
(Small Text). Its old meaning ("Tooth {tooth_number}: X", a fully-templated
report sentence) no longer applies - report assembly now builds the "irt
{tooth}" prefix itself (see §3), so this field is just the plain canned
description text. Fixture data fully replaced with the 21 findings above.

## 2. `OPG Tooth Finding Entry` (child table)

Drops the `is_custom`/`custom_text` dual-mode in favor of a single unified
shape - every entry, whether picked from the master list or fully custom, has:

- `tooth_number` (Data, unchanged)
- `arch` (Select, unchanged - auto-derived from tooth number as today)
- `finding` (Link → OPG Tooth Finding, optional - populated only when chosen
  from the dropdown; blank for a fully custom entry)
- `finding_name` (Data, always populated - copied from the master's
  `finding_name` when chosen from the dropdown, or freely typed for a custom
  entry). This is what gets summarized under Radiologic Impression.
- `description` (Small Text, always populated, always editable - pre-filled
  from the master's `description_template` when a finding is picked, then
  freely editable; freely typed from scratch for a custom entry)

## 3. Report assembly (`report_builder.py`)

Tooth-finding lines change from `"Tooth {tooth_number}: {finding}"` to
`"irt {tooth_number} - {description}"`, reading `entry.description` directly -
no more re-fetching `OPG Tooth Finding`'s template at report-build time, since
the description is already resolved and stored on the entry when it's added.
This simplifies `_tooth_finding_lines` (drops its `frappe.get_all` lookup
entirely).

**Multi-tooth merging** (added per follow-up): entries within the same arch
section are grouped by exact `(finding_name, description)` match before
rendering - one combined line per group, tooth numbers joined in first-seen
(entry list) order: `"irt 16, 17 - {description}"` rather than one line each.
No new field needed for this - it's a render-time grouping over the existing
one-row-per-tooth entries, so if a dentist later edits one tooth's description
independently, that entry naturally falls out of the group (text no longer
matches) and prints as its own line - no explicit "linked group" concept to
maintain in the data model.

After building the normal 7 sections, append to Radiologic Impression: one
line per **distinct** `finding_name` used across all of `report.tooth_findings`
(confirmed: deduplicated, not once per tooth - unaffected by the merging
above, which only affects how the arch-section lines are grouped, not the
Radiologic Impression summary), in first-seen order. Not cross-checked against
whatever the dentist typed into Radiologic Impression directly - a rare
duplicate line is a non-issue now that the generated text is editable (§5), so
the dentist can just trim it rather than the code needing to detect it.

## 4. Tooth-chart UI (`ToothChart.vue`)

Replaces the current checkbox multi-toggle with an "add finding" flow matching
`SectionCard.vue`'s existing pattern: a dropdown of the 21 master findings
(plus a custom-text option) to add a new entry row for the clicked tooth; each
row shows an editable description textarea (pre-filled from the master
template, or blank for custom) and a remove button. Multiple entries per tooth
allowed, including repeats of the same finding.

**Multi-tooth selection** (added per follow-up): a "select multiple teeth"
mode toggle. Off (default): clicking a tooth behaves as today - opens that
one tooth's panel directly. On: clicking teeth toggles them into a
highlighted "selected" set (no panel opens per click); once one or more teeth
are selected, one shared add-finding panel appears below the chart (same
dropdown + editable description as the single-tooth panel). Clicking "Add"
creates one entry per selected tooth, all sharing the identical finding_name
and description text at creation time - which is exactly what makes them
group into one combined report line per §3. Turning multi-select off (or
selecting a new set) clears the current selection; it's a transient UI mode,
not stored state.

## 5. Editable report text

`ReportEditor.vue`'s generated-report-text block changes from a read-only
`<pre>` to a `<textarea v-model="report.generated_report_text">`, persisted
through the existing `saveReportDetails` call (add `generated_report_text` to
its field set). Clicking "Generate Report" still recomputes from structured
findings and overwrites whatever is there - unchanged, expected behavior.

## 6. Annotations baked into print + docx

New module `dental_opg/dental_opg_reporting/image_utils.py`:
`get_annotated_image_bytes(report) -> bytes | None` - loads the report's
`opg_image` via Frappe's file utilities, and if `report.annotations` has any
rows, draws each onto a copy using Pillow (new dependency, added to
`pyproject.toml`): a filled circle for Point, a line with arrowhead for Arrow,
a polyline for Freehand (parsing `path_data`'s JSON point array), and text for
Text - all at pixel coordinates computed by multiplying each annotation's
stored normalized (0-1) coordinates by the actual image's pixel dimensions.
Returns the original bytes unchanged if there are no annotations, and `None`
if there's no image at all.

Chosen over an SVG-overlay-in-print-HTML approach (mirroring the live Vue
viewer's technique) because wkhtmltopdf's static HTML rendering has no
reliable way to know the image's actual rendered pixel box at PDF-generation
time to align an overlay against - baking pixels server-side sidesteps that
entirely and produces one flattened image both output paths can just embed.

**Print format**: new whitelisted GET endpoint (e.g.
`dental_opg.dental_opg_reporting.doctype.opg_report.opg_report.get_annotated_report_image`)
returning the bytes as an image response (`frappe.response.type = "binary"`,
correct `content_type`); the print format's `<img src="{{ doc.opg_image }}">`
becomes `<img src="/api/method/...get_annotated_report_image?name={{ doc.name }}">`.

**Docx export**: `docx_export.py`'s `_insert_image` calls
`get_annotated_image_bytes(report)` instead of reading `report.opg_image`'s raw
file bytes directly - same function, same output, both formats stay
consistent (confirmed with the user).

## Error handling

- No `opg_image`: `get_annotated_image_bytes` returns `None`; both callers
  already have (or gain) a "skip if no image" branch, matching current
  behavior for reports without an uploaded X-ray.
- No annotations: returns the original image bytes unchanged - no Pillow
  drawing work happens, cheapest path stays cheap.
- Malformed `path_data` JSON on a Freehand annotation: let it raise - this
  would only happen from corrupted data, not user input through the normal
  UI flow, consistent with how this app treats other internal-data-integrity
  assumptions elsewhere.

## Testing

- Backend: a test for `report_builder.build_report_sections` asserting the
  `"irt {tooth} - {description}"` format and that Radiologic Impression gets
  the deduplicated finding-name lines appended.
- Backend: a test for `get_annotated_image_bytes` asserting the returned
  bytes differ from the original when annotations exist, and are identical
  when there are none.
- Manual verification: same as the docx export work - render the actual PDF
  and open the actual docx to visually confirm annotations appear, using the
  same LibreOffice-based process already used earlier.
