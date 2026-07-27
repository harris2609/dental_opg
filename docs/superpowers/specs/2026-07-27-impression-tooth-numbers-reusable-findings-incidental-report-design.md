# Impression Tooth Numbers + Reusable Custom Findings + Incidental Findings Report — Design Spec

## Problem

Three related gaps in the reporting workflow:

1. The Radiologic Impression section lists each distinct tooth-finding name
   once (e.g. `"Dental Caries"`), with no tooth numbers — a dentist reading
   the impression can't tell which teeth it refers to without cross-checking
   the arch sections above it.
2. The "add custom finding" boxes (both the 7 section cards and the arch
   tooth chart) only ever produce free text scoped to that one report. A
   dentist who types the same custom finding again on a later patient has to
   retype it from scratch — it never becomes a reusable "+" chip like the
   master findings do.
3. `OPG Incidental Finding` records (logged via `IncidentalFindingsCard`) are
   only visible one report at a time, or via Frappe Desk's list view (System
   Manager access to `/app` required) — there's no clinic-wide view or
   export reachable from inside the app itself.

## Goal

- Radiologic Impression lines read `"{finding_name} irt {tooth numbers}"`.
- Any custom finding typed into either "add custom" box becomes a reusable
  master record (`OPG Standard Finding` / `OPG Tooth Finding`) the moment
  `Save Findings` is clicked, deduplicated by exact text so repeat use
  doesn't pile up duplicates.
- A new page inside the app SPA lists all incidental findings clinic-wide,
  with a working "Export to Excel" button.

## Non-goals

- No change to how the arch sections themselves render (`"irt {teeth} -
  {description}"` stays exactly as-is) — only the Impression section's
  format changes.
- No filter/search UI on the new incidental findings page for v1 — full
  list, sorted by date descending.
- No new Python dependency for the Excel export — reuse
  `frappe.utils.xlsxutils.make_xlsx`, the same utility Frappe's own Desk
  list view uses internally.
- No change to permissions — the new page and its export endpoint follow
  the same access as `OPG Incidental Finding` already has (System Manager
  read), it's just reachable from a new URL instead of only `/app`.

## Part 1: Radiologic Impression tooth numbers

### Current behavior (`report_builder.py`)

`_distinct_tooth_finding_names(report)` returns each `finding_name` once,
first-seen order, ignoring tooth number and description entirely.

### New behavior

Replace it with `_impression_finding_lines(report)`, grouping by
`(finding_name, description)` — **across both arches combined**, since
Radiologic Impression is one unified section with no arch boundary (unlike
`_tooth_finding_lines`, which intentionally keeps `"Maxillary Arch"` and
`"Mandibular Arch"` as separate report sections). Same first-seen-order
merge mechanics already used elsewhere in this file:

```python
def _impression_finding_lines(report):
	groups = {}
	order = []
	for row in report.tooth_findings:
		if not (row.finding_name and row.description):
			continue
		key = (row.finding_name, row.description)
		if key not in groups:
			groups[key] = []
			order.append(key)
		groups[key].append(row.tooth_number)

	lines = []
	for key in order:
		finding_name, _ = key
		tooth_numbers = ", ".join(groups[key])
		lines.append(f"{finding_name} irt {tooth_numbers}")
	return lines
```

If the same `finding_name` was used on different teeth with genuinely
different (edited) descriptions, it produces two separate lines — e.g.
`"Dental Caries irt 16, 17"` and `"Dental Caries irt 26"` — mirroring how
the arch section itself already treats them as distinct entries. If the same
`(finding_name, description)` pair happens to occur on both arches (e.g.
identical description coincidentally used on a maxillary and a mandibular
tooth), it merges into one combined line, since Impression has no
arch-based split.

`build_report_sections` swaps its call from `_distinct_tooth_finding_names`
to `_impression_finding_lines` and appends the result unchanged (each
returned string is already a complete line, not a bare name needing further
formatting).

## Part 2: Custom findings become reusable

### Detection (signals already present in the data model — no new fields)

- Section finding row is custom: `row.is_custom` is truthy (existing
  `OPG Section Finding Entry` field, unchanged).
- Tooth finding row is custom: `row.finding` is falsy (`ToothChart.vue`'s
  `addCustom()` already sets `finding: null` for custom rows, vs. `addFinding()`
  setting `finding: mf.name` when picked from the master list).

### Where the promotion happens

Inside `OPGReport.save_findings()`, immediately before `self.save()`, after
`self.set(...)` has applied the incoming rows. Iterating the just-set rows
(not the raw method arguments) keeps this correct regardless of whether
`section_findings`/`tooth_findings` were passed to this call or left
unchanged from a prior save.

### Section custom → `OPG Standard Finding`

For each row where `is_custom` and `custom_text` (stripped) is non-empty:

- Dedup key: exact match on `section_name == row.section` AND
  `finding_label == custom_text.strip()`.
- If no match exists, create:
  ```python
  frappe.get_doc({
      "doctype": "OPG Standard Finding",
      "section_name": row.section,
      "finding_label": custom_text,
      "finding_template": custom_text,
      "allow_side": 0,
      "allow_tooth": 0,
      "allow_level": 0,
      "active": 1,
  }).insert(ignore_permissions=True)
  ```
  `finding_label` and `finding_template` are set to the identical typed
  text — it becomes a static finding with no `{side}`/`{tooth_number}`/
  `{level}` placeholder fill-in when reused, since the custom-text box never
  captured that structure to begin with.

### Tooth custom → `OPG Tooth Finding`

For each row where `finding` is falsy and both `finding_name` and
`description` (stripped) are non-empty:

- Dedup key: exact match on `finding_name == row.finding_name.strip()` AND
  `description_template == row.description.strip()`. (Not `finding_name`
  alone — a dentist who edits the description after adding a custom entry,
  then later saves, should not silently overwrite what an earlier promotion
  captured; a differently-edited variant becomes its own reusable option,
  consistent with Part 1's per-distinct-description treatment.)
- If no match exists, create:
  ```python
  frappe.get_doc({
      "doctype": "OPG Tooth Finding",
      "finding_name": row.finding_name,
      "description_template": row.description,
      "active": 1,
  }).insert(ignore_permissions=True)
  ```

### What does NOT change

The report's own saved `section_findings`/`tooth_findings` rows are left
exactly as the dentist entered them (`is_custom`/`custom_text` stay as-is;
tooth rows keep `finding: null`). Promotion is a side effect that only
affects what's available as a "+" chip on the *next* report — this report's
own text output is unaffected by whether a matching master record already
existed or was just created. The very next call to
`dental_opg.api.get_reporting_setup_data` (already the source for both chip
lists, no new endpoint) will include the newly created record.

## Part 3: Incidental Findings report page

### New page: `frontend/src/pages/IncidentalFindingsReport.vue`

Route `/dental_opg/incidental-findings`, reachable via a link in
`AppHeader.vue` (alongside the existing app-title link and Logout button).
Lists all `OPG Incidental Finding` records clinic-wide via
`frappe.client.get_list` (columns: report, patient, finding_type, side,
severity, finding_date, reported_by), sorted by `finding_date desc`. A
single "Export to Excel" button triggers a full-page navigation to a new
whitelisted GET endpoint (browser-native file download, same pattern as the
existing `export_report_docx`/`get_annotated_report_image` endpoints — no
JS blob-handling needed).

### New backend endpoint

`dental_opg.api.export_incidental_findings_xlsx` (module-level whitelisted
GET function, mirroring `export_report_docx`'s existing pattern in
`opg_report.py`): fetches all `OPG Incidental Finding` records (same
fields/order as the page), builds rows via
`frappe.utils.xlsxutils.make_xlsx(data, "Incidental Findings")`, and streams
the result as `frappe.local.response` with
`content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"`
and `type = "download"` (matching the established `type="download"` vs.
`type="binary"` lesson from the annotation-image endpoint earlier this
project — `binary` ignores `content_type` entirely).

## Testing

- `report_builder.py`: rewrite the existing
  `test_radiologic_impression_lists_distinct_tooth_finding_names` test (its
  current assertions describe the old bare-name-dedup behavior) to assert
  the new `"{finding_name} irt {teeth}"` format, including one case
  confirming two different descriptions under the same finding name produce
  two separate lines, and one confirming an identical `(finding_name,
  description)` pair used on both arches merges into a single line.
- `save_findings`: new integration tests confirming (a) a custom section
  finding creates exactly one new `OPG Standard Finding` record with the
  expected fields; (b) saving the identical custom text again does not
  create a second record; (c) the equivalent two cases for a custom tooth
  finding and `OPG Tooth Finding`.
- `export_incidental_findings_xlsx`: a test confirming the response is a
  valid, parseable `.xlsx` by reading the returned bytes back with
  `openpyxl` (already present in this bench's Python environment as a
  transitive dependency — confirmed importable, no new package needed) and
  asserting the expected row data appears in the resulting worksheet.
- No JS test runner exists in this project — `IncidentalFindingsReport.vue`
  and the `AppHeader.vue` link are verified by `yarn build` succeeding plus
  manual/curl verification of the real list + export round trip, matching
  every other frontend change in this project so far.
