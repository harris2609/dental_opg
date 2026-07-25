# Incidental Findings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a dentist log incidental findings (finding type, side, severity) while reporting on an OPG Report, stored as a standalone DocType with its own Desk list view for clinic-wide auditing, with patient and reporting doctor stamped server-side from the parent report.

**Architecture:** New standalone `OPG Incidental Finding` DocType (not a child table). A new whitelisted doc method `OPGReport.add_incidental_finding` creates entries immediately (separate from the report's batched "Save Findings"). A new Vue component fetches/add/removes entries for the currently open report, using the existing `frappe.client.*` classic-endpoint pattern already used throughout `frontend/src/api.js`.

**Tech Stack:** Frappe Framework (Python/DocType), Vue 3 + frappe-ui (frontend), bench site `dev.localhost` for manual verification, new site `dental_opg-test.localhost` for automated tests.

## Global Constraints

- Doc-level whitelisted methods live in `opg_report.py`, not standalone `api.py` functions (per this app's existing convention — see `save_findings`/`generate_report`).
- Always declare `@frappe.whitelist(methods=[...])` explicitly on new whitelisted methods.
- `patient` and `reported_by` on `OPG Incidental Finding` must be stamped server-side from the parent `OPG Report` — never trust client-supplied values for these two fields.
- Frontend API calls go through `frappeRequest` from `frappe-ui`, which already unwraps the classic `/api/method` response's `message` key — do not add a second `.then(r => r.message)` on top (this exact bug was already hit and fixed once this session).
- Run `bench --site <site> migrate` after any DocType JSON change. Never run bare `bench migrate`.
- This project has no JS test runner — frontend changes are verified with manual curl reproduction of the browser's HTTP calls (the established pattern throughout this session), not a new test framework.

---

### Task 1: `OPG Incidental Finding` DocType + test site

**Files:**
- Create: `apps/dental_opg/dental_opg/dental_opg_reporting/doctype/opg_incidental_finding/opg_incidental_finding.json`
- Create: `apps/dental_opg/dental_opg/dental_opg_reporting/doctype/opg_incidental_finding/__init__.py`
- Create: `apps/dental_opg/dental_opg/dental_opg_reporting/doctype/opg_incidental_finding/opg_incidental_finding.py`

**Interfaces:**
- Produces: DocType `OPG Incidental Finding` with fields `report` (Link → OPG Report), `patient` (Link → OPG Patient, read-only), `reported_by` (Data, read-only), `finding_type` (Data, required), `side` (Select: Left/Right/Bilateral, required), `severity` (Select: Mild/Moderate/Severe, required), `finding_date` (Date, default Today).

- [ ] **Step 1: Create the test site**

Run: `cd /workspace/development/frappe-bench && bench new-site dental_opg-test.localhost --db-root-username root --mariadb-root-password 123 --admin-password admin --mariadb-user-host-login-scope='%'`

Expected: `*** Scheduler is disabled ***` at the end, no errors.

Run: `bench --site dental_opg-test.localhost install-app dental_opg`

Expected: `Installing dental_opg...` then completes with no traceback.

- [ ] **Step 2: Write the DocType JSON**

Create `apps/dental_opg/dental_opg/dental_opg_reporting/doctype/opg_incidental_finding/opg_incidental_finding.json`:

```json
{
    "name": "OPG Incidental Finding",
    "module": "Dental OPG Reporting",
    "doctype": "DocType",
    "engine": "InnoDB",
    "autoname": "hash",
    "naming_rule": "Random",
    "is_submittable": 0,
    "sort_field": "modified",
    "sort_order": "DESC",
    "fields": [
        {
            "fieldname": "report",
            "fieldtype": "Link",
            "label": "Report",
            "options": "OPG Report",
            "reqd": 1,
            "in_list_view": 1
        },
        {
            "fieldname": "patient",
            "fieldtype": "Link",
            "label": "Patient",
            "options": "OPG Patient",
            "read_only": 1,
            "in_list_view": 1
        },
        {
            "fieldname": "reported_by",
            "fieldtype": "Data",
            "label": "Reported By",
            "read_only": 1,
            "in_list_view": 1
        },
        {
            "fieldname": "finding_type",
            "fieldtype": "Data",
            "label": "Finding Type",
            "reqd": 1,
            "in_list_view": 1
        },
        {
            "fieldname": "side",
            "fieldtype": "Select",
            "label": "Side",
            "options": "Left\nRight\nBilateral",
            "reqd": 1
        },
        {
            "fieldname": "severity",
            "fieldtype": "Select",
            "label": "Severity",
            "options": "Mild\nModerate\nSevere",
            "reqd": 1,
            "in_list_view": 1
        },
        {
            "fieldname": "finding_date",
            "fieldtype": "Date",
            "label": "Finding Date",
            "default": "Today",
            "in_list_view": 1
        }
    ],
    "permissions": [
        {
            "role": "System Manager",
            "read": 1,
            "write": 1,
            "create": 1,
            "delete": 1
        }
    ]
}
```

- [ ] **Step 3: Create the empty `__init__.py`**

Create `apps/dental_opg/dental_opg/dental_opg_reporting/doctype/opg_incidental_finding/__init__.py` (empty file).

- [ ] **Step 4: Create the controller**

Create `apps/dental_opg/dental_opg/dental_opg_reporting/doctype/opg_incidental_finding/opg_incidental_finding.py`:

```python
import frappe
from frappe.model.document import Document


class OPGIncidentalFinding(Document):
	pass
```

- [ ] **Step 5: Migrate the test site and verify**

Run: `bench --site dental_opg-test.localhost migrate`

Expected: completes with no traceback. Look for `Executing after_migrate hooks` near the end and no `Traceback` anywhere in the output.

- [ ] **Step 6: Commit**

```bash
cd /workspace/development/frappe-bench/apps/dental_opg
git add dental_opg/dental_opg_reporting/doctype/opg_incidental_finding/
git commit -m "Add OPG Incidental Finding DocType"
```

---

### Task 2: `add_incidental_finding` doc method (TDD)

**Files:**
- Modify: `apps/dental_opg/dental_opg/dental_opg_reporting/doctype/opg_report/opg_report.py`
- Create: `apps/dental_opg/dental_opg/dental_opg_reporting/doctype/opg_report/test_opg_report.py`

**Interfaces:**
- Consumes: `OPG Incidental Finding` DocType from Task 1 (fields `report`, `patient`, `reported_by`, `finding_type`, `side`, `severity`).
- Produces: `OPGReport.add_incidental_finding(finding_type: str, side: str, severity: str) -> str` — creates and inserts an `OPG Incidental Finding` doc, returns its `name`.

- [ ] **Step 1: Write the failing test**

Create `apps/dental_opg/dental_opg/dental_opg_reporting/doctype/opg_report/test_opg_report.py`:

```python
import frappe
from frappe.tests import IntegrationTestCase


class TestOPGReport(IntegrationTestCase):
	def setUp(self):
		self.patient = frappe.get_doc(
			doctype="OPG Patient",
			patient_name="Test Incidental Patient",
			age=40,
			sex="Male",
			registration_no=frappe.generate_hash(length=8),
		).insert()
		self.report = frappe.get_doc(
			doctype="OPG Report",
			patient=self.patient.name,
			reported_by="Dr. Test Reporter",
		).insert()

	def test_add_incidental_finding_stamps_patient_and_reported_by_from_report(self):
		name = self.report.add_incidental_finding(
			finding_type="Cyst",
			side="Left",
			severity="Moderate",
		)

		finding = frappe.get_doc("OPG Incidental Finding", name)
		self.assertEqual(finding.report, self.report.name)
		self.assertEqual(finding.patient, self.patient.name)
		self.assertEqual(finding.reported_by, "Dr. Test Reporter")
		self.assertEqual(finding.finding_type, "Cyst")
		self.assertEqual(finding.side, "Left")
		self.assertEqual(finding.severity, "Moderate")

	def test_add_incidental_finding_ignores_client_supplied_patient(self):
		"""patient/reported_by must come from the report, never from caller input"""
		other_patient = frappe.get_doc(
			doctype="OPG Patient",
			patient_name="Other Patient",
			registration_no=frappe.generate_hash(length=8),
		).insert()

		name = self.report.add_incidental_finding(
			finding_type="Retained root",
			side="Right",
			severity="Mild",
		)

		finding = frappe.get_doc("OPG Incidental Finding", name)
		self.assertEqual(finding.patient, self.patient.name)
		self.assertNotEqual(finding.patient, other_patient.name)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.dental_opg_reporting.doctype.opg_report.test_opg_report`

Expected: `AttributeError: 'OPGReport' object has no attribute 'add_incidental_finding'` (or similar) — the method doesn't exist yet.

- [ ] **Step 3: Implement `add_incidental_finding`**

Modify `apps/dental_opg/dental_opg/dental_opg_reporting/doctype/opg_report/opg_report.py`. Current content:

```python
import frappe
from frappe.model.document import Document

from dental_opg.dental_opg_reporting.report_builder import build_report_text


class OPGReport(Document):
	def validate(self):
		for row in self.tooth_findings:
			if not row.arch:
				row.arch = "Maxillary" if row.tooth_number and row.tooth_number.strip()[:1] in "12" else "Mandibular"

	@frappe.whitelist(methods=["POST"])
	def save_findings(self, section_findings: list | None = None, tooth_findings: list | None = None):
		if section_findings is not None:
			self.set("section_findings", section_findings)
		if tooth_findings is not None:
			self.set("tooth_findings", tooth_findings)
		self.save()
		return {"name": self.name}

	@frappe.whitelist(methods=["POST"])
	def save_annotations(self, annotations: list):
		self.set("annotations", annotations)
		self.save()
		return {"name": self.name}

	@frappe.whitelist(methods=["POST"])
	def generate_report(self):
		self.generated_report_text = build_report_text(self)
		self.save()
		return self.generated_report_text
```

Add this method to the `OPGReport` class (after `generate_report`):

```python

	@frappe.whitelist(methods=["POST"])
	def add_incidental_finding(self, finding_type: str, side: str, severity: str) -> str:
		finding = frappe.get_doc(
			{
				"doctype": "OPG Incidental Finding",
				"report": self.name,
				"patient": self.patient,
				"reported_by": self.reported_by,
				"finding_type": finding_type,
				"side": side,
				"severity": severity,
			}
		)
		finding.insert()
		return finding.name
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.dental_opg_reporting.doctype.opg_report.test_opg_report`

Expected: `OK` with 2 tests run, 0 failures, 0 errors.

- [ ] **Step 5: Commit**

```bash
cd /workspace/development/frappe-bench/apps/dental_opg
git add dental_opg/dental_opg_reporting/doctype/opg_report/opg_report.py dental_opg/dental_opg_reporting/doctype/opg_report/test_opg_report.py
git commit -m "Add OPGReport.add_incidental_finding doc method with tests"
```

---

### Task 3: Frontend API functions

**Files:**
- Modify: `apps/dental_opg/frontend/src/api.js`

**Interfaces:**
- Consumes: `run_doc_method` classic endpoint pattern (already used by `saveFindings`/`saveAnnotations`/`generateReport` via the existing `callDocMethod` helper); `frappe.client.get_list` and `frappe.client.delete` classic endpoints (already used elsewhere in this file for `listReports`/`saveReportDetails`).
- Produces: `getIncidentalFindings(reportName)`, `addIncidentalFinding(reportName, {finding_type, side, severity})`, `deleteIncidentalFinding(name)` — all exported from `api.js`.

- [ ] **Step 1: Add the three functions**

Modify `apps/dental_opg/frontend/src/api.js`. Add after the existing `generateReport` function (before the `uploadImage` comment block):

```javascript

export function getIncidentalFindings(reportName) {
	return frappeRequest({
		url: '/api/method/frappe.client.get_list',
		method: 'GET',
		params: {
			doctype: 'OPG Incidental Finding',
			filters: JSON.stringify({ report: reportName }),
			fields: JSON.stringify(['name', 'finding_type', 'side', 'severity', 'finding_date']),
			order_by: 'creation asc',
			limit_page_length: 0,
		},
	})
}

export function addIncidentalFinding(reportName, { finding_type, side, severity }) {
	return callDocMethod(reportName, 'add_incidental_finding', { finding_type, side, severity })
}

export function deleteIncidentalFinding(name) {
	return frappeRequest({
		url: '/api/method/frappe.client.delete',
		method: 'POST',
		params: { doctype: 'OPG Incidental Finding', name },
	})
}
```

- [ ] **Step 2: Rebuild the frontend**

Run: `cd /workspace/development/frappe-bench/apps/dental_opg/frontend && yarn build`

Expected: `✓ built in <N>s` with no errors, new hashed filenames in the output (e.g. `index-XXXXXXXX.js`).

Run: `cd /workspace/development/frappe-bench && bench build --app dental_opg`

Expected: `✔ Application Assets Linked` and `DONE` with no errors.

- [ ] **Step 3: Verify `add_incidental_finding` end-to-end via curl**

This reproduces exactly what the browser will do — run against `dev.localhost` (not the test site, since we need a real logged-in session):

```bash
cd /tmp
curl -s -c cookies_incidental.txt -X POST "http://dev.localhost:8000/api/method/login" -d "usr=Administrator&pwd=admin" -o /dev/null -w "login: %{http_code}\n"
TOKEN=$(curl -s -b cookies_incidental.txt "http://dev.localhost:8000/dental_opg" | grep -oP 'window\["csrf_token"\] = "\K[^"]+')

CREATE=$(curl -s -b cookies_incidental.txt -X POST "http://dev.localhost:8000/api/method/dental_opg.api.create_report" \
  -H "Content-Type: application/json" -H "X-Frappe-CSRF-Token: $TOKEN" -H "Referer: http://dev.localhost:8000/dental_opg/new" \
  -d '{"patient_name":"Incidental Test","age":33,"sex":"Female","registration_no":"REG-INCIDENTAL-01"}')
REPORT=$(echo "$CREATE" | python3 -c "import json,sys; print(json.load(sys.stdin)['message']['report'])")
echo "report=$REPORT"

curl -s -b cookies_incidental.txt -X POST "http://dev.localhost:8000/api/method/run_doc_method" \
  -H "Content-Type: application/json" -H "X-Frappe-CSRF-Token: $TOKEN" -H "Referer: http://dev.localhost:8000/dental_opg/new" \
  -d "{\"dt\":\"OPG Report\",\"dn\":\"$REPORT\",\"method\":\"add_incidental_finding\",\"args\":{\"finding_type\":\"Cyst\",\"side\":\"Left\",\"severity\":\"Moderate\"}}"
```

Expected: a JSON response containing `"docs"` and `"message"` keys, where `message` is a hash-like string (the new `OPG Incidental Finding` name).

- [ ] **Step 4: Verify `getIncidentalFindings` end-to-end via curl**

```bash
curl -s -b cookies_incidental.txt "http://dev.localhost:8000/api/method/frappe.client.get_list?doctype=OPG%20Incidental%20Finding&filters=%7B%22report%22%3A%22$REPORT%22%7D&fields=%5B%22name%22%2C%22finding_type%22%2C%22side%22%2C%22severity%22%5D"
```

Expected: `{"message": [{"name": "...", "finding_type": "Cyst", "side": "Left", "severity": "Moderate"}]}`.

- [ ] **Step 5: Clean up the curl test data**

```bash
cd /workspace/development/frappe-bench
bench --site dev.localhost mariadb -e "select name from \`tabOPG Incidental Finding\` where report='$REPORT';"
```

Use the returned name(s) to delete via `bench --site dev.localhost execute frappe.delete_doc --kwargs "{'doctype': 'OPG Incidental Finding', 'name': '<name>', 'force': 1}"`, then delete the `$REPORT` and its patient the same way (pattern used throughout this session for cleaning up curl-created test data).

- [ ] **Step 6: Commit**

```bash
cd /workspace/development/frappe-bench/apps/dental_opg
git add frontend/src/api.js
git commit -m "Add incidental findings API functions to frontend"
```

---

### Task 4: `IncidentalFindingsCard.vue` + wire into `ReportEditor.vue`

**Files:**
- Create: `apps/dental_opg/frontend/src/components/IncidentalFindingsCard.vue`
- Modify: `apps/dental_opg/frontend/src/pages/ReportEditor.vue`

**Interfaces:**
- Consumes: `getIncidentalFindings`, `addIncidentalFinding`, `deleteIncidentalFinding` from `api.js` (Task 3).
- Produces: a `<IncidentalFindingsCard :report-name="report.name" />` component, self-contained (fetches its own data on mount, no parent state needed).

- [ ] **Step 1: Create the component**

Create `apps/dental_opg/frontend/src/components/IncidentalFindingsCard.vue`:

```vue
<template>
	<div class="rounded border bg-white p-4">
		<h2 class="mb-2 text-sm font-semibold text-gray-800">Incidental Findings</h2>

		<div v-if="findings.length" class="mb-3 space-y-1">
			<div
				v-for="row in findings"
				:key="row.name"
				class="flex items-center gap-2 rounded bg-gray-50 p-2 text-xs"
			>
				<span class="min-w-[8rem] flex-1">{{ row.finding_type }}</span>
				<span class="w-20 text-gray-600">{{ row.side }}</span>
				<span class="w-20 text-gray-600">{{ row.severity }}</span>
				<button class="text-red-600" @click="remove(row)">remove</button>
			</div>
		</div>

		<div class="flex flex-wrap items-center gap-2">
			<input
				v-model="form.finding_type"
				placeholder="Finding type"
				class="flex-1 rounded border px-2 py-1 text-xs"
			/>
			<select v-model="form.side" class="rounded border px-2 py-1 text-xs">
				<option value="">side...</option>
				<option>Left</option>
				<option>Right</option>
				<option>Bilateral</option>
			</select>
			<select v-model="form.severity" class="rounded border px-2 py-1 text-xs">
				<option value="">severity...</option>
				<option>Mild</option>
				<option>Moderate</option>
				<option>Severe</option>
			</select>
			<button
				class="rounded bg-gray-900 px-2 py-1 text-xs text-white disabled:opacity-50"
				:disabled="adding || !canAdd"
				@click="add"
			>
				{{ adding ? 'Adding...' : 'Add' }}
			</button>
		</div>
	</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { getIncidentalFindings, addIncidentalFinding, deleteIncidentalFinding } from '../api'

const props = defineProps({ reportName: { type: String, required: true } })

const findings = ref([])
const adding = ref(false)
const form = reactive({ finding_type: '', side: '', severity: '' })

const canAdd = computed(() => form.finding_type.trim() && form.side && form.severity)

onMounted(async () => {
	findings.value = await getIncidentalFindings(props.reportName)
})

async function add() {
	if (!canAdd.value) return
	adding.value = true
	try {
		const name = await addIncidentalFinding(props.reportName, {
			finding_type: form.finding_type.trim(),
			side: form.side,
			severity: form.severity,
		})
		findings.value = [...findings.value, { name, ...form }]
		form.finding_type = ''
		form.side = ''
		form.severity = ''
	} finally {
		adding.value = false
	}
}

async function remove(row) {
	await deleteIncidentalFinding(row.name)
	findings.value = findings.value.filter((r) => r.name !== row.name)
}
</script>
```

- [ ] **Step 2: Wire it into `ReportEditor.vue`**

Modify `apps/dental_opg/frontend/src/pages/ReportEditor.vue`. Add the import (alongside the other component imports near the top of the `<script setup>` block):

```javascript
import IncidentalFindingsCard from '../components/IncidentalFindingsCard.vue'
```

In the `<template>`, add the card after the `v-for` loop over `setup.section_order` and before the `generated_report_text` block:

```html
				<IncidentalFindingsCard :report-name="report.name" />

```

(i.e. insert it as a sibling between the closing `</template>` of the `v-for` section loop and the `<div v-if="report.generated_report_text" ...>` block.)

- [ ] **Step 3: Rebuild and verify no build errors**

Run: `cd /workspace/development/frappe-bench/apps/dental_opg/frontend && yarn build`

Expected: `✓ built in <N>s`, no Vue compiler errors.

Run: `cd /workspace/development/frappe-bench && bench build --app dental_opg`

Expected: `✔ Application Assets Linked` and `DONE`.

- [ ] **Step 4: Manual verification via curl (full round trip through the real page)**

```bash
cd /tmp
curl -s -c cookies_final.txt -X POST "http://dev.localhost:8000/api/method/login" -d "usr=Administrator&pwd=admin" -o /dev/null -w "login: %{http_code}\n"
curl -s -o /dev/null -w "dental_opg page: %{http_code}\n" -b cookies_final.txt "http://dev.localhost:8000/dental_opg/new"
```

Expected: both return `200`. Confirms the rebuilt SPA still serves correctly (catches any build/route regression before manual browser testing).

- [ ] **Step 5: Commit**

```bash
cd /workspace/development/frappe-bench/apps/dental_opg
git add frontend/src/components/IncidentalFindingsCard.vue frontend/src/pages/ReportEditor.vue
git commit -m "Add IncidentalFindingsCard to the reporting screen"
```

---

### Task 5: Final migrate + manual browser verification

**Files:** none (verification only)

- [ ] **Step 1: Migrate `dev.localhost`**

Run: `cd /workspace/development/frappe-bench && bench --site dev.localhost migrate`

Expected: no traceback, `Executing after_migrate hooks` near the end.

- [ ] **Step 2: Confirm the DocType is visible in Desk**

Run: `bench --site dev.localhost execute frappe.db.exists --args "['DocType', 'OPG Incidental Finding']"`

Expected: `OPG Incidental Finding` printed (not `None`).

- [ ] **Step 3: Tell the user it's ready for manual browser testing**

Report to the user: open an existing or new report at `http://dev.localhost:8000/dental_opg/<report-name>`, confirm the "Incidental Findings" card appears after the section cards, add one, confirm it appears in the list and also shows up in Desk's `OPG Incidental Finding` list view (`/app/opg-incidental-finding`), then remove it and confirm it disappears from both places.
