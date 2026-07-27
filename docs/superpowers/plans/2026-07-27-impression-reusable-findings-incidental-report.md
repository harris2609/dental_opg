# Impression Tooth Numbers + Reusable Custom Findings + Incidental Findings Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Radiologic Impression lines carry tooth numbers; custom findings typed into either "add custom" box become reusable master records the moment Save Findings is clicked; a new in-app page lists all incidental findings clinic-wide with a working Excel export.

**Architecture:** Three independent backend changes (`report_builder.py`'s Impression formatting, `OPGReport.save_findings`'s promotion side-effect, a new `api.py` xlsx-export endpoint) plus one frontend task (a new SPA page + `AppHeader` link + `api.js` functions). No schema changes — all three master DocTypes (`OPG Standard Finding`, `OPG Tooth Finding`, `OPG Incidental Finding`) already have every field this plan needs.

**Tech Stack:** Frappe Framework (Python doc methods, `frappe.utils.xlsxutils.make_xlsx`), Vue 3 + vue-router + frappe-ui (existing frontend stack, no new dependencies).

## Global Constraints

- Radiologic Impression line format is exactly `"{finding_name} irt {tooth_numbers}"`, grouped by `(finding_name, description)` across **both arches combined** (Impression has no arch boundary, unlike the arch sections themselves) — first-seen order, tooth numbers joined with `", "`.
- Custom-row detection uses signals already in the data model, no new fields: a section-finding row is custom when `is_custom` is truthy; a tooth-finding row is custom when `finding` is falsy.
- Dedup key for promoted section findings: exact match on `(section_name, finding_label)`. Dedup key for promoted tooth findings: exact match on `(finding_name, description_template)`.
- Promotion is a side effect only, inside `OPGReport.save_findings()`, before `self.save()`. It must never mutate the row's own saved `is_custom`/`custom_text`/`finding` fields — the report's own text output is unaffected either way.
- New master records are created with `ignore_permissions=True` (system-side upsert triggered by a whitelisted doc method, not a direct user create) and `active: 1`.
- Promoted `OPG Standard Finding` records get `allow_side = allow_tooth = allow_level = 0` and `finding_label == finding_template` (both set to the exact typed text) — no placeholder structure to infer from free text.
- Excel export uses `frappe.utils.xlsxutils.make_xlsx(data, sheet_name)` — no new Python dependency. The first row of `data` is the header row.
- Any new whitelisted binary/file-download endpoint uses `frappe.local.response.type = "download"` (never `"binary"`, which ignores `content_type` entirely) — this exact lesson was already learned and fixed once in this app's history (the annotation-image endpoint).
- New page route: `/dental_opg/incidental-findings`, linked from `AppHeader.vue`.
- Frontend styling matches the existing plain Tailwind gray palette (`bg-gray-900` primary buttons, `rounded`, `text-sm`, `text-gray-600`/`text-gray-500` for secondary text) already used throughout this app.
- This project has no JS test runner — frontend correctness is verified by `yarn build` succeeding plus manual/curl verification, not a new test framework.
- Every task that changes frontend source MUST rebuild and commit `dental_opg/public/frontend/**` and `dental_opg/www/dental_opg.html` in the same commit as the source change — this exact class of bug (source committed, bundle not rebuilt) was a Critical finding in a prior feature's final review for this app.

---

### Task 1: Radiologic Impression tooth numbers (TDD)

**Files:**
- Modify: `apps/dental_opg/dental_opg/dental_opg_reporting/report_builder.py`
- Modify: `apps/dental_opg/dental_opg/tests/test_report_builder.py`

**Interfaces:**
- Consumes: `report.tooth_findings` rows (existing `tooth_number`/`arch`/`finding_name`/`description` fields, unchanged).
- Produces: `build_report_sections(report)` (existing signature, unchanged) - the Radiologic Impression section's lines are now `"{finding_name} irt {tooth_numbers}"` strings instead of bare finding names. `_distinct_tooth_finding_names` is removed; `_impression_finding_lines` replaces it.

- [ ] **Step 1: Rewrite the existing Radiologic Impression test**

Replace the existing `test_radiologic_impression_lists_distinct_tooth_finding_names` test in `apps/dental_opg/dental_opg/tests/test_report_builder.py` with:

```python
	def test_radiologic_impression_includes_tooth_numbers_and_splits_by_description(self):
		self.report.save_findings(
			section_findings=[],
			tooth_findings=[
				{"tooth_number": "16", "arch": "Maxillary", "finding_name": "Dental Caries", "description": "desc A"},
				{"tooth_number": "17", "arch": "Maxillary", "finding_name": "Dental Caries", "description": "desc A"},
				{"tooth_number": "26", "arch": "Maxillary", "finding_name": "Dental Caries", "description": "desc B edited"},
				{"tooth_number": "46", "arch": "Mandibular", "finding_name": "Root Stumps", "description": "desc C"},
			],
		)
		self.report.reload()

		sections = build_report_sections(self.report)
		impression = next(s for s in sections if s["name"] == "RADIOLOGIC IMPRESSION")

		self.assertIn("Dental Caries irt 16, 17", impression["lines"])
		self.assertIn("Dental Caries irt 26", impression["lines"])
		self.assertIn("Root Stumps irt 46", impression["lines"])

	def test_radiologic_impression_merges_identical_finding_and_description_across_arches(self):
		self.report.save_findings(
			section_findings=[],
			tooth_findings=[
				{"tooth_number": "16", "arch": "Maxillary", "finding_name": "Dental Caries", "description": "same text"},
				{"tooth_number": "46", "arch": "Mandibular", "finding_name": "Dental Caries", "description": "same text"},
			],
		)
		self.report.reload()

		sections = build_report_sections(self.report)
		impression = next(s for s in sections if s["name"] == "RADIOLOGIC IMPRESSION")

		self.assertEqual(impression["lines"].count("Dental Caries irt 16, 46"), 1)
```

Leave `test_tooth_findings_merge_identical_finding_across_teeth` untouched - it tests the arch-section lines, which this task does not change.

- [ ] **Step 2: Run tests to verify they fail**

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.tests.test_report_builder`

Expected: both new tests fail - the current code still produces bare finding names (`"Dental Caries"`, not `"Dental Caries irt 16, 17"`) with no tooth numbers and no cross-arch merge.

- [ ] **Step 3: Replace `_distinct_tooth_finding_names` with `_impression_finding_lines`**

In `apps/dental_opg/dental_opg/dental_opg_reporting/report_builder.py`, replace this function:

```python
def _distinct_tooth_finding_names(report):
	"""Deduplicated finding names across all tooth findings (both arches),
	first-seen order, for the Radiologic Impression summary."""
	seen = []
	for row in report.tooth_findings:
		if row.finding_name and row.finding_name not in seen:
			seen.append(row.finding_name)
	return seen
```

with:

```python
def _impression_finding_lines(report):
	"""One "{finding_name} irt {tooth_numbers}" line per distinct (finding_name,
	description) pair, tooth numbers merged in first-seen order - across BOTH
	arches combined, since Radiologic Impression is one unified section with
	no arch boundary (unlike _tooth_finding_lines, which keeps the two arch
	sections separate). Two teeth sharing an identical finding name but a
	genuinely different (edited) description produce two separate lines,
	mirroring how the arch section itself already treats them."""
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

Then update `build_report_sections` - change:

```python
	for finding_name in _distinct_tooth_finding_names(report):
		section_lines["Radiologic Impression"].append(finding_name)
```

to:

```python
	section_lines["Radiologic Impression"].extend(_impression_finding_lines(report))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.tests.test_report_builder`

Expected: `OK`, all tests passing (the 2 new tests plus the untouched arch-merge test).

- [ ] **Step 5: Commit**

```bash
cd /workspace/development/frappe-bench/apps/dental_opg
git add dental_opg/dental_opg_reporting/report_builder.py dental_opg/tests/test_report_builder.py
git commit -m "Add tooth numbers to Radiologic Impression lines, merged by finding+description across arches"
```

---

### Task 2: Custom findings become reusable master records on Save Findings (TDD)

**Files:**
- Modify: `apps/dental_opg/dental_opg/dental_opg_reporting/doctype/opg_report/opg_report.py`
- Modify: `apps/dental_opg/dental_opg/dental_opg_reporting/doctype/opg_report/test_opg_report.py`

**Interfaces:**
- Consumes: `OPG Standard Finding` fields (`section_name`, `finding_label`, `finding_template`, `allow_side`, `allow_tooth`, `allow_level`, `active`) and `OPG Tooth Finding` fields (`finding_name`, `description_template`, `active`) - both existing, unchanged.
- Produces: `save_findings(self, section_findings=None, tooth_findings=None)` (existing signature, unchanged) now also creates missing master records as a side effect, before saving. No new return value.

- [ ] **Step 1: Write the failing tests**

Add to `apps/dental_opg/dental_opg/dental_opg_reporting/doctype/opg_report/test_opg_report.py` (same file, same `TestOPGReport` class - append after the existing two test methods):

```python
	def test_save_findings_promotes_new_custom_section_finding_to_reusable_master(self):
		self.report.save_findings(
			section_findings=[
				{"section": "Styloid Process", "is_custom": 1, "custom_text": "Unusual elongation noted bilaterally"},
			],
			tooth_findings=[],
		)

		matches = frappe.get_all(
			"OPG Standard Finding",
			filters={"section_name": "Styloid Process", "finding_label": "Unusual elongation noted bilaterally"},
			fields=["name", "finding_template", "allow_side", "allow_tooth", "allow_level", "active"],
		)
		self.assertEqual(len(matches), 1)
		match = matches[0]
		self.assertEqual(match.finding_template, "Unusual elongation noted bilaterally")
		self.assertEqual(match.allow_side, 0)
		self.assertEqual(match.allow_tooth, 0)
		self.assertEqual(match.allow_level, 0)
		self.assertEqual(match.active, 1)

	def test_save_findings_does_not_duplicate_existing_custom_section_finding(self):
		self.report.save_findings(
			section_findings=[
				{"section": "Styloid Process", "is_custom": 1, "custom_text": "Repeated custom text"},
			],
			tooth_findings=[],
		)

		other_patient = frappe.get_doc(
			doctype="OPG Patient",
			patient_name="Second Report Patient",
			registration_no=frappe.generate_hash(length=8),
		).insert()
		other_report = frappe.get_doc(doctype="OPG Report", patient=other_patient.name).insert()
		other_report.save_findings(
			section_findings=[
				{"section": "Styloid Process", "is_custom": 1, "custom_text": "Repeated custom text"},
			],
			tooth_findings=[],
		)

		matches = frappe.get_all(
			"OPG Standard Finding",
			filters={"section_name": "Styloid Process", "finding_label": "Repeated custom text"},
		)
		self.assertEqual(len(matches), 1)

	def test_save_findings_promotes_new_custom_tooth_finding_to_reusable_master(self):
		self.report.save_findings(
			section_findings=[],
			tooth_findings=[
				{
					"tooth_number": "38",
					"arch": "Mandibular",
					"finding": None,
					"finding_name": "Unusual radiopacity",
					"description": "A distinct radiopaque focus noted near the apex",
				},
			],
		)

		matches = frappe.get_all(
			"OPG Tooth Finding",
			filters={"finding_name": "Unusual radiopacity", "description_template": "A distinct radiopaque focus noted near the apex"},
			fields=["name", "active"],
		)
		self.assertEqual(len(matches), 1)
		self.assertEqual(matches[0].active, 1)

	def test_save_findings_does_not_promote_tooth_finding_picked_from_master_list(self):
		existing = frappe.get_doc(
			doctype="OPG Tooth Finding",
			finding_name="Already A Master Finding",
			description_template="Canned text",
		).insert()

		self.report.save_findings(
			section_findings=[],
			tooth_findings=[
				{
					"tooth_number": "11",
					"arch": "Maxillary",
					"finding": existing.name,
					"finding_name": existing.finding_name,
					"description": existing.description_template,
				},
			],
		)

		matches = frappe.get_all(
			"OPG Tooth Finding",
			filters={"finding_name": "Already A Master Finding"},
		)
		self.assertEqual(len(matches), 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.dental_opg_reporting.doctype.opg_report.test_opg_report`

Expected: the two "promotes" tests fail (no master record gets created - `save_findings` doesn't currently do this at all); the "does not duplicate"/"does not promote" tests currently pass vacuously (nothing is created either way) but will remain meaningful once Step 3 lands.

- [ ] **Step 3: Add promotion logic to `save_findings`**

In `apps/dental_opg/dental_opg/dental_opg_reporting/doctype/opg_report/opg_report.py`, the existing method reads:

```python
	@frappe.whitelist(methods=["POST"])
	def save_findings(self, section_findings: list | None = None, tooth_findings: list | None = None):
		if section_findings is not None:
			self.set("section_findings", section_findings)
		if tooth_findings is not None:
			self.set("tooth_findings", tooth_findings)
		self.save()
		return {"name": self.name}
```

Replace it with the version below, which adds one call to a new helper before `self.save()`, and defines that helper immediately after:

```python
	@frappe.whitelist(methods=["POST"])
	def save_findings(self, section_findings: list | None = None, tooth_findings: list | None = None):
		if section_findings is not None:
			self.set("section_findings", section_findings)
		if tooth_findings is not None:
			self.set("tooth_findings", tooth_findings)
		self._promote_custom_findings_to_master_lists()
		self.save()
		return {"name": self.name}

	def _promote_custom_findings_to_master_lists(self):
		"""Any custom finding a dentist typed into an 'add custom' box becomes a
		reusable master record the moment findings are saved - a side effect
		only, the row's own saved is_custom/custom_text/finding fields are
		never touched. Dedup by exact text match so repeat use doesn't create
		duplicate master entries."""
		for row in self.section_findings:
			if not row.is_custom:
				continue
			text = (row.custom_text or "").strip()
			if not text:
				continue
			exists = frappe.db.exists(
				"OPG Standard Finding", {"section_name": row.section, "finding_label": text}
			)
			if not exists:
				frappe.get_doc(
					{
						"doctype": "OPG Standard Finding",
						"section_name": row.section,
						"finding_label": text,
						"finding_template": text,
						"allow_side": 0,
						"allow_tooth": 0,
						"allow_level": 0,
						"active": 1,
					}
				).insert(ignore_permissions=True)

		for row in self.tooth_findings:
			if row.finding:
				continue
			finding_name = (row.finding_name or "").strip()
			description = (row.description or "").strip()
			if not (finding_name and description):
				continue
			exists = frappe.db.exists(
				"OPG Tooth Finding", {"finding_name": finding_name, "description_template": description}
			)
			if not exists:
				frappe.get_doc(
					{
						"doctype": "OPG Tooth Finding",
						"finding_name": finding_name,
						"description_template": description,
						"active": 1,
					}
				).insert(ignore_permissions=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.dental_opg_reporting.doctype.opg_report.test_opg_report`

Expected: `OK`, all tests passing (the 2 existing incidental-finding tests plus the 4 new promotion tests).

- [ ] **Step 5: Run the full test suite to confirm no regression**

Run: `bench --site dental_opg-test.localhost run-tests --app dental_opg`

Expected: `OK`, all tests passing (including Task 1's rewritten `test_report_builder.py`).

- [ ] **Step 6: Commit**

```bash
cd /workspace/development/frappe-bench/apps/dental_opg
git add dental_opg/dental_opg_reporting/doctype/opg_report/opg_report.py \
        dental_opg/dental_opg_reporting/doctype/opg_report/test_opg_report.py
git commit -m "Promote custom findings to reusable master records when findings are saved"
```

---

### Task 3: Incidental Findings Excel export endpoint (TDD)

**Files:**
- Modify: `apps/dental_opg/dental_opg/api.py`
- Create: `apps/dental_opg/dental_opg/tests/test_incidental_findings_export.py`

**Interfaces:**
- Consumes: `OPG Incidental Finding` fields (`report`, `patient`, `finding_type`, `side`, `severity`, `finding_date`, `reported_by` - all existing).
- Produces: `export_incidental_findings_xlsx()` (new module-level whitelisted GET function in `api.py`) - sets `frappe.local.response` to a downloadable `.xlsx` file. Consumed by Task 4's frontend page via a plain browser navigation (not an XHR call).

- [ ] **Step 1: Write the failing test**

Create `apps/dental_opg/dental_opg/tests/test_incidental_findings_export.py`:

```python
import io

import frappe
import openpyxl
from frappe.tests import IntegrationTestCase

from dental_opg.api import export_incidental_findings_xlsx


class TestIncidentalFindingsExport(IntegrationTestCase):
	def setUp(self):
		self.patient = frappe.get_doc(
			doctype="OPG Patient",
			patient_name="Export Test Patient",
			registration_no=frappe.generate_hash(length=8),
		).insert()
		self.report = frappe.get_doc(
			doctype="OPG Report",
			patient=self.patient.name,
			reported_by="Dr. Export Tester",
		).insert()
		self.report.add_incidental_finding(finding_type="Cyst", side="Left", severity="Moderate")

	def tearDown(self):
		frappe.local.response = frappe._dict()

	def test_export_produces_valid_xlsx_with_expected_row(self):
		export_incidental_findings_xlsx()

		content = frappe.local.response.filecontent
		self.assertEqual(frappe.local.response.content_type, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
		self.assertEqual(frappe.local.response.type, "download")

		workbook = openpyxl.load_workbook(io.BytesIO(content))
		sheet = workbook.active
		rows = list(sheet.iter_rows(values_only=True))

		header = rows[0]
		self.assertIn("Finding Type", header)
		self.assertIn("Patient", header)

		data_rows = rows[1:]
		matching = [r for r in data_rows if "Cyst" in r]
		self.assertEqual(len(matching), 1)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.tests.test_incidental_findings_export`

Expected: fails with `ImportError` / `AttributeError` - `export_incidental_findings_xlsx` doesn't exist yet.

- [ ] **Step 3: Add the endpoint to `api.py`**

Add to `apps/dental_opg/dental_opg/api.py` (after `create_report`, at module level):

```python
@frappe.whitelist(methods=["GET"])
def export_incidental_findings_xlsx():
	from frappe.utils.xlsxutils import make_xlsx

	fields = ["report", "patient", "finding_type", "side", "severity", "finding_date", "reported_by"]
	headers = ["Report", "Patient", "Finding Type", "Side", "Severity", "Finding Date", "Reported By"]

	records = frappe.get_all(
		"OPG Incidental Finding",
		fields=fields,
		order_by="finding_date desc, creation desc",
	)

	data = [headers] + [[record.get(f) for f in fields] for record in records]

	xlsx_file = make_xlsx(data, "Incidental Findings")

	frappe.local.response.filename = "incidental_findings.xlsx"
	frappe.local.response.filecontent = xlsx_file.getvalue()
	frappe.local.response.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
	frappe.local.response.type = "download"
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.tests.test_incidental_findings_export`

Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
cd /workspace/development/frappe-bench/apps/dental_opg
git add dental_opg/api.py dental_opg/tests/test_incidental_findings_export.py
git commit -m "Add Excel export endpoint for incidental findings"
```

---

### Task 4: Incidental Findings report page (frontend)

**Files:**
- Modify: `apps/dental_opg/frontend/src/api.js`
- Modify: `apps/dental_opg/frontend/src/router.js`
- Modify: `apps/dental_opg/frontend/src/components/AppHeader.vue`
- Create: `apps/dental_opg/frontend/src/pages/IncidentalFindingsReport.vue`

**Interfaces:**
- Consumes: `export_incidental_findings_xlsx` (Task 3, reached via plain navigation, not an API call), `frappe.client.get_list` (existing pattern already used by `listReports`/`getIncidentalFindings` in `api.js`).
- Produces: route `/dental_opg/incidental-findings`, linked from `AppHeader.vue`. Last frontend task in this plan - no later task depends on anything here.

- [ ] **Step 1: Add `listAllIncidentalFindings` to `api.js`**

Add to `apps/dental_opg/frontend/src/api.js` (near `getIncidentalFindings` - no changes to any existing exported function):

```javascript
export function listAllIncidentalFindings() {
	return frappeRequest({
		url: '/api/method/frappe.client.get_list',
		method: 'GET',
		params: {
			doctype: 'OPG Incidental Finding',
			fields: JSON.stringify(['name', 'report', 'patient', 'finding_type', 'side', 'severity', 'finding_date', 'reported_by']),
			order_by: 'finding_date desc, creation desc',
			limit_page_length: 0,
		},
	})
}
```

- [ ] **Step 2: Add the route to `router.js`**

Modify `apps/dental_opg/frontend/src/router.js` to:

```javascript
import { createRouter, createWebHistory } from 'vue-router'
import ReportList from './pages/ReportList.vue'
import NewReport from './pages/NewReport.vue'
import ReportEditor from './pages/ReportEditor.vue'
import Login from './pages/Login.vue'
import IncidentalFindingsReport from './pages/IncidentalFindingsReport.vue'

const routes = [
	{ path: '/dental_opg', name: 'ReportList', component: ReportList },
	{ path: '/dental_opg/new', name: 'NewReport', component: NewReport },
	{ path: '/dental_opg/login', name: 'Login', component: Login },
	{ path: '/dental_opg/incidental-findings', name: 'IncidentalFindingsReport', component: IncidentalFindingsReport },
	{ path: '/dental_opg/:reportId', name: 'ReportEditor', component: ReportEditor, props: true },
]

export default createRouter({
	history: createWebHistory('/'),
	routes,
})
```

The new route is declared before the catch-all `/dental_opg/:reportId`, same reasoning as the existing `Login` route.

- [ ] **Step 3: Create `IncidentalFindingsReport.vue`**

Create `apps/dental_opg/frontend/src/pages/IncidentalFindingsReport.vue`:

```vue
<template>
	<div class="mx-auto max-w-4xl p-6">
		<div class="mb-4 flex items-center justify-between">
			<h1 class="text-xl font-semibold">Incidental Findings</h1>
			<a
				href="/api/method/dental_opg.api.export_incidental_findings_xlsx"
				class="rounded bg-gray-900 px-3 py-1.5 text-sm text-white hover:bg-gray-700"
			>
				Export to Excel
			</a>
		</div>

		<div v-if="loading" class="text-sm text-gray-500">Loading...</div>
		<div v-else-if="!findings.length" class="text-sm text-gray-500">No incidental findings yet.</div>
		<table v-else class="w-full divide-y rounded border text-sm">
			<thead>
				<tr class="bg-gray-50 text-left text-xs text-gray-500">
					<th class="px-3 py-2">Report</th>
					<th class="px-3 py-2">Patient</th>
					<th class="px-3 py-2">Finding Type</th>
					<th class="px-3 py-2">Side</th>
					<th class="px-3 py-2">Severity</th>
					<th class="px-3 py-2">Date</th>
					<th class="px-3 py-2">Reported By</th>
				</tr>
			</thead>
			<tbody class="divide-y">
				<tr v-for="row in findings" :key="row.name">
					<td class="px-3 py-2">
						<router-link :to="`/dental_opg/${row.report}`" class="text-gray-900 hover:underline">{{ row.report }}</router-link>
					</td>
					<td class="px-3 py-2">{{ row.patient }}</td>
					<td class="px-3 py-2">{{ row.finding_type }}</td>
					<td class="px-3 py-2 text-gray-600">{{ row.side }}</td>
					<td class="px-3 py-2 text-gray-600">{{ row.severity }}</td>
					<td class="px-3 py-2 text-gray-500">{{ row.finding_date }}</td>
					<td class="px-3 py-2 text-gray-500">{{ row.reported_by }}</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listAllIncidentalFindings } from '../api'

const findings = ref([])
const loading = ref(true)

onMounted(async () => {
	findings.value = await listAllIncidentalFindings()
	loading.value = false
})
</script>
```

The Export button is a plain `<a href>` (full browser navigation to the whitelisted GET endpoint), not a JS `fetch` - the endpoint returns a real file download response (`type = "download"`), and Frappe's own CSRF exemption for GET requests means no token handling is needed, exactly like the app's existing `Export DOCX` button in `ReportEditor.vue`.

- [ ] **Step 4: Add a link to `AppHeader.vue`**

In `apps/dental_opg/frontend/src/components/AppHeader.vue`, add a link between the existing app-title link and the Logout button:

```vue
<template>
	<div class="flex items-center justify-between border-b bg-white px-6 py-3">
		<router-link to="/dental_opg" class="text-sm font-semibold text-gray-900">
			Yenepoya Dental College &middot; OPG Reporting
		</router-link>
		<div class="flex items-center gap-4">
			<router-link to="/dental_opg/incidental-findings" class="text-sm text-gray-600 hover:text-gray-900">
				Incidental Findings
			</router-link>
			<button
				@click="handleLogout"
				:disabled="loggingOut"
				class="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 disabled:opacity-50"
			>
				{{ loggingOut ? 'Logging out...' : 'Logout' }}
			</button>
		</div>
	</div>
</template>

<script setup>
import { ref } from 'vue'
import { logout } from '../api'

const loggingOut = ref(false)

async function handleLogout() {
	loggingOut.value = true
	try {
		await logout()
	} finally {
		window.location.href = '/dental_opg/login'
	}
}
</script>
```

(Only the template changed - the `<script setup>` block is unchanged from its current content, reproduced here in full so the file's final state is unambiguous.)

- [ ] **Step 5: Build and verify**

Run: `cd /workspace/development/frappe-bench/apps/dental_opg/frontend && yarn build`

Expected: `✓ built in <N>s`, no Vue compiler errors.

Run: `cd /workspace/development/frappe-bench && bench build --app dental_opg`

Expected: `✔ Application Assets Linked` and `DONE`.

- [ ] **Step 6: Full end-to-end curl verification on `dev.localhost`**

```bash
cd /tmp

# Reuse or reset the dev.localhost Administrator password if not already known
curl -s -c cookies_irf.txt -X POST "http://dev.localhost:8000/api/method/login" -d "usr=Administrator&pwd=<current dev.localhost admin password>" -o /dev/null -w "login: %{http_code}\n"

# List (should be a valid JSON array, possibly empty or containing prior real data - just confirm it doesn't error)
curl -s -b cookies_irf.txt "http://dev.localhost:8000/api/method/frappe.client.get_list?doctype=OPG%20Incidental%20Finding&fields=%5B%22name%22%2C%22finding_type%22%5D&limit_page_length=5" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert 'message' in d, 'expected message key'
print('list OK, count:', len(d['message']))
"

# Export - confirm it's a real xlsx (starts with the ZIP magic bytes PK)
curl -s -b cookies_irf.txt "http://dev.localhost:8000/api/method/dental_opg.api.export_incidental_findings_xlsx" -o /tmp/irf_export_check.xlsx
python3 -c "
with open('/tmp/irf_export_check.xlsx', 'rb') as f:
    magic = f.read(2)
assert magic == b'PK', f'not a valid xlsx, got magic bytes {magic!r}'
print('EXPORT VERIFIED OK')
"
rm -f /tmp/irf_export_check.xlsx cookies_irf.txt
```

Expected: `list OK, count: <N>` and `EXPORT VERIFIED OK` printed with no assertion errors. If the current `dev.localhost` Administrator password isn't known, reset it first with `bench --site dev.localhost set-admin-password <new-password>`, matching how prior features in this project handled the same situation.

- [ ] **Step 7: Confirm the built frontend contains the new UI**

```bash
grep -c "Incidental Findings" /workspace/development/frappe-bench/apps/dental_opg/dental_opg/public/frontend/assets/*.js
```

Expected: at least 1 match.

- [ ] **Step 8: Commit**

```bash
cd /workspace/development/frappe-bench && bench build --app dental_opg
cd /workspace/development/frappe-bench/apps/dental_opg
git add frontend/src/api.js frontend/src/router.js frontend/src/components/AppHeader.vue \
        frontend/src/pages/IncidentalFindingsReport.vue \
        dental_opg/public/frontend dental_opg/www/dental_opg.html
git commit -m "Add Incidental Findings report page with Excel export"
```

---

### Task 5: Final verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `bench --site dental_opg-test.localhost run-tests --app dental_opg`

Expected: `OK`, all tests passing (includes every new test from Tasks 1-3 alongside every pre-existing test).

- [ ] **Step 2: Migrate `dev.localhost`**

Run: `cd /workspace/development/frappe-bench && bench --site dev.localhost migrate`

Expected: no traceback (no schema changes in this plan, but running it keeps the site's fixture/asset state current, matching the pattern from every prior feature in this project).

- [ ] **Step 3: Manual browser verification checklist**

Report to the user: open an existing report at `http://dev.localhost:8000/dental_opg/<report-name>`, add a tooth finding via the "Add custom" box in an arch, and a custom finding via a section card's "Add custom" box, then click Save Findings. Reload the page (or open a different report) and confirm both custom entries now also appear as "+" chip options. Click Generate Report and confirm the Radiologic Impression lines now include tooth numbers in the `"{finding} irt {teeth}"` format. Click "Incidental Findings" in the header, confirm the list loads, and click "Export to Excel" to confirm a real `.xlsx` file downloads and opens correctly.

---
