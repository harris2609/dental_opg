# Incidental Findings — Design

## Purpose

While reporting on a panoramic radiograph, a dentist may notice findings unrelated
to the report's main sections (e.g. a cyst, retained root, foreign body) that are
still clinically important to record and follow up on. These need to be logged
per-report, but also need to be browsable/auditable across the whole clinic
(e.g. "show me every severe incidental finding from the last month, across all
patients") — which a child table on `OPG Report` cannot give us for free.

## Scope

In scope: a new standalone DocType with its own Desk list view, a doc method to
create entries scoped to the currently open report, and a Vue section to
add/view/remove entries while reporting.

Out of scope (separate spec): docx export of the print format.

## Data model

New DocType `OPG Incidental Finding` (standalone, `istable: 0`, own list view):

| Field | Type | Notes |
|---|---|---|
| `report` | Link → OPG Report | Set server-side from the calling report, not client input |
| `patient` | Link → OPG Patient | Auto-filled server-side from `report.patient` |
| `reported_by` | Data | Auto-filled server-side from `report.reported_by` |
| `finding_type` | Data | Free text, dentist types whatever they observed |
| `side` | Select | Left / Right / Bilateral |
| `severity` | Select | Mild / Moderate / Severe |
| `finding_date` | Date | Defaults to today |

`patient` and `reported_by` are stamped by the server from the parent report,
never trusted from client input — a dentist filling this in should not be able
to attribute a finding to the wrong patient or a different reporting doctor by
tampering with the request.

Permissions: same as other DocTypes in this app — System Manager read/write/create/delete.
The standard Desk list view (filter/sort by patient, severity, doctor, date) comes for
free once this is a real DocType — no custom list UI needed.

## Backend

One new doc-level whitelisted method on `OPGReport` (list/delete reuse generic
`frappe.client.*` endpoints, no new backend code needed for those):

- `add_incidental_finding(finding_type, side, severity)` — creates and inserts a new
  `OPG Incidental Finding` doc, stamping `report`, `patient`, `reported_by` from `self`.
  Returns the new document's name.
- Removal uses the existing generic `frappe.client.delete` classic endpoint (already
  the pattern used for other client-side calls in `api.js`) — no new backend code needed
  for delete, since it's a real standalone doc with normal permissions.

A new whitelisted list method is needed to fetch a report's existing incidental
findings on load: reuse `frappe.client.get_list` (already used elsewhere in `api.js`)
filtered by `report = <report name>`.

## Frontend

New `IncidentalFindingsCard.vue` component, rendered after the 7 existing section
cards in `ReportEditor.vue`:

- On report load, fetch existing incidental findings for this report (`frappe.client.get_list`
  filtered by `report`).
- Shows each existing entry as a row (finding type, side, severity, date) with a remove button.
- A small add form: finding type text input, side dropdown, severity dropdown, "Add" button.
  Clicking "Add" calls `add_incidental_finding` immediately (its own doc insert, not
  batched with the rest of the report's "Save Findings" click, since this is a separate
  top-level doctype, not a child table).
- Remove button calls `frappe.client.delete` and removes the row from local state on success.

## Error handling

- `add_incidental_finding` relies on normal Frappe validation (required fields via DocType
  `reqd: 1` on `finding_type`, `side`, `severity`) — a missing value throws a standard
  `frappe.ValidationError`, surfaced to the user via the existing error handling already
  in `frappeRequest` (console-logged `data.exc` + thrown error with `.messages`).
- No optimistic UI updates — the row is only added to local state after the server
  confirms the insert succeeded, matching how image upload and other saves already behave.

## Testing

- Backend: a test creating an `OPG Report`, calling `add_incidental_finding`, and asserting
  the created `OPG Incidental Finding` doc has the correct `patient`/`reported_by` stamped
  from the parent report (not from whatever was passed in, if anything was).
- Manual verification: add via Vue screen, confirm it appears in the Desk list view
  filtered by patient/severity; remove via Vue screen, confirm it's gone from Desk too.
