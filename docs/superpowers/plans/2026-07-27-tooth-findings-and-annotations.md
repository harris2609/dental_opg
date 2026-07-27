# Tooth Findings Overhaul + Printed Annotations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the invented tooth-finding master list with the clinic's real 21 findings/descriptions, change the report line format to `"irt {tooth} - {description}"` with automatic Radiologic Impression summarization, support multi-tooth selection with report-line merging, make the generated report text editable, and bake image annotations into the actual image used by both the PDF print format and the docx export.

**Architecture:** Schema/fixture changes to `OPG Tooth Finding` (master) and `OPG Tooth Finding Entry` (child table) come first since everything else depends on the new field shape. `report_builder.py`'s tooth-finding assembly is rewritten to read the entry's own stored description directly (no more master-template re-lookup) and to group identical entries across teeth into one merged line. A new `image_utils.py` (Pillow) bakes annotations into image bytes, shared by a new print-format image endpoint and the existing docx export. `ToothChart.vue` is rewritten with a dropdown-add-finding flow (matching `SectionCard.vue`'s existing pattern) plus a multi-tooth-select mode.

**Tech Stack:** Frappe Framework, `Pillow` (already installed in the bench env; added to `pyproject.toml` for production-safety, same treatment as `python-docx` earlier), Vue 3 frontend.

## Global Constraints

- All 21 findings from `opgcommonfindings.docx` apply uniformly as tooth-click options (confirmed with the user) - multi-part (Coronally/Radicularly/Periapically) descriptions are joined into one text block per finding.
- Report line format: `"irt {tooth_number(s)} - {description}"`, tooth numbers comma-joined when multiple teeth share an identical (finding_name, description) pair within the same arch section - grouped at render time in `report_builder.py`, not stored as a linked group in the data model.
- Radiologic Impression gets one line per **distinct** `finding_name` across all tooth findings (deduplicated, not once per tooth or per merged-line-group).
- `OPG Tooth Finding Entry` drops `is_custom`/`custom_text` - every entry always has `finding_name` (Data) and `description` (Small Text) populated, `finding` (Link) populated only when chosen from the master dropdown.
- Annotations get baked into actual image pixels (Pillow), shared by both the print format and the docx export - not an HTML/SVG overlay, since wkhtmltopdf can't reliably know the rendered image's pixel box at PDF-generation time to align an overlay against.
- Always run `bench --site <site> migrate` after any DocType/fixture change. `bench` commands run from `/workspace/development/frappe-bench` (bench root). Test site is `dental_opg-test.localhost` (already exists). Human-active dev site is `dev.localhost` - only touch data you create yourself there, clean it up after.
- This project has no JS test runner - frontend verification is manual curl reproduction of real HTTP calls plus a `yarn build` check, not a new test framework.

---

### Task 1: Schema + fixture data for `OPG Tooth Finding` / `OPG Tooth Finding Entry`

**Files:**
- Modify: `apps/dental_opg/dental_opg/dental_opg_reporting/doctype/opg_tooth_finding/opg_tooth_finding.json`
- Modify: `apps/dental_opg/dental_opg/dental_opg_reporting/doctype/opg_tooth_finding_entry/opg_tooth_finding_entry.json`
- Modify: `apps/dental_opg/dental_opg/fixtures/opg_tooth_finding.json` (full replacement)

**Interfaces:**
- Produces: `OPG Tooth Finding` with fields `finding_name` (Data, reqd), `description_template` (Small Text, reqd, renamed from `finding_template`), `active` (Check). `OPG Tooth Finding Entry` with fields `tooth_number`, `arch`, `finding` (Link, optional), `finding_name` (Data, reqd), `description` (Small Text, reqd) - `is_custom`/`custom_text` removed.

- [ ] **Step 1: Replace `opg_tooth_finding.json`**

Replace the full contents of `apps/dental_opg/dental_opg/dental_opg_reporting/doctype/opg_tooth_finding/opg_tooth_finding.json` with:

```json
{
    "name": "OPG Tooth Finding",
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
            "fieldname": "finding_name",
            "fieldtype": "Data",
            "label": "Finding Name",
            "reqd": 1,
            "in_list_view": 1
        },
        {
            "fieldname": "description_template",
            "fieldtype": "Small Text",
            "label": "Description Template",
            "description": "Canned description shown when this finding is picked for a tooth - editable per entry afterward.",
            "reqd": 1
        },
        {
            "fieldname": "active",
            "fieldtype": "Check",
            "label": "Active",
            "default": "1",
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

- [ ] **Step 2: Replace `opg_tooth_finding_entry.json`**

Replace the full contents of `apps/dental_opg/dental_opg/dental_opg_reporting/doctype/opg_tooth_finding_entry/opg_tooth_finding_entry.json` with:

```json
{
    "name": "OPG Tooth Finding Entry",
    "module": "Dental OPG Reporting",
    "doctype": "DocType",
    "engine": "InnoDB",
    "istable": 1,
    "autoname": "hash",
    "naming_rule": "Random",
    "fields": [
        {
            "fieldname": "tooth_number",
            "fieldtype": "Data",
            "label": "Tooth Number (FDI)",
            "reqd": 1,
            "in_list_view": 1
        },
        {
            "fieldname": "arch",
            "fieldtype": "Select",
            "label": "Arch",
            "options": "Maxillary\nMandibular",
            "in_list_view": 1
        },
        {
            "fieldname": "finding",
            "fieldtype": "Link",
            "label": "Tooth Finding",
            "options": "OPG Tooth Finding",
            "in_list_view": 1
        },
        {
            "fieldname": "finding_name",
            "fieldtype": "Data",
            "label": "Finding Name",
            "reqd": 1,
            "in_list_view": 1
        },
        {
            "fieldname": "description",
            "fieldtype": "Small Text",
            "label": "Description",
            "reqd": 1
        }
    ]
}
```

- [ ] **Step 3: Replace the fixture data**

Replace the full contents of `apps/dental_opg/dental_opg/fixtures/opg_tooth_finding.json` with (21 findings extracted from `opgcommonfindings.docx`, multi-part Coronally/Radicularly/Periapically descriptions joined into one block per finding, confirmed with the user):

```json
[
    {
        "doctype": "OPG Tooth Finding",
        "name": "dental-caries",
        "finding_name": "Dental Caries",
        "description_template": "Coronally- an ill-defined radiolucency involving enamel and dentin on the mesial aspect Radicularly-no changes appreciated Periapically- no changes appreciated",
        "active": 1
    },
    {
        "doctype": "OPG Tooth Finding",
        "name": "dental-caries-involving-pulp",
        "finding_name": "Dental Caries Involving Pulp",
        "description_template": "Coronally- an ill-defined radiolucency involving enamel dentin and approximating pulp on the mesial aspect Radicularly-no changes appreciated Periapically- no changes appreciated",
        "active": 1
    },
    {
        "doctype": "OPG Tooth Finding",
        "name": "secondary-caries",
        "finding_name": "Secondary Caries",
        "description_template": "Coronally-a well-defined radiopacity noted s/o restorative material beneath which ill defined radiolucency approximating pulp noted Radicularly-no changes appreciated Periapically- no changes appreciated.",
        "active": 1
    },
    {
        "doctype": "OPG Tooth Finding",
        "name": "periapical-abscess",
        "finding_name": "Periapical Abscess",
        "description_template": "Coronally-an ill-defined radiolucency involving enamel dentin and approximating pulp on the mesioproximal aspect noted Radicularly- no changes appreciated Periapically - loss of lamina dura with ill defined hazy radiolucency noted",
        "active": 1
    },
    {
        "doctype": "OPG Tooth Finding",
        "name": "chronic-apical-periodontitis",
        "finding_name": "Chronic Apical Periodontitis",
        "description_template": "Coronally-an ill-defined radiolucency involving enamel dentin and approximating pulp on the mesioproximal aspect noted Radicularly- no changes appreciated Periapically – widening of pdl space noted",
        "active": 1
    },
    {
        "doctype": "OPG Tooth Finding",
        "name": "grossly-decayed",
        "finding_name": "Grossly Decayed",
        "description_template": "Coronally- an ill-defined radiolucency involving enamel dentin and approximating pulp with partial loss of crown structure Radicularly-no changes appreciated Periapically- no changes appreciated",
        "active": 1
    },
    {
        "doctype": "OPG Tooth Finding",
        "name": "root-stumps",
        "finding_name": "Root Stumps",
        "description_template": "Coronally- complete loss of crown structure Radicularly-no changes appreciated Periapically- no changes appreciated",
        "active": 1
    },
    {
        "doctype": "OPG Tooth Finding",
        "name": "root-caries",
        "finding_name": "Root Caries",
        "description_template": "Coronally- an ill-defined radiolucency involving enamel dentin and approximating pulp on the mesial aspect Radicularly- ill defined radiolucency noted on the cervical third approximating canals Periapically- no changes appreciated",
        "active": 1
    },
    {
        "doctype": "OPG Tooth Finding",
        "name": "incompletely-endodontically-treated-tooth",
        "finding_name": "Incompletely Endodontically Treated Tooth",
        "description_template": "Coronally- a well-defined radiopacity noted along with partial loss of crown structure; Radicularly - homogenous thin linear radiopacity noted involving the root canal s/o endodontic restorative material periapically - no changes appreciated.",
        "active": 1
    },
    {
        "doctype": "OPG Tooth Finding",
        "name": "restoration",
        "finding_name": "Restoration",
        "description_template": "Coronally- a well-defined radiopacity involving enamel noted;s/o restorative material Radicularly-no changes appreciated Periapically- no changes appreciated",
        "active": 1
    },
    {
        "doctype": "OPG Tooth Finding",
        "name": "prosthetic-crown",
        "finding_name": "Prosthetic Crown",
        "description_template": "Coronally- a well-defined radiopacity noted;s/o prosthetic crown Radicularly-no changes appreciated Periapically- no changes appreciated",
        "active": 1
    },
    {
        "doctype": "OPG Tooth Finding",
        "name": "incompletely-endodontically-treated-tooth-with-rarefying-osteitis",
        "finding_name": "Incompletely Endodontically Treated Tooth With Rarefying Osteitis",
        "description_template": "Coronally- a well-defined radiopacity noted along with partial loss of crown structure; Radicularly - homogenous thin linear radiopacity which is 3-4mm short of apex involving the root canal s/o endodontic restorative material periapically - ill defined hazy radiolucency with loss of lamina dura noted",
        "active": 1
    },
    {
        "doctype": "OPG Tooth Finding",
        "name": "mesioangular-impaction",
        "finding_name": "Mesioangular Impaction",
        "description_template": "A dense radiopaque structure with density and morphology similar to that of a tooth with it’s long axis is mesially inclined to that of adjacent tooth,The mesial portion crown is at the level of cervical third of adjacent tooth.The root formation is incomplete.The apical third of roots are in close approximation to inferior alveolar nerve canal suggestive of mesioangular impaction.",
        "active": 1
    },
    {
        "doctype": "OPG Tooth Finding",
        "name": "distoangular-impaction",
        "finding_name": "Distoangular Impaction",
        "description_template": "A dense radiopaque structure with density and morphology similar to that of a tooth noted ,the crown at the level of cervical third with it’s long axis distally oriented to that of adjacent tooth, root formation is incomplete ,suggestive of distoangular impaction.",
        "active": 1
    },
    {
        "doctype": "OPG Tooth Finding",
        "name": "horizontal-impaction",
        "finding_name": "Horizontal Impaction",
        "description_template": "A dense radiopaque structure with density and morphology similar to that of tooth a with it’s long axis is perpendicular to that of adjacent tooth,The tooth is embedded inside the bone except the distal cusp which is at the level of occlusal third of adjacent tooth.The root formation is incomplete.The follicular space is increased .The tooth in close approximation to inferior alveolar nerve canal suggestive of horizontal impaction.",
        "active": 1
    },
    {
        "doctype": "OPG Tooth Finding",
        "name": "vertical-impaction",
        "finding_name": "Vertical Impaction",
        "description_template": "A dense radiopaque structure with density and morphology similar to that of a tooth with it’s long axis parallel to that of adjacent tooth noted.The crown is embedded inside the bone and is at the level of cervical third of adjacent tooth.The root formation is complete .The follicular space is increased .The apical third of roots are in close approximation to inferior alveolar nerve canal suggestive of vertical impaction.",
        "active": 1
    },
    {
        "doctype": "OPG Tooth Finding",
        "name": "partially-edentulous",
        "finding_name": "Partially Edentulous",
        "description_template": "Partial complement set of permanent dentition noted, with missing wrt",
        "active": 1
    },
    {
        "doctype": "OPG Tooth Finding",
        "name": "periodontitis",
        "finding_name": "Periodontitis",
        "description_template": "The crest of the alveolar ridge is at the level of middle third of the roots of all the teeth except wrt 41 31 which is at the apical third of the root",
        "active": 1
    },
    {
        "doctype": "OPG Tooth Finding",
        "name": "generalised-attrition",
        "finding_name": "Generalised Attrition",
        "description_template": "Irt all teeth - coronally - flattening of inscisal edge and cusps involving enamel and dentin noted s/o attrition",
        "active": 1
    },
    {
        "doctype": "OPG Tooth Finding",
        "name": "idiopathic-osteosclerosis",
        "finding_name": "Idiopathic Osteosclerosis",
        "description_template": "Ill defined hazy radiopacity noted between the apical region of 11 and 12 region s/o idiopathic osteosclerosis.",
        "active": 1
    },
    {
        "doctype": "OPG Tooth Finding",
        "name": "soft-tissue-calcification",
        "finding_name": "Soft Tissue Calcification",
        "description_template": "Wrt laryngeal cartilage region below the level of hyoid bone a discrete radiopacity and a linear radiopacity noted s/o soft tissue calcification.",
        "active": 1
    }
]
```

- [ ] **Step 4: Migrate the test site and verify**

Run: `bench --site dental_opg-test.localhost migrate`

Expected: no traceback anywhere in the output.

Run: `bench --site dental_opg-test.localhost execute frappe.db.count --args "['OPG Tooth Finding']"`

Expected: `30` at this point (21 new + 9 old - fixture sync only upserts what's listed in the file, it does not delete records that existed before but are no longer present, so the old 9 are still there; the next step removes them).

- [ ] **Step 5: Delete the 9 old finding master records**

Fixture sync doesn't delete records missing from the fixture file, so the previous invented findings (`missing`, `caries`, `root-stump`, `impacted`, `restored`, `fracture`, `bone-loss`, `periapical-radiolucency`, `mobility`) are still sitting in the database as orphaned `OPG Tooth Finding` records after Step 4 and must be removed explicitly:

```bash
cd /workspace/development/frappe-bench
for name in missing caries root-stump impacted restored fracture bone-loss periapical-radiolucency mobility; do
  bench --site dental_opg-test.localhost execute frappe.delete_doc --kwargs "{'doctype': 'OPG Tooth Finding', 'name': '$name', 'force': 1}"
done
bench --site dental_opg-test.localhost execute frappe.db.count --args "['OPG Tooth Finding']"
```

Expected: the final count command prints `21`.

Note for a later task: this same cleanup needs to run against `dev.localhost` too (Task 6's final migrate) - `dev.localhost` is the site a human has been actively testing against, so also check for and flag (don't silently delete) any pre-existing `OPG Report` documents whose `tooth_findings` child rows reference the old schema (`is_custom`/`custom_text`, now-removed fields) - those rows will just display with blank `finding_name`/`description` after migration since the columns they used no longer exist, which is acceptable for dev/test data but worth surfacing to the user rather than assuming silently.

- [ ] **Step 6: Commit**

```bash
cd /workspace/development/frappe-bench/apps/dental_opg
git add dental_opg/dental_opg_reporting/doctype/opg_tooth_finding/opg_tooth_finding.json \
        dental_opg/dental_opg_reporting/doctype/opg_tooth_finding_entry/opg_tooth_finding_entry.json \
        dental_opg/fixtures/opg_tooth_finding.json
git commit -m "Replace tooth finding master list with the clinic's real 21 findings"
```

---

### Task 2: `report_builder.py` rewrite - irt format, merging, Radiologic Impression summary (TDD)

**Files:**
- Modify: `apps/dental_opg/dental_opg/dental_opg_reporting/report_builder.py`
- Create: `apps/dental_opg/dental_opg/tests/test_report_builder.py`

**Interfaces:**
- Consumes: `OPG Tooth Finding Entry` rows now have `finding_name`/`description` (Task 1).
- Produces: `build_report_sections(report)` (existing signature, unchanged) - tooth-finding lines now read as `"irt {tooth_number(s)} - {description}"`, merged across teeth sharing an identical `(finding_name, description)` pair per arch section; Radiologic Impression gets deduplicated `finding_name` lines appended.

- [ ] **Step 1: Write the failing tests**

Create `apps/dental_opg/dental_opg/tests/test_report_builder.py`:

```python
import frappe
from frappe.tests import IntegrationTestCase

from dental_opg.dental_opg_reporting.report_builder import build_report_sections


class TestReportBuilderToothFindings(IntegrationTestCase):
	def setUp(self):
		self.patient = frappe.get_doc(
			doctype="OPG Patient",
			patient_name="Report Builder Test",
			registration_no=frappe.generate_hash(length=8),
		).insert()
		self.report = frappe.get_doc(
			doctype="OPG Report",
			patient=self.patient.name,
		).insert()

	def test_tooth_findings_merge_identical_finding_across_teeth(self):
		self.report.save_findings(
			section_findings=[],
			tooth_findings=[
				{"tooth_number": "16", "arch": "Maxillary", "finding_name": "Dental Caries", "description": "desc A"},
				{"tooth_number": "17", "arch": "Maxillary", "finding_name": "Dental Caries", "description": "desc A"},
				{"tooth_number": "26", "arch": "Maxillary", "finding_name": "Dental Caries", "description": "desc B edited"},
			],
		)
		self.report.reload()

		sections = build_report_sections(self.report)
		maxillary = next(s for s in sections if s["name"] == "MAXILLARY ARCH")

		self.assertIn("irt 16, 17 - desc A", maxillary["lines"])
		self.assertIn("irt 26 - desc B edited", maxillary["lines"])

	def test_radiologic_impression_lists_distinct_tooth_finding_names(self):
		self.report.save_findings(
			section_findings=[],
			tooth_findings=[
				{"tooth_number": "16", "arch": "Maxillary", "finding_name": "Dental Caries", "description": "desc A"},
				{"tooth_number": "26", "arch": "Maxillary", "finding_name": "Dental Caries", "description": "desc B"},
				{"tooth_number": "46", "arch": "Mandibular", "finding_name": "Root Stumps", "description": "desc C"},
			],
		)
		self.report.reload()

		sections = build_report_sections(self.report)
		impression = next(s for s in sections if s["name"] == "RADIOLOGIC IMPRESSION")

		self.assertEqual(impression["lines"].count("Dental Caries"), 1)
		self.assertIn("Root Stumps", impression["lines"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.tests.test_report_builder`

Expected: failures - `"irt 16, 17 - desc A"` not found in maxillary lines (old code still produces `"Tooth 16: Dental Caries"`-style text and does its own `OPG Tooth Finding` lookup which no longer matches these ad-hoc dict rows the same way).

- [ ] **Step 3: Rewrite `report_builder.py`**

Replace the full contents of `apps/dental_opg/dental_opg/dental_opg_reporting/report_builder.py` with:

```python
import frappe

SECTION_ORDER = [
	"Condylar Morphology",
	"Styloid Process",
	"Maxillary Sinus",
	"Inferior Border of Mandible",
	"Maxillary Arch",
	"Mandibular Arch",
	"Radiologic Impression",
]

ARCH_TO_SECTION = {
	"Maxillary": "Maxillary Arch",
	"Mandibular": "Mandibular Arch",
}

SIDE_PHRASES = {
	"Left": "left",
	"Right": "right",
	"Bilateral": "bilateral",
}


class _SafeDict(dict):
	def __missing__(self, key):
		return ""


def _render_template(template, **kwargs):
	return " ".join(template.format_map(_SafeDict(**kwargs)).split())


def _section_finding_lines(report):
	standard_finding_names = {row.finding for row in report.section_findings if row.finding}
	templates = {}
	if standard_finding_names:
		templates = {
			row.name: row.finding_template
			for row in frappe.get_all(
				"OPG Standard Finding",
				filters={"name": ["in", list(standard_finding_names)]},
				fields=["name", "finding_template"],
			)
		}

	lines_by_section = {section: [] for section in SECTION_ORDER}
	for row in report.section_findings:
		if row.is_custom or not row.finding:
			text = (row.custom_text or "").strip()
		else:
			template = templates.get(row.finding, "")
			text = _render_template(
				template,
				side=SIDE_PHRASES.get(row.side, row.side or ""),
				tooth_number=row.tooth_number or "",
				level=(row.level or "").lower(),
			)
		if text and row.section in lines_by_section:
			lines_by_section[row.section].append(text)
	return lines_by_section


def _tooth_finding_lines(report):
	"""One line per distinct (arch section, finding_name, description) group,
	tooth numbers merged in first-seen order - so selecting the same finding
	with the same (possibly edited) description on multiple teeth produces one
	combined "irt 16, 17 - ..." line instead of a separate line per tooth. If
	a dentist edits one tooth's description independently afterward, that
	entry naturally falls out of the group (its text no longer matches) and
	prints as its own line - no explicit "linked group" state to maintain."""
	groups = {}
	order = []
	for row in report.tooth_findings:
		section = ARCH_TO_SECTION.get(row.arch)
		if not section:
			continue
		key = (section, row.finding_name, row.description)
		if key not in groups:
			groups[key] = []
			order.append(key)
		groups[key].append(row.tooth_number)

	lines_by_arch_section = {"Maxillary Arch": [], "Mandibular Arch": []}
	for key in order:
		section, finding_name, description = key
		if not (finding_name and description):
			continue
		tooth_numbers = ", ".join(groups[key])
		lines_by_arch_section[section].append(f"irt {tooth_numbers} - {description}")
	return lines_by_arch_section


def _distinct_tooth_finding_names(report):
	"""Deduplicated finding names across all tooth findings (both arches),
	first-seen order, for the Radiologic Impression summary."""
	seen = []
	for row in report.tooth_findings:
		if row.finding_name and row.finding_name not in seen:
			seen.append(row.finding_name)
	return seen


def build_report_sections(report):
	"""Structured (section name, lines) pairs in fixed order, skipping empty
	sections. Used by the print format so each section heading can be styled
	(bold + underline) separately from its plain finding lines."""
	section_lines = _section_finding_lines(report)
	tooth_lines = _tooth_finding_lines(report)
	for section, extra_lines in tooth_lines.items():
		section_lines[section].extend(extra_lines)

	for finding_name in _distinct_tooth_finding_names(report):
		section_lines["Radiologic Impression"].append(finding_name)

	sections = []
	for section in SECTION_ORDER:
		lines = section_lines.get(section) or []
		if lines:
			sections.append({"name": section.upper(), "lines": lines})
	return sections


def build_report_text(report):
	"""Assemble deterministic, template-based narrative text from structured findings on an OPG Report doc."""
	blocks = [f"{section['name']}:\n" + "\n".join(section["lines"]) for section in build_report_sections(report)]
	return "\n\n".join(blocks)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.tests.test_report_builder`

Expected: `OK` with 2 tests run, 0 failures.

Also run the existing full suite to confirm nothing else broke:

Run: `bench --site dental_opg-test.localhost run-tests --app dental_opg`

Expected: `OK`, all tests passing (this app has other pre-existing tests for `OPGReport`/docx export that must continue to pass unchanged).

- [ ] **Step 5: Commit**

```bash
cd /workspace/development/frappe-bench/apps/dental_opg
git add dental_opg/dental_opg_reporting/report_builder.py dental_opg/tests/test_report_builder.py
git commit -m "Rewrite tooth-finding report assembly: irt format, merging, Radiologic Impression summary"
```

---

### Task 3: `image_utils.py` - bake annotations into image pixels (TDD)

**Files:**
- Create: `apps/dental_opg/dental_opg/dental_opg_reporting/image_utils.py`
- Create: `apps/dental_opg/dental_opg/tests/test_image_utils.py`
- Modify: `apps/dental_opg/pyproject.toml`

**Interfaces:**
- Produces: `get_annotated_image_bytes(report) -> bytes | None` - `None` if no image, original bytes unchanged if no annotations, otherwise a flattened JPEG with all annotations drawn onto it.

- [ ] **Step 1: Add the `Pillow` dependency**

Modify `apps/dental_opg/pyproject.toml`. Current `dependencies` block:

```toml
dependencies = [
    # "frappe~=16.0.0" # Installed and managed by bench.
    "python-docx~=1.2.0",
]
```

Change to:

```toml
dependencies = [
    # "frappe~=16.0.0" # Installed and managed by bench.
    "python-docx~=1.2.0",
    "Pillow~=12.2.0",
]
```

(Already installed in this bench's Python environment - this just makes it a declared, production-safe dependency, same treatment `python-docx` got earlier.)

- [ ] **Step 2: Write the failing tests**

Create `apps/dental_opg/dental_opg/tests/test_image_utils.py`:

```python
import io

import frappe
from frappe.tests import IntegrationTestCase
from PIL import Image

from dental_opg.dental_opg_reporting.image_utils import get_annotated_image_bytes


def _make_test_jpeg_bytes():
	buffer = io.BytesIO()
	Image.new("RGB", (100, 60), color=(200, 200, 200)).save(buffer, format="JPEG")
	return buffer.getvalue()


class TestImageUtils(IntegrationTestCase):
	def setUp(self):
		self.patient = frappe.get_doc(
			doctype="OPG Patient",
			patient_name="Image Utils Test",
			registration_no=frappe.generate_hash(length=8),
		).insert()
		self.report = frappe.get_doc(
			doctype="OPG Report",
			patient=self.patient.name,
		).insert()

	def test_no_image_returns_none(self):
		self.assertIsNone(get_annotated_image_bytes(self.report))

	def test_image_with_no_annotations_returns_original_bytes(self):
		original_bytes = _make_test_jpeg_bytes()
		self._attach_image(original_bytes)

		result = get_annotated_image_bytes(self.report)
		self.assertEqual(result, original_bytes)

	def test_image_with_annotations_differs_from_original(self):
		original_bytes = _make_test_jpeg_bytes()
		self._attach_image(original_bytes)
		self.report.save_annotations(
			annotations=[{"annotation_type": "Point", "x": 0.5, "y": 0.5, "color": "#ff0000"}]
		)
		self.report.reload()

		result = get_annotated_image_bytes(self.report)
		self.assertNotEqual(result, original_bytes)

	def _attach_image(self, content):
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"attached_to_doctype": "OPG Report",
				"attached_to_name": self.report.name,
				"attached_to_field": "opg_image",
				"file_name": "test_opg.jpg",
				"content": content,
				"is_private": 0,
			}
		).insert()
		self.report.opg_image = file_doc.file_url
		self.report.save()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.tests.test_image_utils`

Expected: `ModuleNotFoundError: No module named 'dental_opg.dental_opg_reporting.image_utils'`.

- [ ] **Step 4: Write `image_utils.py`**

Create `apps/dental_opg/dental_opg/dental_opg_reporting/image_utils.py`:

```python
import io
import json
import math

from PIL import Image, ImageDraw, ImageFont
from frappe.utils.file_manager import get_file


def _denormalize(x, y, width, height):
	return x * width, y * height


def _draw_point(draw, ann, width, height):
	cx, cy = _denormalize(ann.x or 0, ann.y or 0, width, height)
	radius = max(4, int(min(width, height) * 0.007))
	color = ann.color or "#ff0000"
	draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=color)


def _draw_arrow(draw, ann, width, height):
	x1, y1 = _denormalize(ann.x or 0, ann.y or 0, width, height)
	x2, y2 = _denormalize(ann.x2 or 0, ann.y2 or 0, width, height)
	color = ann.color or "#ff0000"
	line_width = max(2, int(min(width, height) * 0.003))
	draw.line([x1, y1, x2, y2], fill=color, width=line_width)

	angle = math.atan2(y2 - y1, x2 - x1)
	arrow_len = max(10, int(min(width, height) * 0.02))
	for delta in (0.4, -0.4):
		ax = x2 - arrow_len * math.cos(angle + delta)
		ay = y2 - arrow_len * math.sin(angle + delta)
		draw.line([x2, y2, ax, ay], fill=color, width=line_width)


def _draw_text(draw, ann, width, height):
	x1, y1 = _denormalize(ann.x or 0, ann.y or 0, width, height)
	color = ann.color or "#ff0000"
	font_size = max(14, int(min(width, height) * 0.03))
	try:
		font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
	except OSError:
		font = ImageFont.load_default()
	draw.text((x1, y1), ann.label_text or "", fill=color, font=font)


def _draw_freehand(draw, ann, width, height):
	if not ann.path_data:
		return
	points = json.loads(ann.path_data)
	coords = [_denormalize(p["x"], p["y"], width, height) for p in points]
	if len(coords) > 1:
		color = ann.color or "#ff0000"
		line_width = max(2, int(min(width, height) * 0.003))
		draw.line(coords, fill=color, width=line_width)


_DRAW_FUNCS = {
	"Point": _draw_point,
	"Arrow": _draw_arrow,
	"Text": _draw_text,
	"Freehand": _draw_freehand,
}


def get_annotated_image_bytes(report):
	"""Return the report's opg_image with all its annotations baked in as
	actual pixels, so both the PDF print format and the docx export can embed
	one flattened image instead of relying on an HTML/SVG overlay that
	wkhtmltopdf has no reliable way to align against a static render.

	Returns None if there's no image at all. Returns the original bytes
	unchanged if there's an image but no annotations.
	"""
	if not report.opg_image:
		return None

	_, content = get_file(report.opg_image)

	if not report.annotations:
		return content

	image = Image.open(io.BytesIO(content)).convert("RGB")
	draw = ImageDraw.Draw(image)
	width, height = image.size

	for ann in report.annotations:
		draw_func = _DRAW_FUNCS.get(ann.annotation_type)
		if draw_func:
			draw_func(draw, ann, width, height)

	buffer = io.BytesIO()
	image.save(buffer, format="JPEG", quality=90)
	return buffer.getvalue()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.tests.test_image_utils`

Expected: `OK` with 3 tests run, 0 failures.

- [ ] **Step 6: Commit**

```bash
cd /workspace/development/frappe-bench/apps/dental_opg
git add dental_opg/dental_opg_reporting/image_utils.py dental_opg/tests/test_image_utils.py pyproject.toml
git commit -m "Add image_utils.get_annotated_image_bytes to bake annotations into image pixels"
```

---

### Task 4: Wire annotation baking into the print format and docx export

**Files:**
- Modify: `apps/dental_opg/dental_opg/dental_opg_reporting/doctype/opg_report/opg_report.py`
- Modify: `apps/dental_opg/dental_opg/fixtures/print_format.json`
- Modify: `apps/dental_opg/dental_opg/dental_opg_reporting/docx_export.py`

**Interfaces:**
- Consumes: `get_annotated_image_bytes(report)` from Task 3.
- Produces: `get_annotated_report_image(name: str)` - a new whitelisted GET endpoint (module-level, doctype-level convention, same as `export_report_docx`) returning the annotated image as a binary response; print format's `<img>` now points at it; docx export's image insertion uses the same function instead of reading the raw file directly.

- [ ] **Step 1: Add the image endpoint**

Modify `apps/dental_opg/dental_opg/dental_opg_reporting/doctype/opg_report/opg_report.py`. Add this at the end of the file (module level, after `export_report_docx`):

```python


@frappe.whitelist(methods=["GET"])
def get_annotated_report_image(name: str):
	from dental_opg.dental_opg_reporting.image_utils import get_annotated_image_bytes

	report = frappe.get_doc("OPG Report", name)
	report.check_permission("read")

	content = get_annotated_image_bytes(report)
	if content is None:
		frappe.throw(frappe._("Report {0} has no OPG image").format(name), frappe.DoesNotExistError)

	frappe.local.response.filename = f"{report.name}.jpg"
	frappe.local.response.filecontent = content
	frappe.local.response.content_type = "image/jpeg"
	frappe.local.response.type = "binary"
```

- [ ] **Step 2: Point the print format's image at the new endpoint**

Modify `apps/dental_opg/dental_opg/fixtures/print_format.json`. Inside the `html` field's JSON string, find this exact substring:

```
<img src=\"{{ doc.opg_image }}\" style=\"max-width:100%; max-height:280px;\" />
```

Replace it with:

```
<img src=\"/api/method/dental_opg.dental_opg_reporting.doctype.opg_report.opg_report.get_annotated_report_image?name={{ doc.name }}\" style=\"max-width:100%; max-height:280px;\" />
```

(This is a single find-and-replace inside the fixture's `html` JSON string value - the surrounding `{% if doc.opg_image %}` conditional and everything else in the file stays untouched.)

- [ ] **Step 3: Update docx export's image insertion**

Modify `apps/dental_opg/dental_opg/dental_opg_reporting/docx_export.py`. Current imports (top of file):

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
```

Remove the `from frappe.utils.file_manager import get_file` line and add the new import, so it reads:

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

from dental_opg.dental_opg_reporting.image_utils import get_annotated_image_bytes
from dental_opg.dental_opg_reporting.report_builder import build_report_sections
```

Current `_insert_image`:

```python
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
```

Replace with:

```python
def _insert_image(doc, report):
	marker = next((p for p in doc.paragraphs if p.text == "{{OPG_IMAGE}}"), None)
	if marker is None:
		return
	marker.text = ""
	content = get_annotated_image_bytes(report)
	if content is None:
		return
	marker.alignment = 1  # center
	run = marker.add_run()
	run.add_picture(io.BytesIO(content), width=Inches(6))
```

- [ ] **Step 4: Migrate and verify existing docx export tests still pass**

Run: `bench --site dental_opg-test.localhost migrate`

Expected: no traceback.

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.tests.test_docx_export`

Expected: `OK`, all 4 existing tests still passing (none of them set annotations, so `get_annotated_image_bytes` should behave as a passthrough for all of them - confirming the swap didn't change existing behavior for the no-annotation case).

- [ ] **Step 5: Manual verification on `dev.localhost` - annotations actually appear**

```bash
cd /tmp
curl -s -c cookies_annot.txt -X POST "http://dev.localhost:8000/api/method/login" -d "usr=Administrator&pwd=admin" -o /dev/null -w "login: %{http_code}\n"
TOKEN=$(curl -s -b cookies_annot.txt "http://dev.localhost:8000/dental_opg" | grep -oP 'window\["csrf_token"\] = "\K[^"]+')

CREATE=$(curl -s -b cookies_annot.txt -X POST "http://dev.localhost:8000/api/method/dental_opg.api.create_report" \
  -H "Content-Type: application/json" -H "X-Frappe-CSRF-Token: $TOKEN" -H "Referer: http://dev.localhost:8000/dental_opg/new" \
  -d '{"patient_name":"Annotation Verify","age":30,"sex":"Male","registration_no":"REG-ANNOT-01"}')
REPORT=$(echo "$CREATE" | python3 -c "import json,sys; print(json.load(sys.stdin)['message']['report'])")

curl -s -b cookies_annot.txt -X POST "http://dev.localhost:8000/api/method/upload_file" \
  -H "X-Frappe-CSRF-Token: $TOKEN" -H "Referer: http://dev.localhost:8000/dental_opg/new" \
  -F "file=@/tmp/docx_media/word/media/image1.jpeg;filename=opg_annot_test.jpg;type=image/jpeg" \
  -F "doctype=OPG Report" -F "docname=$REPORT" -F "fieldname=opg_image" -F "is_private=0" -o /dev/null -w "upload: %{http_code}\n"

curl -s -b cookies_annot.txt -X POST "http://dev.localhost:8000/api/method/frappe.client.set_value" \
  -H "Content-Type: application/json" -H "X-Frappe-CSRF-Token: $TOKEN" -H "Referer: http://dev.localhost:8000/dental_opg/new" \
  -d "{\"doctype\":\"OPG Report\",\"name\":\"$REPORT\",\"fieldname\":\"opg_image\",\"value\":\"/files/opg_annot_test.jpg\"}" -o /dev/null -w "set_value: %{http_code}\n"

curl -s -b cookies_annot.txt -X POST "http://dev.localhost:8000/api/method/run_doc_method" \
  -H "Content-Type: application/json" -H "X-Frappe-CSRF-Token: $TOKEN" -H "Referer: http://dev.localhost:8000/dental_opg/new" \
  -d "{\"dt\":\"OPG Report\",\"dn\":\"$REPORT\",\"method\":\"save_annotations\",\"args\":{\"annotations\":[{\"annotation_type\":\"Point\",\"x\":0.5,\"y\":0.5,\"color\":\"#ff0000\"},{\"annotation_type\":\"Text\",\"x\":0.6,\"y\":0.3,\"label_text\":\"Impacted\",\"color\":\"#0000ff\"}]}}" -o /dev/null -w "save_annotations: %{http_code}\n"

curl -s -b cookies_annot.txt "http://dev.localhost:8000/api/method/dental_opg.dental_opg_reporting.doctype.opg_report.opg_report.get_annotated_report_image?name=$REPORT" \
  -o /tmp/annotated_endpoint_check.jpg -w "image endpoint: %{http_code}\n"
file /tmp/annotated_endpoint_check.jpg

echo "$REPORT" > /tmp/annot_report.txt
```

Expected: `image endpoint: 200`, and `file` reports a valid JPEG. Read the resulting `/tmp/annotated_endpoint_check.jpg` (e.g. via the Read tool, since it's an image) to visually confirm the red point and blue "Impacted" text label actually appear on the X-ray - do not just trust the HTTP status code.

- [ ] **Step 6: Clean up verification data**

```bash
cd /workspace/development/frappe-bench
REPORT=$(cat /tmp/annot_report.txt)
bench --site dev.localhost mariadb -e "select patient from \`tabOPG Report\` where name='$REPORT';"
```

Use the returned patient name to delete both via `bench --site dev.localhost execute frappe.delete_doc --kwargs "{'doctype': 'OPG Report', 'name': '$REPORT', 'force': 1}"` and the equivalent for the patient.

- [ ] **Step 7: Commit**

```bash
cd /workspace/development/frappe-bench/apps/dental_opg
git add dental_opg/dental_opg_reporting/doctype/opg_report/opg_report.py \
        dental_opg/fixtures/print_format.json \
        dental_opg/dental_opg_reporting/docx_export.py
git commit -m "Bake annotations into the image shown in the print format and docx export"
```

---

### Task 5: Frontend - `ToothChart.vue` rewrite, `api.py` fields, editable report text

**Files:**
- Modify: `apps/dental_opg/dental_opg/api.py`
- Modify: `apps/dental_opg/frontend/src/components/ToothChart.vue` (full replacement)
- Modify: `apps/dental_opg/frontend/src/pages/ReportEditor.vue`

**Interfaces:**
- Consumes: `OPG Tooth Finding` now has `description_template` (Task 1); `get_reporting_setup_data`'s `tooth_findings` list needs it too, for `ToothChart.vue`'s dropdown to pre-fill descriptions.
- Produces: `ToothChart.vue` emits `update:tooth-findings` with rows shaped `{tooth_number, arch, finding, finding_name, description}` (no more `is_custom`/`custom_text`); multi-tooth-select mode toggle.

- [ ] **Step 1: Update `get_reporting_setup_data`'s tooth-findings fields**

Modify `apps/dental_opg/dental_opg/api.py`. Find:

```python
	tooth_findings = frappe.get_all(
		"OPG Tooth Finding",
		filters={"active": 1},
		fields=["name", "finding_name"],
		order_by="finding_name asc",
	)
```

Replace with:

```python
	tooth_findings = frappe.get_all(
		"OPG Tooth Finding",
		filters={"active": 1},
		fields=["name", "finding_name", "description_template"],
		order_by="finding_name asc",
	)
```

- [ ] **Step 2: Replace `ToothChart.vue`**

Replace the full contents of `apps/dental_opg/frontend/src/components/ToothChart.vue` with:

```vue
<template>
	<div>
		<div class="mb-2 flex items-center justify-between">
			<span class="text-xs text-gray-500">{{ multiSelect ? 'Click teeth to select multiple' : 'Click a tooth' }}</span>
			<button
				class="rounded border px-2 py-1 text-xs"
				:class="multiSelect ? 'border-gray-900 bg-gray-900 text-white' : 'border-gray-300'"
				@click="toggleMultiSelect"
			>
				{{ multiSelect ? 'Multi-select on' : 'Select multiple teeth' }}
			</button>
		</div>

		<div class="flex flex-wrap justify-center gap-1">
			<button
				v-for="tooth in teeth"
				:key="tooth"
				class="relative h-9 w-9 rounded border text-xs font-medium hover:bg-gray-100"
				:class="[
					isHighlighted(tooth) ? 'border-gray-900 ring-1 ring-gray-900' : 'border-gray-300',
					countFor(tooth) ? 'bg-red-50 text-red-700 border-red-300' : '',
				]"
				@click="onToothClick(tooth)"
			>
				{{ tooth }}
				<span
					v-if="countFor(tooth)"
					class="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-600 text-[9px] text-white"
				>
					{{ countFor(tooth) }}
				</span>
			</button>
		</div>

		<div v-if="panelTeeth.length" class="mt-3 rounded border bg-gray-50 p-3">
			<div class="mb-2 text-sm font-medium">
				{{ panelTeeth.length > 1 ? `Teeth ${panelTeeth.join(', ')} findings` : `Tooth ${panelTeeth[0]} findings` }}
			</div>

			<div v-if="!multiSelect" class="mb-3 space-y-2">
				<div v-for="(row, idx) in singleToothRows" :key="idx" class="rounded border bg-white p-2 text-xs">
					<div class="mb-1 flex items-center justify-between">
						<span class="font-medium">{{ row.finding_name }}</span>
						<button class="text-red-600" @click="removeRow(row)">remove</button>
					</div>
					<textarea
						v-model="row.description"
						rows="2"
						class="w-full rounded border px-2 py-1 text-xs"
						@input="emitUpdate"
					></textarea>
				</div>
			</div>

			<div class="mb-2 flex flex-wrap gap-1.5">
				<button
					v-for="mf in toothFindingsMaster"
					:key="mf.name"
					class="rounded-full border border-gray-300 px-2.5 py-1 text-xs hover:bg-gray-100"
					@click="addFinding(mf)"
				>
					+ {{ mf.finding_name }}
				</button>
			</div>

			<div class="flex gap-2">
				<input
					v-model="customText"
					placeholder="Add custom finding"
					class="flex-1 rounded border px-2 py-1 text-xs"
					@keyup.enter="addCustom"
				/>
				<button class="rounded bg-gray-900 px-2 py-1 text-xs text-white" @click="addCustom">Add</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
	arch: { type: String, required: true }, // 'Maxillary' | 'Mandibular'
	toothFindings: { type: Array, default: () => [] },
	toothFindingsMaster: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:toothFindings'])

const UPPER = ['18', '17', '16', '15', '14', '13', '12', '11', '21', '22', '23', '24', '25', '26', '27', '28']
const LOWER = ['48', '47', '46', '45', '44', '43', '42', '41', '31', '32', '33', '34', '35', '36', '37', '38']
const teeth = computed(() => (props.arch === 'Maxillary' ? UPPER : LOWER))

const multiSelect = ref(false)
const selectedTooth = ref(null)
const selectedTeeth = ref([])
const customText = ref('')

const panelTeeth = computed(() => (multiSelect.value ? selectedTeeth.value : selectedTooth.value ? [selectedTooth.value] : []))

function toggleMultiSelect() {
	multiSelect.value = !multiSelect.value
	selectedTeeth.value = []
	selectedTooth.value = null
}

function onToothClick(tooth) {
	if (multiSelect.value) {
		const i = selectedTeeth.value.indexOf(tooth)
		if (i === -1) selectedTeeth.value = [...selectedTeeth.value, tooth]
		else selectedTeeth.value = selectedTeeth.value.filter((t) => t !== tooth)
	} else {
		selectedTooth.value = selectedTooth.value === tooth ? null : tooth
	}
}

function isHighlighted(tooth) {
	return multiSelect.value ? selectedTeeth.value.includes(tooth) : selectedTooth.value === tooth
}

function rowsFor(tooth) {
	return props.toothFindings.filter((r) => r.tooth_number === tooth)
}
function countFor(tooth) {
	return rowsFor(tooth).length
}

const singleToothRows = computed(() => (selectedTooth.value ? rowsFor(selectedTooth.value) : []))

function emitUpdate() {
	emit('update:toothFindings', [...props.toothFindings])
}

function addFinding(masterFinding) {
	const newRows = panelTeeth.value.map((tooth) => ({
		tooth_number: tooth,
		arch: props.arch,
		finding: masterFinding.name,
		finding_name: masterFinding.finding_name,
		description: masterFinding.description_template,
	}))
	emit('update:toothFindings', [...props.toothFindings, ...newRows])
}

function addCustom() {
	if (!customText.value.trim() || !panelTeeth.value.length) return
	const newRows = panelTeeth.value.map((tooth) => ({
		tooth_number: tooth,
		arch: props.arch,
		finding: null,
		finding_name: customText.value.trim(),
		description: customText.value.trim(),
	}))
	emit('update:toothFindings', [...props.toothFindings, ...newRows])
	customText.value = ''
}

function removeRow(row) {
	emit(
		'update:toothFindings',
		props.toothFindings.filter((r) => r !== row),
	)
}
</script>
```

- [ ] **Step 3: Make the generated report text editable**

Modify `apps/dental_opg/frontend/src/pages/ReportEditor.vue`. Find:

```html
				<div v-if="report.generated_report_text" class="rounded border bg-white p-4">
					<h2 class="mb-2 text-sm font-semibold text-gray-800">Generated Report Text</h2>
					<pre class="whitespace-pre-wrap text-xs text-gray-700">{{ report.generated_report_text }}</pre>
				</div>
```

Replace with:

```html
				<div v-if="report.generated_report_text !== undefined" class="rounded border bg-white p-4">
					<h2 class="mb-2 text-sm font-semibold text-gray-800">Generated Report Text</h2>
					<textarea
						v-model="report.generated_report_text"
						rows="14"
						class="w-full rounded border px-2 py-1 font-mono text-xs text-gray-700"
					></textarea>
				</div>
```

(The `v-if` condition changes from truthy-check to `!== undefined` so the box is present - and editable - even for a fresh report before "Generate Report" has ever been clicked, not just after there's already text in it.)

Find the `save()` function's `saveReportDetails` call:

```javascript
		await saveReportDetails(report.name, {
			report_date: report.report_date,
			referred_by: report.referred_by,
			clinical_diagnosis: report.clinical_diagnosis,
			status: report.status,
			reported_by: report.reported_by,
			verified_by: report.verified_by,
		})
```

Add `generated_report_text` to the field set:

```javascript
		await saveReportDetails(report.name, {
			report_date: report.report_date,
			referred_by: report.referred_by,
			clinical_diagnosis: report.clinical_diagnosis,
			status: report.status,
			reported_by: report.reported_by,
			verified_by: report.verified_by,
			generated_report_text: report.generated_report_text,
		})
```

- [ ] **Step 4: Rebuild and verify**

Run: `cd /workspace/development/frappe-bench/apps/dental_opg/frontend && yarn build`

Expected: `✓ built in <N>s`, no Vue compiler errors.

Run: `cd /workspace/development/frappe-bench && bench build --app dental_opg`

Expected: `✔ Application Assets Linked` and `DONE`.

- [ ] **Step 5: Full end-to-end verification via curl on `dev.localhost`**

```bash
cd /tmp
curl -s -c cookies_tf.txt -X POST "http://dev.localhost:8000/api/method/login" -d "usr=Administrator&pwd=admin" -o /dev/null -w "login: %{http_code}\n"
TOKEN=$(curl -s -b cookies_tf.txt "http://dev.localhost:8000/dental_opg" | grep -oP 'window\["csrf_token"\] = "\K[^"]+')

curl -s -b cookies_tf.txt "http://dev.localhost:8000/api/method/dental_opg.api.get_reporting_setup_data" | python3 -c "
import json, sys
d = json.load(sys.stdin)['message']
tf = d['tooth_findings']
print('tooth findings count:', len(tf))
assert len(tf) == 21, f'expected 21, got {len(tf)}'
assert 'description_template' in tf[0], 'description_template missing from setup data'
print('sample:', tf[0]['finding_name'], '->', tf[0]['description_template'][:50])
"

CREATE=$(curl -s -b cookies_tf.txt -X POST "http://dev.localhost:8000/api/method/dental_opg.api.create_report" \
  -H "Content-Type: application/json" -H "X-Frappe-CSRF-Token: $TOKEN" -H "Referer: http://dev.localhost:8000/dental_opg/new" \
  -d '{"patient_name":"Tooth Findings Verify","age":25,"sex":"Female","registration_no":"REG-TF-VERIFY-01"}')
REPORT=$(echo "$CREATE" | python3 -c "import json,sys; print(json.load(sys.stdin)['message']['report'])")
echo "report=$REPORT"

curl -s -b cookies_tf.txt -X POST "http://dev.localhost:8000/api/method/run_doc_method" \
  -H "Content-Type: application/json" -H "X-Frappe-CSRF-Token: $TOKEN" -H "Referer: http://dev.localhost:8000/dental_opg/new" \
  -d "{\"dt\":\"OPG Report\",\"dn\":\"$REPORT\",\"method\":\"save_findings\",\"args\":{\"section_findings\":[],\"tooth_findings\":[{\"tooth_number\":\"16\",\"arch\":\"Maxillary\",\"finding\":\"dental-caries\",\"finding_name\":\"Dental Caries\",\"description\":\"Coronally- test desc\"},{\"tooth_number\":\"17\",\"arch\":\"Maxillary\",\"finding\":\"dental-caries\",\"finding_name\":\"Dental Caries\",\"description\":\"Coronally- test desc\"}]}}" -o /dev/null -w "save_findings: %{http_code}\n"

curl -s -b cookies_tf.txt -X POST "http://dev.localhost:8000/api/method/run_doc_method" \
  -H "Content-Type: application/json" -H "X-Frappe-CSRF-Token: $TOKEN" -H "Referer: http://dev.localhost:8000/dental_opg/new" \
  -d "{\"dt\":\"OPG Report\",\"dn\":\"$REPORT\",\"method\":\"generate_report\",\"args\":{}}" | python3 -c "
import json, sys
text = json.load(sys.stdin)['message']
print(text)
assert 'irt 16, 17 - Coronally- test desc' in text, 'merged irt line missing'
assert 'Dental Caries' in text.split('RADIOLOGIC IMPRESSION:')[-1], 'Radiologic Impression summary missing'
print('CONTENT VERIFIED OK')
"

echo "$REPORT" > /tmp/tf_verify_report.txt
```

Expected: setup-data check prints `tooth findings count: 21` with no assertion error, and the generate_report output contains `CONTENT VERIFIED OK` on its own confirming both the merged line and the Radiologic Impression summary are present in the real generated text.

- [ ] **Step 6: Clean up verification data**

```bash
cd /workspace/development/frappe-bench
REPORT=$(cat /tmp/tf_verify_report.txt)
bench --site dev.localhost mariadb -e "select patient from \`tabOPG Report\` where name='$REPORT';"
```

Use the returned patient name to delete both (same pattern as prior tasks).

- [ ] **Step 7: Commit**

```bash
cd /workspace/development/frappe-bench/apps/dental_opg
git add dental_opg/api.py frontend/src/components/ToothChart.vue frontend/src/pages/ReportEditor.vue \
        dental_opg/public/frontend dental_opg/www/dental_opg.html
git commit -m "Rewrite ToothChart with dropdown-add + multi-select, make report text editable"
```

---

### Task 6: Final migrate + comprehensive manual verification

**Files:** none (verification only)

- [ ] **Step 1: Migrate `dev.localhost`**

Run: `cd /workspace/development/frappe-bench && bench --site dev.localhost migrate`

Expected: no traceback.

- [ ] **Step 1b: Delete the 9 old finding master records on `dev.localhost` too**

Same reasoning as Task 1 Step 5 - fixture sync on this site also leaves the old 9 records orphaned:

```bash
cd /workspace/development/frappe-bench
for name in missing caries root-stump impacted restored fracture bone-loss periapical-radiolucency mobility; do
  bench --site dev.localhost execute frappe.delete_doc --kwargs "{'doctype': 'OPG Tooth Finding', 'name': '$name', 'force': 1}"
done
bench --site dev.localhost execute frappe.db.count --args "['OPG Tooth Finding']"
```

Expected: prints `21`.

- [ ] **Step 1c: Check for pre-existing reports using the old tooth-finding schema**

`dev.localhost` is the site a human has been actively testing against through this whole project - check whether any real `OPG Report` documents have `tooth_findings` rows predating this migration (they'd have used the now-removed `is_custom`/`custom_text` fields and be missing the new required `finding_name`/`description`):

```bash
bench --site dev.localhost mariadb -e "select parent, name, tooth_number, finding_name, description from \`tabOPG Tooth Finding Entry\`;"
```

If this returns any rows with `finding_name`/`description` as `NULL` or empty, **do not silently delete or backfill them** - report the exact `parent` (report name) and `tooth_number` values to the user and ask whether they want those specific rows cleaned up, backfilled with placeholder text, or left as-is (they'll just render as blank finding/description in the UI, which is a display quirk, not a crash). If the query returns no rows, no action needed.

- [ ] **Step 2: Run the full test suite one more time**

Run: `bench --site dental_opg-test.localhost run-tests --app dental_opg`

Expected: `OK`, all tests passing (this now includes the new `test_report_builder.py` and `test_image_utils.py` alongside every pre-existing test).

- [ ] **Step 3: Confirm the built frontend actually contains the new UI**

```bash
grep -c "Select multiple teeth" /workspace/development/frappe-bench/apps/dental_opg/dental_opg/public/frontend/assets/*.js
```

Expected: at least one match (guards against the exact "committed source but not the rebuilt bundle" mistake from the docx export feature's final review).

- [ ] **Step 4: Tell the user it's ready for manual browser testing**

Report to the user: open a report at `http://dev.localhost:8000/dental_opg/<report-name>`, click a tooth in either arch, confirm the finding chips + editable description box appear; try "Select multiple teeth", pick 2+ teeth, add one finding, confirm one entry per tooth was created; click Generate Report, confirm the `irt {tooth} - {description}` lines and the Radiologic Impression summary look right, and that the generated text box is now editable and its edits persist after Save; click Print and Export DOCX, confirm any annotations drawn on the image actually show up in both.
