# DOCX Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a dentist export an OPG Report as a `.docx` file that visually matches the clinic's original letterhead, using the already-prepared template (`opg_report_template.docx`) and token map.

**Architecture:** A new `docx_export.py` module in `dental_opg_reporting/` (sibling to the existing `report_builder.py`, same pattern - business logic lives in the package, the doctype file just orchestrates + whitelists) fills the template's tokens and section markers, reusing the existing `build_report_sections()` as the single source of truth for finding text (already used by the PDF print format). A thin whitelisted module-level function `export_report_docx(name)` in `opg_report.py` calls it and returns the result as a file download - mirrors how Frappe's own `download_pdf` works (plain GET endpoint, `frappe.response.filecontent`, not a JSON-returning `run_doc_method` call).

**Tech Stack:** `python-docx` 1.2.0 (already installed in the bench env and added to `pyproject.toml` dependencies), Frappe Framework, Vue 3 frontend.

## Global Constraints

- The template (`apps/dental_opg/dental_opg/dental_opg_reporting/templates/opg_report_template.docx`) and its exact marker text are already built and committed (commit `5eeba0c`) - this plan only writes the code that fills it in. Do not regenerate or edit the template as part of this plan.
- Metadata tokens (each lives in its own single run - verified when the template was built): `{{patient_name}}`, `{{age}}`, `{{sex}}`, `{{registration_no}}`, `{{report_date}}`, `{{referred_by}}`, `{{radiographic_projection}}`, `{{clinical_diagnosis}}`, `{{reported_by}}`, `{{verified_by}}`.
- Image marker: `{{OPG_IMAGE}}` (a standalone body paragraph).
- Section markers, one per section, each a standalone body paragraph: `{{FINDINGS:CONDYLAR_MORPHOLOGY}}`, `{{FINDINGS:STYLOID_PROCESS}}`, `{{FINDINGS:MAXILLARY_SINUS}}`, `{{FINDINGS:INFERIOR_BORDER_OF_MANDIBLE}}`, `{{FINDINGS:MAXILLARY_ARCH}}` (bulleted paragraph style), `{{FINDINGS:MANDIBULAR_ARCH}}` (bulleted paragraph style), `{{FINDINGS:RADIOLOGIC_IMPRESSION}}`.
- Section heading text to match/delete when a section is empty (exact, after `.strip()`): `CONDYLAR MORPHOLOGY:`, `STYLOID PROCESS:`, `MAXILLARY SINUS:`, `INFERIOR BORDER OF MANDIBLE`, `MAXILLARY ARCH:`, `MANDIBULAR ARCH:`, `RADIOLOGIC IMPRESSION`.
- `build_report_sections(report)` (in `dental_opg.dental_opg_reporting.report_builder`, already exists) returns `[{"name": "CONDYLAR MORPHOLOGY", "lines": [...]}, ...]` for non-empty sections only, `name` uppercase with spaces - `.replace(" ", "_")` on `name` gives the exact section-marker key (e.g. `"CONDYLAR_MORPHOLOGY"`), confirmed by tracing `report_builder.SECTION_ORDER` against the template's marker keys.
- Always run `bench --site <site> migrate` after any DocType/hooks change (this plan makes none, but stated per this app's established convention). `bench` commands run from `/workspace/development/frappe-bench`.
- This project has no JS test runner - frontend verification is manual curl reproduction of real HTTP calls (established pattern this session), not a new test framework.

---

### Task 1: `docx_export.py` module (TDD)

**Files:**
- Create: `apps/dental_opg/dental_opg/dental_opg_reporting/docx_export.py`
- Create: `apps/dental_opg/dental_opg/tests/__init__.py` (already created, empty)
- Create: `apps/dental_opg/dental_opg/tests/test_docx_export.py`

**Interfaces:**
- Consumes: `build_report_sections(report)` from `dental_opg.dental_opg_reporting.report_builder` (existing).
- Produces: `build_docx(report) -> bytes` - takes an `OPG Report` document, returns the filled-in `.docx` file's bytes. `TEMPLATE_PATH` (module constant, the template's path).

- [ ] **Step 1: Write the failing tests**

Create `apps/dental_opg/dental_opg/tests/test_docx_export.py`:

```python
import io

import frappe
from docx import Document as DocxDocument
from frappe.tests import IntegrationTestCase

from dental_opg.dental_opg_reporting.docx_export import TEMPLATE_PATH, build_docx


class TestDocxExport(IntegrationTestCase):
	def setUp(self):
		self.patient = frappe.get_doc(
			doctype="OPG Patient",
			patient_name="Docx Export Test",
			age=45,
			sex="Female",
			registration_no=frappe.generate_hash(length=8),
		).insert()
		self.report = frappe.get_doc(
			doctype="OPG Report",
			patient=self.patient.name,
			reported_by="Dr. Test Reporter",
			verified_by="Dr. Test Verifier",
		).insert()

	def test_template_file_exists_and_opens(self):
		DocxDocument(str(TEMPLATE_PATH))

	def test_build_docx_fills_populated_sections_and_removes_empty_ones(self):
		self.report.save_findings(
			section_findings=[
				{"section": "Condylar Morphology", "finding": "csf-normal"},
			],
			tooth_findings=[],
		)
		self.report.reload()

		content = build_docx(self.report)
		result_doc = DocxDocument(io.BytesIO(content))
		all_text = "\n".join(p.text for p in result_doc.paragraphs)

		self.assertIn("Condylar morphology appears to be normal", all_text)
		self.assertNotIn("STYLOID PROCESS", all_text)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.tests.test_docx_export`

Expected: `ModuleNotFoundError: No module named 'dental_opg.dental_opg_reporting.docx_export'` (the module doesn't exist yet).

- [ ] **Step 3: Write `docx_export.py`**

Create `apps/dental_opg/dental_opg/dental_opg_reporting/docx_export.py`:

```python
import copy
import io
from pathlib import Path

import frappe
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches
from docx.text.paragraph import Paragraph
from frappe.utils.file_manager import get_file

from dental_opg.dental_opg_reporting.report_builder import build_report_sections

TEMPLATE_PATH = Path(__file__).parent / "templates" / "opg_report_template.docx"

BULLET_SECTIONS = {"MAXILLARY_ARCH", "MANDIBULAR_ARCH"}

SECTION_HEADINGS = {
	"CONDYLAR_MORPHOLOGY": "CONDYLAR MORPHOLOGY:",
	"STYLOID_PROCESS": "STYLOID PROCESS:",
	"MAXILLARY_SINUS": "MAXILLARY SINUS:",
	"INFERIOR_BORDER_OF_MANDIBLE": "INFERIOR BORDER OF MANDIBLE",
	"MAXILLARY_ARCH": "MAXILLARY ARCH:",
	"MANDIBULAR_ARCH": "MANDIBULAR ARCH:",
	"RADIOLOGIC_IMPRESSION": "RADIOLOGIC IMPRESSION",
}


def build_docx(report) -> bytes:
	"""Fill the clinic's docx template with one OPG Report's data, return the
	resulting .docx file as bytes."""
	doc = Document(str(TEMPLATE_PATH))

	patient = frappe.get_doc("OPG Patient", report.patient) if report.patient else None
	_replace_tokens(doc, _metadata_replacements(report, patient))
	_insert_image(doc, report)
	_fill_sections(doc, report)

	buffer = io.BytesIO()
	doc.save(buffer)
	return buffer.getvalue()


def _metadata_replacements(report, patient) -> dict:
	return {
		"{{patient_name}}": (patient.patient_name if patient else "") or "",
		"{{age}}": str(patient.age) if patient and patient.age else "",
		"{{sex}}": (patient.sex or "")[:1] if patient else "",
		"{{registration_no}}": (patient.registration_no if patient else "") or "",
		"{{report_date}}": frappe.utils.formatdate(report.report_date) if report.report_date else "",
		"{{referred_by}}": report.referred_by or "",
		"{{radiographic_projection}}": report.radiographic_projection or "OPG",
		"{{clinical_diagnosis}}": report.clinical_diagnosis or "",
		"{{reported_by}}": report.reported_by or "",
		"{{verified_by}}": report.verified_by or "",
	}


def _iter_all_paragraphs(doc):
	yield from doc.paragraphs
	for table in doc.tables:
		for row in table.rows:
			for cell in row.cells:
				yield from cell.paragraphs


def _replace_tokens(doc, replacements: dict):
	for p in _iter_all_paragraphs(doc):
		for run in p.runs:
			if run.text in replacements:
				run.text = replacements[run.text]


def _insert_image(doc, report):
	marker = next((p for p in doc.paragraphs if p.text == "{{OPG_IMAGE}}"), None)
	if marker is None:
		return
	marker.text = ""
	if not report.opg_image:
		return
	_, content = get_file(report.opg_image)
	marker.alignment = 1  # center
	run = marker.add_run()
	run.add_picture(io.BytesIO(content), width=Inches(6))


def _fill_sections(doc, report):
	sections_by_key = {s["name"].replace(" ", "_"): s["lines"] for s in build_report_sections(report)}

	for key, heading_text in SECTION_HEADINGS.items():
		marker_text = "{{FINDINGS:%s}}" % key
		marker = next((p for p in doc.paragraphs if p.text == marker_text), None)
		if marker is None:
			continue

		lines = sections_by_key.get(key)
		if not lines:
			heading = next((p for p in doc.paragraphs if p.text.strip() == heading_text), None)
			if heading is not None:
				heading._p.getparent().remove(heading._p)
			marker._p.getparent().remove(marker._p)
			continue

		style = marker.style
		marker.text = lines[0]
		last = marker
		for line in lines[1:]:
			last = _insert_paragraph_after(last, line, style)
			if key in BULLET_SECTIONS:
				_copy_numbering(marker, last)


def _insert_paragraph_after(reference_paragraph, text, style):
	new_p_elem = OxmlElement("w:p")
	reference_paragraph._p.addnext(new_p_elem)
	new_p = Paragraph(new_p_elem, reference_paragraph._parent)
	new_p.text = text
	new_p.style = style
	return new_p


def _copy_numbering(from_paragraph, to_paragraph):
	from_pPr = from_paragraph._p.pPr
	if from_pPr is None:
		return
	numPr = from_pPr.find(qn("w:numPr"))
	if numPr is None:
		return
	to_pPr = to_paragraph._p.get_or_add_pPr()
	to_pPr.append(copy.deepcopy(numPr))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.tests.test_docx_export`

Expected: `OK` with 2 tests run, 0 failures, 0 errors.

- [ ] **Step 5: Commit**

```bash
cd /workspace/development/frappe-bench/apps/dental_opg
git add dental_opg/dental_opg_reporting/docx_export.py dental_opg/tests/__init__.py dental_opg/tests/test_docx_export.py
git commit -m "Add docx_export module to fill the OPG Report docx template"
```

---

### Task 2: Whitelisted `export_report_docx` endpoint

**Files:**
- Modify: `apps/dental_opg/dental_opg/dental_opg_reporting/doctype/opg_report/opg_report.py`

**Interfaces:**
- Consumes: `build_docx(report)` from `dental_opg.dental_opg_reporting.docx_export` (Task 1).
- Produces: `export_report_docx(name: str)` - a module-level (not class method) whitelisted GET endpoint at `/api/method/dental_opg.dental_opg_reporting.doctype.opg_report.opg_report.export_report_docx?name=<report>`, matching this app's existing "doctype-level function" convention (module-root functions for logic that doesn't need `self` - see `api.md`) and Frappe's own `download_pdf` pattern (sets `frappe.response.filecontent` directly, not a JSON-returning `run_doc_method` call).

- [ ] **Step 1: Add the function**

Modify `apps/dental_opg/dental_opg/dental_opg_reporting/doctype/opg_report/opg_report.py`. Add this at the end of the file, after the `OPGReport` class (module level, not indented as a method):

```python


@frappe.whitelist(methods=["GET"])
def export_report_docx(name: str):
	from dental_opg.dental_opg_reporting.docx_export import build_docx

	report = frappe.get_doc("OPG Report", name)
	report.check_permission("read")

	content = build_docx(report)

	frappe.local.response.filename = f"{report.name}.docx"
	frappe.local.response.filecontent = content
	frappe.local.response.content_type = (
		"application/vnd.openxmlformats-officedocument.wordprocessingml.document"
	)
	frappe.local.response.type = "download"
```

- [ ] **Step 2: Verify via curl against the real site**

```bash
cd /tmp
curl -s -c cookies_docx.txt -X POST "http://dev.localhost:8000/api/method/login" -d "usr=Administrator&pwd=admin" -o /dev/null -w "login: %{http_code}\n"
TOKEN=$(curl -s -b cookies_docx.txt "http://dev.localhost:8000/dental_opg" | grep -oP 'window\["csrf_token"\] = "\K[^"]+')

CREATE=$(curl -s -b cookies_docx.txt -X POST "http://dev.localhost:8000/api/method/dental_opg.api.create_report" \
  -H "Content-Type: application/json" -H "X-Frappe-CSRF-Token: $TOKEN" -H "Referer: http://dev.localhost:8000/dental_opg/new" \
  -d '{"patient_name":"Docx Export Verify","age":28,"sex":"Male","registration_no":"REG-DOCX-VERIFY-01"}')
REPORT=$(echo "$CREATE" | python3 -c "import json,sys; print(json.load(sys.stdin)['message']['report'])")
echo "report=$REPORT"

curl -s -b cookies_docx.txt -X POST "http://dev.localhost:8000/api/method/frappe.client.set_value" \
  -H "Content-Type: application/json" -H "X-Frappe-CSRF-Token: $TOKEN" -H "Referer: http://dev.localhost:8000/dental_opg/new" \
  -d "{\"doctype\":\"OPG Report\",\"name\":\"$REPORT\",\"fieldname\":{\"reported_by\":\"Dr. Test\",\"verified_by\":\"Dr. Test2\"}}" -o /dev/null -w "set_value: %{http_code}\n"

curl -s -b cookies_docx.txt -X POST "http://dev.localhost:8000/api/method/run_doc_method" \
  -H "Content-Type: application/json" -H "X-Frappe-CSRF-Token: $TOKEN" -H "Referer: http://dev.localhost:8000/dental_opg/new" \
  -d "{\"dt\":\"OPG Report\",\"dn\":\"$REPORT\",\"method\":\"save_findings\",\"args\":{\"section_findings\":[{\"section\":\"Condylar Morphology\",\"finding\":\"csf-normal\"}],\"tooth_findings\":[]}}" -o /dev/null -w "save_findings: %{http_code}\n"

curl -s -b cookies_docx.txt "http://dev.localhost:8000/api/method/dental_opg.dental_opg_reporting.doctype.opg_report.opg_report.export_report_docx?name=$REPORT" \
  -o /tmp/export_verify.docx -D /tmp/export_verify_headers.txt -w "export: %{http_code}\n"

echo "--- response headers ---"
cat /tmp/export_verify_headers.txt
echo "--- file check ---"
file /tmp/export_verify.docx
echo "$REPORT" > /tmp/docx_export_verify_report.txt
```

Expected: `export: 200`, headers include `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document` and a `Content-Disposition: attachment` header with the report's name as filename, and `file /tmp/export_verify.docx` reports it as a valid Microsoft Word / Zip archive document (not corrupted).

- [ ] **Step 3: Verify the content is actually correct, not just a valid file**

```bash
/workspace/development/frappe-bench/env/bin/python3 -c "
from docx import Document
doc = Document('/tmp/export_verify.docx')
all_text = '\n'.join(p.text for p in doc.paragraphs)
assert 'Docx Export Verify' in all_text, 'patient name not filled in'
assert 'Condylar morphology appears to be normal' in all_text, 'finding not filled in'
assert 'STYLOID PROCESS' not in all_text, 'empty section heading should be removed'
assert '{{' not in all_text, 'a token was left unfilled: ' + all_text
print('content verified OK')
"
```

Expected: `content verified OK` with no assertion errors.

- [ ] **Step 4: Clean up the verification test data**

```bash
cd /workspace/development/frappe-bench
REPORT=$(cat /tmp/docx_export_verify_report.txt)
bench --site dev.localhost mariadb -e "select patient from \`tabOPG Report\` where name='$REPORT';"
```

Use the returned patient name to delete both via `bench --site dev.localhost execute frappe.delete_doc --kwargs "{'doctype': 'OPG Report', 'name': '$REPORT', 'force': 1}"` and the equivalent for the patient (pattern used throughout this session for curl-created test data cleanup).

- [ ] **Step 5: Commit**

```bash
cd /workspace/development/frappe-bench/apps/dental_opg
git add dental_opg/dental_opg_reporting/doctype/opg_report/opg_report.py
git commit -m "Add export_report_docx whitelisted endpoint"
```

---

### Task 3: Frontend "Export DOCX" button

**Files:**
- Modify: `apps/dental_opg/frontend/src/pages/ReportEditor.vue`

**Interfaces:**
- Consumes: `/api/method/dental_opg.dental_opg_reporting.doctype.opg_report.opg_report.export_report_docx` (Task 2), same plain-link download pattern as the existing Print/Get PDF buttons.

- [ ] **Step 1: Add the button**

Modify `apps/dental_opg/frontend/src/pages/ReportEditor.vue`. Find the header button row containing the existing Print link:

```html
				<a class="actionbtn inline-block" :href="printUrl" target="_blank">Print</a>
```

Add a new link right after it, in the same `<div class="ml-auto flex gap-2">` container:

```html
				<a class="actionbtn inline-block" :href="printUrl" target="_blank">Print</a>
				<a class="actionbtn inline-block" :href="docxExportUrl">Export DOCX</a>
```

Add a matching computed property next to the existing `printUrl` computed (in the `<script setup>` block):

```javascript
const printUrl = computed(
	() => `/printview?doctype=OPG%20Report&name=${encodeURIComponent(report.name || '')}&format=OPG%20Report`,
)
const docxExportUrl = computed(
	() =>
		`/api/method/dental_opg.dental_opg_reporting.doctype.opg_report.opg_report.export_report_docx?name=${encodeURIComponent(report.name || '')}`,
)
```

- [ ] **Step 2: Rebuild and verify no build errors**

Run: `cd /workspace/development/frappe-bench/apps/dental_opg/frontend && yarn build`

Expected: `✓ built in <N>s`, no Vue compiler errors.

Run: `cd /workspace/development/frappe-bench && bench build --app dental_opg`

Expected: `✔ Application Assets Linked` and `DONE`.

- [ ] **Step 3: Verify the page still loads and the link is present**

```bash
cd /tmp
curl -s -c cookies_docx2.txt -X POST "http://dev.localhost:8000/api/method/login" -d "usr=Administrator&pwd=admin" -o /dev/null -w "login: %{http_code}\n"
curl -s -o /dev/null -w "dental_opg page: %{http_code}\n" -b cookies_docx2.txt "http://dev.localhost:8000/dental_opg/new"
grep -o "Export DOCX" /workspace/development/frappe-bench/apps/dental_opg/frontend/src/pages/ReportEditor.vue
```

Expected: `200` and `Export DOCX` printed (confirms the button text is actually in the source that got built).

- [ ] **Step 4: Commit**

```bash
cd /workspace/development/frappe-bench/apps/dental_opg
git add frontend/src/pages/ReportEditor.vue
git commit -m "Add Export DOCX button to the reporting screen"
```

---

### Task 4: Final migrate + manual verification

**Files:** none (verification only)

- [ ] **Step 1: Migrate `dev.localhost`**

Run: `cd /workspace/development/frappe-bench && bench --site dev.localhost migrate`

Expected: no traceback, `Executing after_migrate hooks` near the end.

- [ ] **Step 2: Tell the user it's ready for manual verification**

Report to the user: open an existing report at `http://dev.localhost:8000/dental_opg/<report-name>`, click "Export DOCX", confirm the downloaded file opens correctly in Word/LibreOffice and visually matches the clinic's letterhead (logo, banner, table borders/shading, footer bars) with the report's actual data filled in.
