# Rado-2 Feedback Round Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the 18 changes from the clinic's `Rado-2.xlsx` sheet and the revised tooth-finding list from `OPG COMMON FINDINGS (1).docx`.

**Architecture:** Backend changes are schema tweaks (5 DocType JSONs), fixture data, one patch, and logic in `report_builder.py`, `docx_export.py`, `image_utils.py`, `api.py`. Frontend (Vue 3 + Tailwind, built into `dental_opg/public/frontend`) gets a shared `FindingPicker` component, reworked `SectionCard` / `ToothChart`, new annotation tools in `ImageViewer`, and patient/signatory additions in `ReportEditor`.

**Tech Stack:** Frappe (Python, `IntegrationTestCase`), python-docx, Pillow, Vue 3, Tailwind, frappe-ui, Vite.

**Spec:** `docs/superpowers/specs/2026-10-13-rado-2-feedback-design.md`

## Global Constraints

- `bench` commands run from `/workspace/development/frappe-bench`. Test site: `dental_opg-test.localhost`. Dev site `dev.localhost` is human-active — only touch data you create, clean it up.
- After any DocType JSON / fixture change: bump that JSON's `"modified"` to `"2026-10-13 12:00:00.000000"` (or later) and run `bench --site dental_opg-test.localhost migrate`.
- Full test run: `bench --site dental_opg-test.localhost run-tests --app dental_opg`. Baseline before this plan: 31 tests, OK.
- No JS test runner exists. Frontend verification = `yarn build` succeeds + manual check in browser. Built assets (`dental_opg/public/frontend/**`, `dental_opg/www/dental_opg.html`) MUST be committed — a past release shipped source without the rebuilt bundle.
- Times New Roman, black text for every exported/printed character; letterhead header (logo + department title) untouched.
- Python indentation: tabs (match repo). Vue: tabs.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Work on branch `rado-2-feedback`, never on `main`.

## Review Focus

1. **Old reports with old data** — reports saved before this change (Data `finding_name`, no `edited_text`, templates with "irt tooth number") must still open, save, generate and export. Covered by: patch test (Task 2), builder test with empty `edited_text` (Task 3).
2. **Partial complement with no tooth number** — dentist picks "Partial complement…" but leaves tooth # empty: no dangling `PARTIALLY EDENTULOUS irt ` line. Test in Task 3.
3. **Section skipped in export** — when a whole section has no findings its heading is removed; no blank gap left behind. Test in Task 4 (`test_no_blank_paragraphs_after_findings_start`, uses only one section).
4. **Polyline/Curve double-click** — the two mousedowns preceding `dblclick` add duplicate vertices; must be de-duplicated, and fewer than 2 distinct points must not create an annotation. Manual check in Task 8, logic in `finishPath`.
5. **Deciduous tooth arch** — child teeth 51–85 must land in the right arch section in the generated report, not all in Mandibular. Test in Task 1.

---

## Task 0: Branch + commit spec and plan

- [ ] **Step 1:** 

```bash
cd /workspace/development/frappe-bench/apps/dental_opg
git checkout -b rado-2-feedback
git add docs/superpowers/specs/2026-10-13-rado-2-feedback-design.md docs/superpowers/plans/2026-10-13-rado-2-feedback.md
git commit -m "Add Rado-2 feedback design spec and implementation plan

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Do NOT commit `Rado-2.xlsx` or `OPG COMMON FINDINGS (1).docx` (client source files).

---

## Task 1: Schema changes + deciduous arch derivation

**Files:**
- Modify: `dental_opg/dental_opg_reporting/doctype/opg_tooth_finding/opg_tooth_finding.json` (`finding_name` → Small Text)
- Modify: `dental_opg/dental_opg_reporting/doctype/opg_tooth_finding_entry/opg_tooth_finding_entry.json` (`finding_name` → Small Text)
- Modify: `dental_opg/dental_opg_reporting/doctype/opg_standard_finding/opg_standard_finding.json` (+ `impression_label`)
- Modify: `dental_opg/dental_opg_reporting/doctype/opg_report_finding/opg_report_finding.json` (+ `edited_text`)
- Modify: `dental_opg/dental_opg_reporting/doctype/opg_annotation/opg_annotation.json` (+ 3 options)
- Modify: `dental_opg/dental_opg_reporting/doctype/opg_report/opg_report.py` (`validate`)
- Test: `dental_opg/dental_opg_reporting/doctype/opg_report/test_opg_report.py`

**Interfaces:**
- Produces: fields `OPG Standard Finding.impression_label` (Data), `OPG Report Finding.edited_text` (Small Text); annotation types `Polyline`, `Landmark`, `Curve`; `finding_name` has no 140-char cap.

- [ ] **Step 1: Write failing tests** — append to the `TestOPGReport` class in `test_opg_report.py` (its `setUp` already creates `self.patient` and `self.report`):

```python
	def test_validate_assigns_arch_for_deciduous_teeth(self):
		self.report.save_findings(
			section_findings=[],
			tooth_findings=[
				{"tooth_number": tooth, "finding_name": "Test", "description": "Test"}
				for tooth in ("55", "65", "75", "85")
			],
		)
		self.report.reload()
		arch_by_tooth = {row.tooth_number: row.arch for row in self.report.tooth_findings}
		self.assertEqual(
			arch_by_tooth,
			{"55": "Maxillary", "65": "Maxillary", "75": "Mandibular", "85": "Mandibular"},
		)

	def test_tooth_finding_name_longer_than_140_characters_saves(self):
		long_name = "Custom finding " + "x" * 300
		self.report.save_findings(
			section_findings=[],
			tooth_findings=[{"tooth_number": "16", "finding_name": long_name, "description": long_name}],
		)
		self.report.reload()
		self.assertEqual(self.report.tooth_findings[0].finding_name, long_name)

	def test_section_finding_edited_text_is_saved(self):
		self.report.save_findings(
			section_findings=[
				{"section": "Condylar Morphology", "finding": "csf-normal", "edited_text": "Edited for patient"}
			],
			tooth_findings=[],
		)
		self.report.reload()
		self.assertEqual(self.report.section_findings[0].edited_text, "Edited for patient")
```

- [ ] **Step 2: Run, verify fail**

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.dental_opg_reporting.doctype.opg_report.test_opg_report`
Expected: 3 new FAILs (arch for 55/65 is Mandibular; long name raises `CharacterLengthExceededError`; `edited_text` missing attribute).

- [ ] **Step 3: Edit DocType JSONs** — use a script so `modified` gets bumped consistently:

```bash
cd /workspace/development/frappe-bench/apps/dental_opg
../../env/bin/python -I - <<'EOF'
import json
from pathlib import Path

BASE = Path("dental_opg/dental_opg_reporting/doctype")
MODIFIED = "2026-10-13 12:00:00.000000"

def edit(doctype_dir, fn):
	path = BASE / doctype_dir / f"{doctype_dir}.json"
	data = json.loads(path.read_text())
	fn(data)
	data["modified"] = MODIFIED
	path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")

def field(data, name):
	return next(f for f in data["fields"] if f["fieldname"] == name)

def insert_after(data, after, new_field):
	data["field_order"].insert(data["field_order"].index(after) + 1, new_field["fieldname"])
	idx = next(i for i, f in enumerate(data["fields"]) if f["fieldname"] == after)
	data["fields"].insert(idx + 1, new_field)

def small_text_finding_name(data):
	field(data, "finding_name")["fieldtype"] = "Small Text"

edit("opg_tooth_finding", small_text_finding_name)
edit("opg_tooth_finding_entry", small_text_finding_name)
edit("opg_standard_finding", lambda d: insert_after(d, "allow_level", {
	"fieldname": "impression_label",
	"fieldtype": "Data",
	"label": "Impression Label",
	"description": "When set and the row has tooth numbers, adds '<label> irt <teeth>' to Radiologic Impression",
}))
edit("opg_report_finding", lambda d: insert_after(d, "custom_text", {
	"fieldname": "edited_text",
	"fieldtype": "Small Text",
	"label": "Edited Text",
	"description": "Per-patient override of the rendered finding text",
}))
def add_annotation_types(data):
	f = field(data, "annotation_type")
	f["options"] = f["options"].rstrip("\n") + "\nPolyline\nLandmark\nCurve"
edit("opg_annotation", add_annotation_types)
EOF
git diff --stat
```

- [ ] **Step 4: Update `validate` in `opg_report.py`:**

```python
MAXILLARY_QUADRANTS = ("1", "2", "5", "6")


class OPGReport(Document):
	def validate(self):
		for row in self.tooth_findings:
			if not row.arch:
				quadrant = (row.tooth_number or "").strip()[:1]
				row.arch = "Maxillary" if quadrant in MAXILLARY_QUADRANTS else "Mandibular"
```

(`MAXILLARY_QUADRANTS` goes at module level above the class; FDI quadrants 1, 2 permanent upper, 5, 6 deciduous upper.)

- [ ] **Step 5: Migrate + run tests**

```bash
cd /workspace/development/frappe-bench
bench --site dental_opg-test.localhost migrate
bench --site dental_opg-test.localhost run-tests --app dental_opg
```
Expected: all pass (31 + 3 = 34).

- [ ] **Step 6: Commit**

```bash
cd apps/dental_opg
git add dental_opg/dental_opg_reporting/doctype
git commit -m "Lift 140-char limit on tooth finding names, add edited_text/impression_label, new annotation types, deciduous arch mapping

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 2: Fixtures (revised findings) + irt template patch

**Files:**
- Modify: `dental_opg/fixtures/opg_tooth_finding.json` (regenerated, 41 records)
- Modify: `dental_opg/fixtures/opg_standard_finding.json`
- Create: `dental_opg/patches/fix_irt_tooth_number_templates.py`
- Modify: `dental_opg/patches.txt`
- Test: `dental_opg/tests/test_patches.py` (create)

**Interfaces:**
- Consumes: `impression_label` field (Task 1).
- Produces: standard findings `ri-chronic-generalized-periodontitis`, `ri-localized-periodontitis`; `ma-partial` / `mda-partial` with `impression_label = "PARTIALLY EDENTULOUS"`; tooth-finding descriptions with `\n` between Coronally / Radicularly / Periapically; literal `(tooth number)` placeholder in Partially Edentulous + Periodontitis.

- [ ] **Step 1: Write failing patch test** — `dental_opg/tests/test_patches.py`:

```python
import frappe
from frappe.tests import IntegrationTestCase

from dental_opg.patches import fix_irt_tooth_number_templates


class TestFixIrtToothNumberTemplates(IntegrationTestCase):
	def test_strips_literal_tooth_number_words(self):
		finding = frappe.get_doc(
			doctype="OPG Standard Finding",
			section_name="Maxillary Arch",
			finding_label="Old style template",
			finding_template="Missing irt tooth number {tooth_number}",
			allow_tooth=1,
			active=1,
		).insert()

		fix_irt_tooth_number_templates.execute()

		self.assertEqual(
			frappe.db.get_value("OPG Standard Finding", finding.name, "finding_template"),
			"Missing irt {tooth_number}",
		)

	def test_leaves_other_templates_untouched(self):
		finding = frappe.get_doc(
			doctype="OPG Standard Finding",
			section_name="Maxillary Arch",
			finding_label="Unrelated",
			finding_template="Crest at {level} irt {tooth_number}",
			active=1,
		).insert()

		fix_irt_tooth_number_templates.execute()

		self.assertEqual(
			frappe.db.get_value("OPG Standard Finding", finding.name, "finding_template"),
			"Crest at {level} irt {tooth_number}",
		)
```

- [ ] **Step 2: Run, verify fail**

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.tests.test_patches`
Expected: FAIL / ImportError `fix_irt_tooth_number_templates`.

- [ ] **Step 3: Write patch** — `dental_opg/patches/fix_irt_tooth_number_templates.py`:

```python
"""Standard finding templates used to read "... irt tooth number {tooth_number}",
so the export said "irt tooth number 16" and dentists deleted "tooth number"
by hand after every export. The fixture is fixed directly; this patch fixes
any non-fixture copies (e.g. promoted custom findings) already in the DB."""

import frappe

OLD = "irt tooth number {tooth_number}"
NEW = "irt {tooth_number}"


def execute():
	rows = frappe.get_all(
		"OPG Standard Finding",
		filters={"finding_template": ["like", "%irt tooth number%"]},
		fields=["name", "finding_template"],
	)
	for row in rows:
		if OLD in (row.finding_template or ""):
			frappe.db.set_value(
				"OPG Standard Finding",
				row.name,
				"finding_template",
				row.finding_template.replace(OLD, NEW),
				update_modified=False,
			)
```

Append to `dental_opg/patches.txt` under `[post_model_sync]`:

```
dental_opg.patches.fix_irt_tooth_number_templates
```

- [ ] **Step 4: Run patch test, verify pass**

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.tests.test_patches`
Expected: 2 PASS.

- [ ] **Step 5: Regenerate tooth-finding fixture.** Save this one-off generator to the session scratchpad (not the repo) and run it from the app dir. Text is the Word doc with typos fixed (Stapels→Staples, Decidouos→Deciduous, inscisal→incisal, adjascent→adjacent, it's→its), hyphen spacing normalized to `Coronally - `, duplicate PARTIALLY EDENTULOUS / PERIODONTITIS collapsed. Slugs of the 21 existing findings are unchanged.

```python
import json
import sys

CN = "Coronally - "
RN = "Radicularly - "
PN = "Periapically - "
NONE = "no changes appreciated"
CARIES_PULP = "an ill-defined radiolucency involving enamel dentin and approximating pulp on the occlusal aspect"
ENDO_ROOT = "homogenous thin linear radiopacity noted involving the root canal s/o endodontic restorative material"


def three(coronal, radicular=NONE, periapical=NONE):
	return f"{CN}{coronal}\n{RN}{radicular}\n{PN}{periapical}"


FINDINGS = [
	("dental-caries", "Dental Caries", three("an ill-defined radiolucency involving enamel and dentin on the occlusal aspect")),
	("deep-dentinal-caries", "Deep Dentinal Caries", three("an ill-defined radiolucency involving enamel and dentin and approximating pulp on the occlusal aspect")),
	("dental-caries-involving-pulp", "Dental Caries Involving Pulp", three(CARIES_PULP)),
	("secondary-caries", "Secondary Caries", three("a well-defined radiopacity noted s/o restorative material beneath which ill-defined radiolucency approximating pulp")),
	("periapical-abscess", "Periapical Abscess", three(CARIES_PULP, periapical="loss of lamina dura with ill-defined hazy radiolucency noted")),
	("chronic-apical-periodontitis", "Chronic Apical Periodontitis", three(CARIES_PULP, periapical="widening of pdl space noted")),
	("periapical-granuloma", "Periapical Granuloma", three(CARIES_PULP + " noted", periapical="loss of lamina dura with well-defined hazy radiolucency noted")),
	("periapical-cyst", "Periapical Cyst", three(CARIES_PULP + " noted", periapical="loss of lamina dura with well-defined radiolucency with corticated border noted")),
	("caries-involving-pulp-with-periapical-rarefying-osteitis", "Caries Involving Pulp With Periapical Rarefying Osteitis", three(CARIES_PULP + " noted", periapical="loss of lamina dura with well-defined hazy radiolucency noted")),
	("periodontal-abscess", "Periodontal Abscess", three(NONE, radicular="widening of pdl space", periapical="loss of lamina dura with ill-defined hazy radiolucency that is extending till the alveolar ridge")),
	("grossly-decayed", "Grossly Decayed", three("an ill-defined radiolucency involving enamel dentin and approximating pulp with partial loss of crown structure")),
	("root-stumps", "Root Stumps", three("complete loss of crown structure")),
	("infected-root-stumps", "Infected Root Stumps", three("complete loss of crown structure", periapical="loss of lamina dura with ill-defined hazy radiolucency")),
	("root-caries", "Root Caries", three(CARIES_PULP, radicular="ill-defined radiolucency noted on the cervical third approximating canals")),
	("proximal-caries", "Proximal Caries", three("an ill-defined radiolucency involving enamel and dentin on the mesial / distal aspect")),
	("incompletely-endodontically-treated-tooth", "Incompletely Endodontically Treated Tooth", three("a well-defined radiopacity noted along with partial loss of crown structure", radicular=ENDO_ROOT)),
	("restoration", "Restoration", three("a well-defined radiopacity involving enamel noted s/o restorative material")),
	("prosthetic-crown", "Prosthetic Crown", three("a well-defined radiopacity noted s/o prosthetic crown")),
	("endodontically-treated-tooth", "Endodontically Treated Tooth", three("a well-defined radiopacity noted s/o prosthesis", radicular=ENDO_ROOT)),
	("incompletely-endodontically-treated-tooth-with-rarefying-osteitis", "Incompletely Endodontically Treated Tooth With Rarefying Osteitis", three(
		"a well-defined radiopacity noted along with partial loss of crown structure",
		radicular="homogenous thin linear radiopacity which is 3-4mm short of apex involving the root canal s/o endodontic restorative material",
		periapical="ill-defined hazy radiolucency with loss of lamina dura noted",
	)),
	("mesioangular-impaction", "Mesioangular Impaction", "A dense radiopaque structure with density and morphology similar to that of a tooth with its long axis mesially inclined to that of adjacent tooth. The mesial portion of crown is at the level of cervical third of adjacent tooth. The root formation is incomplete. The apical third of roots are in close approximation to inferior alveolar nerve canal suggestive of mesioangular impaction."),
	("distoangular-impaction", "Distoangular Impaction", "A dense radiopaque structure with density and morphology similar to that of a tooth noted, the crown at the level of cervical third with its long axis distally oriented to that of adjacent tooth, root formation is incomplete, suggestive of distoangular impaction."),
	("horizontal-impaction", "Horizontal Impaction", "A dense radiopaque structure with density and morphology similar to that of a tooth with its long axis perpendicular to that of adjacent tooth. The tooth is embedded inside the bone except the distal cusp which is at the level of occlusal third of adjacent tooth. The root formation is incomplete. The follicular space is increased. The tooth is in close approximation to inferior alveolar nerve canal suggestive of horizontal impaction."),
	("vertical-impaction", "Vertical Impaction", "A dense radiopaque structure with density and morphology similar to that of a tooth with its long axis parallel to that of adjacent tooth noted. The crown is embedded inside the bone and is at the level of cervical third of adjacent tooth. The root formation is complete. The follicular space is increased. The apical third of roots are in close approximation to inferior alveolar nerve canal suggestive of vertical impaction."),
	("partially-edentulous", "Partially Edentulous", "Partial complement set of permanent dentition noted, with missing wrt (tooth number)"),
	("periodontitis", "Periodontitis", "The crest of the alveolar ridge is at the level of the middle third of the roots of all the teeth except wrt (tooth number), which is at the apical third of the root"),
	("generalised-attrition", "Generalised Attrition", "Irt all teeth - coronally - flattening of incisal edge / cusps involving enamel and dentin noted s/o attrition"),
	("attrition", "Attrition", "Coronally - flattening of incisal edge / cusps involving enamel and dentin noted s/o attrition"),
	("idiopathic-osteosclerosis", "Idiopathic Osteosclerosis", "Ill-defined hazy radiopacity noted between the apical region of 11 and 12 s/o idiopathic osteosclerosis."),
	("soft-tissue-calcification", "Soft Tissue Calcification", "Wrt laryngeal cartilage region below the level of hyoid bone a discrete radiopacity and a linear radiopacity noted s/o soft tissue calcification."),
	("retained-root-stump", "Retained Root Stump", "A root fragment is noted within the alveolar bone with complete loss of the coronal tooth structure, suggestive of a retained root stump. No associated periapical pathology is evident."),
	("tonsillolith", "Tonsillolith", "Well-defined, irregular/ovoid radiopaque foci are noted superimposed over the region of the mandibular ramus, suggestive of tonsilloliths."),
	("sialolith", "Sialolith", "A well-defined radiopaque focus is noted in the region of the floor of the mouth, possibly representing a sialolith. Correlation with occlusal radiography/ultrasonography may be considered."),
	("calcified-lymph-node", "Calcified Lymph Node", "Irregular, lobulated radiopaque calcified foci are noted inferior to the angle of the mandible, suggestive of calcified lymph nodes."),
	("fixed-prostheses", "Fixed Prostheses", "A well-defined radiopaque structure extending from the coronal portion of – to – and covering the entire crown s/o fixed prostheses"),
	("surgical-staples", "Surgical Staples", "Well-defined, discrete multiple radiopacities noted on the angle of the mandible region s/o surgical staples"),
	("surgical-plate", "Surgical Plate", "A well-defined linear heterogenous series of evenly spaced round radiopaque rings that forms a chain like structure extending from --- with radiopaque cylindrical structures extending from the plate into bone s/o surgical fixation plate with screws"),
	("ryles-tube", "Ryle's Tube", "A well-defined radiopaque tubular structure extending along the maxillofacial region s/o Ryle's tube"),
	("supernumerary-tooth", "Supernumerary Tooth", "An additional tooth-like radiopaque structure is noted in the ---- in relation to ______."),
	("retained-deciduous-tooth", "Retained Deciduous Tooth", "Well-defined heterogenous radiopacity with density and morphology similar to that of a tooth and comparatively smaller than the permanent adjacent tooth s/o retained deciduous tooth"),
	("condensing-osteitis", "Condensing Osteitis", three(
		"ill-defined radiolucency involving enamel dentin and approximating pulp",
		radicular="no significant changes appreciated",
		periapical="ill-defined radiolucency with loss of lamina dura followed by a radiopacity suggestive of condensing osteitis",
	)),
]

assert len(FINDINGS) == 41
assert len({slug for slug, _, _ in FINDINGS}) == 41

records = [
	{"doctype": "OPG Tooth Finding", "name": slug, "finding_name": name, "description_template": text, "active": 1}
	for slug, name, text in FINDINGS
]
with open(sys.argv[1], "w") as f:
	json.dump(records, f, indent=4, ensure_ascii=False)
	f.write("\n")
```

Run: `../../env/bin/python -I <scratchpad>/gen_tooth_fixture.py dental_opg/fixtures/opg_tooth_finding.json`
Then check: `git diff --stat dental_opg/fixtures/opg_tooth_finding.json` and confirm all 21 old slugs still present: `grep -c '"name"' dental_opg/fixtures/opg_tooth_finding.json` → 41.

- [ ] **Step 6: Update standard-finding fixture** (script, same style):

```bash
../../env/bin/python -I - <<'EOF'
import json
path = "dental_opg/fixtures/opg_standard_finding.json"
data = json.load(open(path))
by_name = {r["name"]: r for r in data}
for r in data:
	r["finding_template"] = r["finding_template"].replace("irt tooth number {tooth_number}", "irt {tooth_number}")
for name in ("ma-partial", "mda-partial"):
	by_name[name]["impression_label"] = "PARTIALLY EDENTULOUS"
data += [
	{
		"doctype": "OPG Standard Finding",
		"name": "ri-chronic-generalized-periodontitis",
		"section_name": "Radiologic Impression",
		"finding_label": "Chronic generalized periodontitis",
		"finding_template": "Chronic generalized periodontitis",
		"allow_side": 0, "allow_tooth": 0, "allow_level": 0, "active": 1,
	},
	{
		"doctype": "OPG Standard Finding",
		"name": "ri-localized-periodontitis",
		"section_name": "Radiologic Impression",
		"finding_label": "Localized periodontitis",
		"finding_template": "Localized periodontitis irt {tooth_number}",
		"allow_side": 0, "allow_tooth": 1, "allow_level": 0, "active": 1,
	},
]
json.dump(data, open(path, "w"), indent=4, ensure_ascii=False)
open(path, "a").write("\n")
EOF
grep -c "irt tooth number" dental_opg/fixtures/opg_standard_finding.json   # expect 0
```

- [ ] **Step 7: Migrate + verify data + full tests**

```bash
cd /workspace/development/frappe-bench
bench --site dental_opg-test.localhost migrate
bench --site dental_opg-test.localhost execute frappe.db.count --args "['OPG Tooth Finding', {'active': 1}]"
bench --site dental_opg-test.localhost execute frappe.db.get_value --args "['OPG Standard Finding', 'ma-partial', 'impression_label']"
bench --site dental_opg-test.localhost run-tests --app dental_opg
```
Expected: count ≥ 41 (custom promoted findings may add more); `"PARTIALLY EDENTULOUS"`; all tests pass. If an existing test asserted old fixture text (e.g. "mesial aspect"), update the assertion to the new fixture text — the fixture is the source of truth now.

- [ ] **Step 8: Commit**

```bash
cd apps/dental_opg
git add dental_opg/fixtures dental_opg/patches dental_opg/patches.txt dental_opg/tests/test_patches.py
git commit -m "Replace tooth findings with revised clinic list, fix 'irt tooth number' templates, add periodontitis impressions

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 3: Report builder — edited text, impression labels, setup data

**Files:**
- Modify: `dental_opg/dental_opg_reporting/report_builder.py`
- Modify: `dental_opg/api.py` (`get_reporting_setup_data` fields)
- Test: `dental_opg/tests/test_report_builder.py`

**Interfaces:**
- Consumes: `edited_text`, `impression_label` (Task 1).
- Produces: `build_report_sections(report)` unchanged signature; lines may contain `\n` (multi-line tooth descriptions). `get_reporting_setup_data()` standard findings now include `finding_template`, `impression_label`.

- [ ] **Step 1: Write failing tests** — append to `TestReportBuilderSectionFindings` in `test_report_builder.py`:

```python
	def test_edited_text_overrides_rendered_template(self):
		finding = self._standard_finding("Styloid Process", "Elongated", "Appears elongated on the {side} side")
		self.report.save_findings(
			section_findings=[
				{
					"section": "Styloid Process",
					"finding": finding.name,
					"is_custom": 0,
					"side": "Left",
					"edited_text": "Appears markedly elongated on the left side",
				}
			],
			tooth_findings=[],
		)
		self.report.reload()

		styloid = next(s for s in build_report_sections(self.report) if s["name"] == "STYLOID PROCESS")
		self.assertEqual(styloid["lines"], ["Appears markedly elongated on the left side"])

	def test_blank_edited_text_falls_back_to_template(self):
		finding = self._standard_finding("Styloid Process", "Elongated", "Appears elongated on the {side} side")
		self.report.save_findings(
			section_findings=[
				{"section": "Styloid Process", "finding": finding.name, "is_custom": 0, "side": "Left", "edited_text": "  "}
			],
			tooth_findings=[],
		)
		self.report.reload()

		styloid = next(s for s in build_report_sections(self.report) if s["name"] == "STYLOID PROCESS")
		self.assertEqual(styloid["lines"], ["Appears elongated on the left side"])

	def test_impression_label_merges_teeth_across_arches(self):
		upper = self._standard_finding("Maxillary Arch", "Partial upper", "Missing irt {tooth_number}")
		upper.db_set("allow_tooth", 1)
		upper.db_set("impression_label", "PARTIALLY EDENTULOUS")
		lower = self._standard_finding("Mandibular Arch", "Partial lower", "Missing irt {tooth_number}")
		lower.db_set("allow_tooth", 1)
		lower.db_set("impression_label", "PARTIALLY EDENTULOUS")
		self.report.save_findings(
			section_findings=[
				{"section": "Maxillary Arch", "finding": upper.name, "is_custom": 0, "tooth_number": "16, 17"},
				{"section": "Mandibular Arch", "finding": lower.name, "is_custom": 0, "tooth_number": "36"},
			],
			tooth_findings=[],
		)
		self.report.reload()

		impression = next(s for s in build_report_sections(self.report) if s["name"] == "RADIOLOGIC IMPRESSION")
		self.assertIn("PARTIALLY EDENTULOUS irt 16, 17, 36", impression["lines"])

	def test_impression_label_skipped_without_tooth_number(self):
		finding = self._standard_finding("Maxillary Arch", "Partial upper", "Partial complement noted")
		finding.db_set("impression_label", "PARTIALLY EDENTULOUS")
		self.report.save_findings(
			section_findings=[{"section": "Maxillary Arch", "finding": finding.name, "is_custom": 0, "tooth_number": ""}],
			tooth_findings=[],
		)
		self.report.reload()

		names = [s["name"] for s in build_report_sections(self.report)]
		self.assertNotIn("RADIOLOGIC IMPRESSION", names)

	def test_multi_line_tooth_description_keeps_line_breaks(self):
		self.report.save_findings(
			section_findings=[],
			tooth_findings=[
				{"tooth_number": "16", "finding_name": "Caries", "description": "Coronally - a\nRadicularly - b"}
			],
		)
		self.report.reload()

		arch = next(s for s in build_report_sections(self.report) if s["name"] == "MAXILLARY ARCH")
		self.assertEqual(arch["lines"], ["irt 16 - Coronally - a\nRadicularly - b"])
```

- [ ] **Step 2: Run, verify fail**

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.tests.test_report_builder`
Expected: `test_edited_text_overrides_rendered_template` and `test_impression_label_merges_teeth_across_arches` FAIL; others may already pass (they pin behaviour).

- [ ] **Step 3: Implement in `report_builder.py`.** Replace `_section_finding_lines` and add `_impression_label_lines`; wire into `build_report_sections`:

```python
def _standard_finding_masters(report):
	names = {row.finding for row in report.section_findings if row.finding}
	if not names:
		return {}
	return {
		row.name: row
		for row in frappe.get_all(
			"OPG Standard Finding",
			filters={"name": ["in", list(names)]},
			fields=["name", "finding_template", "finding_label", "impression_label"],
		)
	}


def _section_finding_lines(report, masters):
	lines_by_section = {section: [] for section in SECTION_ORDER}
	for row in report.section_findings:
		if row.is_custom or not row.finding:
			text = (row.custom_text or "").strip()
		elif (row.edited_text or "").strip():
			# Dentist individualized this finding for this patient only.
			text = row.edited_text.strip()
		else:
			master = masters.get(row.finding)
			text = _render_template(
				(master and master.finding_template) or "",
				side=SIDE_PHRASES.get(row.side, row.side or ""),
				tooth_number=row.tooth_number or "",
				level=(row.level or "").lower(),
			)
			# A finding the dentist explicitly selected must never silently
			# vanish - fall back to its label if the template rendered empty.
			if not text and master:
				text = (master.finding_label or "").strip()
		if text and row.section in lines_by_section:
			lines_by_section[row.section].append(text)
	return lines_by_section


def _impression_label_lines(report, masters):
	"""One "{impression_label} irt {teeth}" line per distinct label, teeth from
	every row of that label merged in first-seen order across both arches - so
	"Partial complement" picked in each arch yields one PARTIALLY EDENTULOUS
	line. Rows without tooth numbers contribute nothing."""
	teeth_by_label = {}
	for row in report.section_findings:
		master = masters.get(row.finding) if row.finding and not row.is_custom else None
		label = (master and master.impression_label or "").strip()
		teeth = [t.strip() for t in (row.tooth_number or "").split(",") if t.strip()]
		if not (label and teeth):
			continue
		bucket = teeth_by_label.setdefault(label, [])
		bucket.extend(t for t in teeth if t not in bucket)
	return [f"{label} irt {', '.join(teeth)}" for label, teeth in teeth_by_label.items()]
```

In `build_report_sections`, replace the first line and add the label lines before the tooth impression lines:

```python
	masters = _standard_finding_masters(report)
	section_lines = _section_finding_lines(report, masters)
	tooth_lines = _tooth_finding_lines(report)
	for section, extra_lines in tooth_lines.items():
		section_lines[section].extend(extra_lines)

	section_lines["Radiologic Impression"].extend(_impression_label_lines(report, masters))
	section_lines["Radiologic Impression"].extend(_impression_finding_lines(report))
```

Remove the old `standard_finding_names` / `masters` lookup block at the top of the old `_section_finding_lines`.

- [ ] **Step 4: Setup data fields** — in `dental_opg/api.py` `get_reporting_setup_data`, change standard-finding `fields` to:

```python
		fields=[
			"name",
			"section_name",
			"finding_label",
			"finding_template",
			"impression_label",
			"allow_side",
			"allow_tooth",
			"allow_level",
		],
```

- [ ] **Step 5: Run tests**

Run: `bench --site dental_opg-test.localhost run-tests --app dental_opg`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add dental_opg/dental_opg_reporting/report_builder.py dental_opg/api.py dental_opg/tests/test_report_builder.py
git commit -m "Support per-patient edited finding text and impression labels (PARTIALLY EDENTULOUS irt ...)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 4: DOCX export + print format formatting

**Files:**
- Modify: `dental_opg/dental_opg_reporting/docx_export.py`
- Modify: `dental_opg/fixtures/print_format.json`
- Test: `dental_opg/tests/test_docx_export.py`

**Interfaces:**
- Consumes: `build_report_sections` lines containing `\n` (Task 3).
- Produces: `build_docx(report) -> bytes` unchanged signature.

- [ ] **Step 1: Write failing tests** — append to `TestDocxExport`:

```python
	def _export(self, section_findings=None, tooth_findings=None):
		self.report.save_findings(section_findings=section_findings or [], tooth_findings=tooth_findings or [])
		self.report.reload()
		return DocxDocument(io.BytesIO(build_docx(self.report)))

	def _all_runs(self, doc):
		footer = doc.sections[0].footer
		paragraphs = list(doc.paragraphs) + list(footer.paragraphs)
		for table in list(doc.tables) + list(footer.tables):
			for row in table.rows:
				for cell in row.cells:
					paragraphs.extend(cell.paragraphs)
		return [run for p in paragraphs for run in p.runs if run.text.strip()]

	def test_no_blank_paragraphs_after_findings_start(self):
		doc = self._export(section_findings=[{"section": "Condylar Morphology", "finding": "csf-normal"}])
		texts = [p.text for p in doc.paragraphs]
		start = next(i for i, t in enumerate(texts) if t.strip().startswith("PANORAMIC RADIOGRAPH SHOWS"))
		blank = [
			i
			for i, p in enumerate(doc.paragraphs[start + 1 :], start + 1)
			if not p.text.strip() and not p._p.findall(".//" + qn("w:drawing")) and p._p.find("./" + qn("w:pPr") + "/" + qn("w:sectPr")) is None
		]
		self.assertEqual(blank, [])

	def test_section_headings_get_space_before(self):
		doc = self._export(section_findings=[{"section": "Condylar Morphology", "finding": "csf-normal"}])
		heading = next(p for p in doc.paragraphs if p.text.strip() == "CONDYLAR MORPHOLOGY:")
		self.assertEqual(heading.paragraph_format.space_before, Pt(6))

	def test_every_run_is_black_times_new_roman(self):
		doc = self._export(
			section_findings=[{"section": "Condylar Morphology", "finding": "csf-normal"}],
			tooth_findings=[{"tooth_number": "16", "finding_name": "Caries", "description": "Coronally - a"}],
		)
		runs = self._all_runs(doc)
		self.assertTrue(runs)
		for run in runs:
			self.assertEqual(run.font.name, "Times New Roman", run.text)
			self.assertEqual(run.font.color.rgb, RGBColor(0, 0, 0), run.text)

	def test_multi_line_description_uses_line_breaks(self):
		doc = self._export(
			tooth_findings=[
				{"tooth_number": "16", "finding_name": "Caries", "description": "Coronally - a\nRadicularly - b"}
			]
		)
		line = next(p for p in doc.paragraphs if "irt 16" in p.text)
		self.assertEqual(line.text, "irt 16 - Coronally - a\nRadicularly - b")
		self.assertTrue(line._p.findall(".//" + qn("w:br")))

	def test_footer_cells_centered_without_fill(self):
		doc = self._export()
		table = doc.sections[0].footer.tables[0]
		for cell in table.rows[0].cells:
			self.assertIsNone(cell._tc.get_or_add_tcPr().find(qn("w:shd")))
			self.assertEqual(cell.vertical_alignment, WD_CELL_VERTICAL_ALIGNMENT.CENTER)
			for p in cell.paragraphs:
				self.assertEqual(p.alignment, WD_ALIGN_PARAGRAPH.CENTER)
```

Add imports at top of the test file:

```python
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
```

- [ ] **Step 2: Run, verify fail**

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.tests.test_docx_export`
Expected: the 5 new tests FAIL.

- [ ] **Step 3: Implement in `docx_export.py`.** New imports:

```python
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor
```

Constants under `SECTION_HEADINGS`:

```python
FONT_NAME = "Times New Roman"
BLACK = RGBColor(0, 0, 0)
FINDINGS_START = "PANORAMIC RADIOGRAPH SHOWS"
```

`build_docx` body becomes:

```python
	doc = Document(str(TEMPLATE_PATH))

	patient = frappe.get_doc("OPG Patient", report.patient) if report.patient else None
	_replace_tokens(doc, _metadata_replacements(report, patient))
	_insert_image(doc, report)
	_fill_sections(doc, report)
	_remove_blank_paragraphs(doc)
	_space_section_headings(doc)
	_restyle_footer(doc)
	_apply_black_times_new_roman(doc)

	buffer = io.BytesIO()
	doc.save(buffer)
	return buffer.getvalue()
```

In `_fill_sections`, replace `marker.text = lines[0]` with `_set_text_with_breaks(marker, lines[0])`. In `_insert_paragraph_after`, replace `new_p.text = text` with `_set_text_with_breaks(new_p, text)`. New helpers:

```python
def _set_text_with_breaks(paragraph, text):
	"""Write text into paragraph as one run, turning each "\\n" into a Word
	line break so multi-line tooth descriptions (Coronally / Radicularly /
	Periapically) stay inside a single bullet."""
	for run in list(paragraph.runs):
		run._r.getparent().remove(run._r)
	run = paragraph.add_run()
	for i, part in enumerate(text.split("\n")):
		if i:
			run.add_break()
		run.add_text(part)


def _keeps_layout(paragraph):
	p = paragraph._p
	return bool(p.findall(".//" + qn("w:drawing"))) or p.find("./" + qn("w:pPr") + "/" + qn("w:sectPr")) is not None


def _remove_blank_paragraphs(doc):
	"""The template carries hardcoded empty paragraphs between sections, which
	show up as big gaps in the export. Drop every empty paragraph after the
	findings heading; spacing comes from _space_section_headings instead."""
	paragraphs = doc.paragraphs
	start = next((i for i, p in enumerate(paragraphs) if p.text.strip().startswith(FINDINGS_START)), None)
	if start is None:
		return
	for paragraph in paragraphs[start + 1 :]:
		if not paragraph.text.strip() and not _keeps_layout(paragraph):
			paragraph._p.getparent().remove(paragraph._p)


def _space_section_headings(doc):
	headings = set(SECTION_HEADINGS.values())
	for paragraph in doc.paragraphs:
		if paragraph.text.strip() in headings:
			paragraph.paragraph_format.space_before = Pt(6)


def _restyle_footer(doc):
	"""Plain, centered two-column Reported by / Verified by footer: no colored
	fills (text goes black in _apply_black_times_new_roman)."""
	for table in doc.sections[0].footer.tables:
		table.alignment = WD_TABLE_ALIGNMENT.CENTER
		for row in table.rows:
			for cell in row.cells:
				tc_pr = cell._tc.get_or_add_tcPr()
				for shading in tc_pr.findall(qn("w:shd")):
					tc_pr.remove(shading)
				cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
				for paragraph in cell.paragraphs:
					paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _apply_black_times_new_roman(doc):
	normal = doc.styles["Normal"]
	normal.font.name = FONT_NAME
	normal.font.color.rgb = BLACK
	normal.element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), FONT_NAME)
	for paragraph in _iter_all_paragraphs(doc):
		for run in paragraph.runs:
			run.font.name = FONT_NAME
			run.font.color.rgb = BLACK
			run._r.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), FONT_NAME)
```

Note: `_iter_all_paragraphs` (existing) covers body, body tables and footer — not the header, which is intentional (letterhead stays).

- [ ] **Step 4: Run tests**

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.tests.test_docx_export`
Expected: all pass. If `test_every_run_is_black_times_new_roman` fails on a run inside a `w:hyperlink` or text box, extend `_apply_black_times_new_roman` to also iterate `doc.element.body.iter(qn("w:r"))` via `docx.text.run.Run(r, paragraph)` — do not weaken the test.

- [ ] **Step 5: Print format** — script edit of the HTML inside the fixture (multi-line `<br>`, plain centered footer):

```bash
../../env/bin/python -I - <<'EOF'
import json
path = "dental_opg/fixtures/print_format.json"
data = json.load(open(path))
pf = data[0]
html = pf["html"]
replacements = [
	("<li>{{ line }}</li>", '<li>{{ line.replace("\\n", "<br>") }}</li>'),
	('<div class="opg-section-line">{{ line }}</div>', '<div class="opg-section-line">{{ line.replace("\\n", "<br>") }}</div>'),
	('<td style="background:#0070C0; color:#ffffff; text-align:center; padding:6px;">', '<td style="width:50%; color:#000; text-align:center; vertical-align:middle; padding:6px;">'),
	('<td style="background:#9CC2E5; color:#002060; text-align:center; padding:6px;">', '<td style="width:50%; color:#000; text-align:center; vertical-align:middle; padding:6px;">'),
]
for old, new in replacements:
	assert old in html, old
	html = html.replace(old, new)
pf["html"] = html
pf["modified"] = "2026-10-13 12:00:00.000000"
json.dump(data, open(path, "w"), indent=4, ensure_ascii=False)
open(path, "a").write("\n")
EOF
cd /workspace/development/frappe-bench && bench --site dental_opg-test.localhost migrate
```

Verify: `bench --site dental_opg-test.localhost execute frappe.db.get_value --args "['Print Format', 'OPG Report', 'html']" | grep -c 'background:#0070C0'` → `0`.

- [ ] **Step 6: Full tests + commit**

```bash
bench --site dental_opg-test.localhost run-tests --app dental_opg
cd apps/dental_opg
git add dental_opg/dental_opg_reporting/docx_export.py dental_opg/tests/test_docx_export.py dental_opg/fixtures/print_format.json
git commit -m "DOCX export: drop blank gaps, black Times New Roman text, centered plain footer, multi-line findings

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 5: Signatory suggestions API

**Files:**
- Modify: `dental_opg/api.py`
- Test: `dental_opg/tests/test_api.py` (create)

**Interfaces:**
- Produces: `GET /api/method/dental_opg.api.get_signatory_suggestions` → `{"reported_by": [str], "verified_by": [str]}`, distinct, most recently modified first, ≤ 50 each.

- [ ] **Step 1: Failing test** — `dental_opg/tests/test_api.py`:

```python
import frappe
from frappe.tests import IntegrationTestCase

from dental_opg.api import get_signatory_suggestions


class TestSignatorySuggestions(IntegrationTestCase):
	def _report(self, reported_by, verified_by):
		patient = frappe.get_doc(
			doctype="OPG Patient", patient_name="Signatory Test", registration_no=frappe.generate_hash(length=8)
		).insert()
		return frappe.get_doc(
			doctype="OPG Report", patient=patient.name, reported_by=reported_by, verified_by=verified_by
		).insert()

	def test_returns_distinct_names_newest_first(self):
		older = frappe.generate_hash(length=6)
		newer = frappe.generate_hash(length=6)
		self._report(f"Dr {older}", f"Dr V{older}")
		self._report(f"Dr {older}", "")
		self._report(f"Dr {newer}", f"Dr V{newer}")

		result = get_signatory_suggestions()

		reported = result["reported_by"]
		self.assertEqual(reported.count(f"Dr {older}"), 1)
		self.assertLess(reported.index(f"Dr {newer}"), reported.index(f"Dr {older}"))
		self.assertIn(f"Dr V{older}", result["verified_by"])
		self.assertNotIn("", result["verified_by"])
		self.assertLessEqual(len(reported), 50)
```

- [ ] **Step 2: Run, verify fail** — `bench --site dental_opg-test.localhost run-tests --module dental_opg.tests.test_api` → ImportError.

- [ ] **Step 3: Implement** in `dental_opg/api.py` (after `get_reporting_setup_data`):

```python
SIGNATORY_FIELDS = ("reported_by", "verified_by")
MAX_SIGNATORY_SUGGESTIONS = 50


@frappe.whitelist(methods=["GET"])
def get_signatory_suggestions():
	"""Names previously typed into Reported by / Verified by, most recent first,
	so the editor can offer them instead of making the dentist retype them."""
	suggestions = {}
	for field in SIGNATORY_FIELDS:
		values = frappe.get_all(
			"OPG Report",
			filters={field: ["is", "set"]},
			pluck=field,
			order_by="modified desc",
			limit_page_length=500,
		)
		unique = []
		for value in values:
			name = (value or "").strip()
			if name and name not in unique:
				unique.append(name)
		suggestions[field] = unique[:MAX_SIGNATORY_SUGGESTIONS]
	return suggestions
```

- [ ] **Step 4: Run tests** — module then full app; expected pass.

- [ ] **Step 5: Commit**

```bash
git add dental_opg/api.py dental_opg/tests/test_api.py
git commit -m "Add signatory suggestions endpoint for Reported by / Verified by memory

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 6: FindingPicker + SectionCard (search, A–Z, edit per patient)

**Files:**
- Create: `frontend/src/components/FindingPicker.vue`
- Create: `frontend/src/findingText.js`
- Modify: `frontend/src/components/SectionCard.vue`

**Interfaces:**
- Consumes: setup data `finding_template` (Task 3); row field `edited_text` (Task 1).
- Produces: `<FindingPicker :items labelField placeholder @pick>`; `renderTemplate(template, row) -> string`, `fillToothNumber(text, teeth[]) -> string` in `findingText.js` (used by Task 7).

- [ ] **Step 1: `frontend/src/findingText.js`:**

```js
// Mirrors report_builder._render_template: only {side}, {tooth_number},
// {level} are substituted; whitespace collapsed.
const PLACEHOLDER = /\{(side|tooth_number|level)\}/g

export function renderTemplate(template, row) {
	const values = {
		side: (row.side || '').toLowerCase(),
		tooth_number: row.tooth_number || '',
		level: (row.level || '').toLowerCase(),
	}
	return (template || '').replace(PLACEHOLDER, (_, key) => values[key]).split(/\s+/).filter(Boolean).join(' ')
}

// Clinic finding texts carry a literal "(tooth number)" placeholder.
export function fillToothNumber(text, teeth) {
	return (text || '').replaceAll('(tooth number)', teeth.join(', '))
}
```

- [ ] **Step 2: `frontend/src/components/FindingPicker.vue`:**

```vue
<template>
	<div>
		<input
			v-model="query"
			:placeholder="`Search ${placeholder}...`"
			class="mb-2 w-full rounded border px-2 py-1 text-xs"
		/>
		<div class="flex max-h-48 flex-wrap gap-1.5 overflow-y-auto">
			<button
				v-for="item in visibleItems"
				:key="item.name"
				class="rounded-full border border-gray-300 px-2.5 py-1 text-xs hover:bg-gray-100"
				@click="emit('pick', item)"
			>
				+ {{ item[labelField] }}
			</button>
			<span v-if="!visibleItems.length" class="text-xs text-gray-400">No findings match "{{ query }}"</span>
		</div>
	</div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
	items: { type: Array, default: () => [] },
	labelField: { type: String, required: true },
	placeholder: { type: String, default: 'findings' },
})
const emit = defineEmits(['pick'])

const query = ref('')

const visibleItems = computed(() => {
	const q = query.value.trim().toLowerCase()
	const label = (item) => item[props.labelField] || ''
	return props.items
		.filter((item) => !q || label(item).toLowerCase().includes(q))
		.sort((a, b) => label(a).localeCompare(label(b), undefined, { sensitivity: 'base' }))
})
</script>
```

(`filter` returns a new array, so `sort` never mutates the prop.)

- [ ] **Step 3: Rewrite `SectionCard.vue` template + script:**

```vue
<template>
	<div class="rounded border bg-white p-4">
		<h2 class="mb-2 text-sm font-semibold text-gray-800">{{ section }}</h2>

		<FindingPicker class="mb-3" :items="standardFindings" label-field="finding_label" @pick="addFinding" />

		<div v-if="rows.length" class="space-y-2">
			<div v-for="(row, idx) in rows" :key="idx" class="rounded bg-gray-50 p-2 text-xs">
				<div class="flex flex-wrap items-center gap-2">
					<span class="min-w-[10rem] flex-1">
						{{ row.is_custom ? row.custom_text : labelFor(row.finding) }}
					</span>
					<select v-if="!row.is_custom && master(row)?.allow_side" v-model="row.side" class="rounded border px-1 py-0.5" @change="emitUpdate">
						<option value="">side...</option>
						<option>Left</option>
						<option>Right</option>
						<option>Bilateral</option>
					</select>
					<input
						v-if="!row.is_custom && master(row)?.allow_tooth"
						v-model="row.tooth_number"
						placeholder="tooth #"
						class="w-24 rounded border px-1 py-0.5"
						@input="emitUpdate"
					/>
					<select v-if="!row.is_custom && master(row)?.allow_level" v-model="row.level" class="rounded border px-1 py-0.5" @change="emitUpdate">
						<option value="">level...</option>
						<option>Cervical Third</option>
						<option>Middle Third</option>
						<option>Apical Third</option>
					</select>
					<button v-if="!row.is_custom" class="text-gray-700 underline" @click="toggleEdit(row)">
						{{ editing.has(row) ? 'done' : 'edit' }}
					</button>
					<button class="text-red-600" @click="removeRow(idx)">remove</button>
				</div>
				<div v-if="!row.is_custom && editing.has(row)" class="mt-2">
					<textarea
						v-model="row.edited_text"
						rows="5"
						class="w-full resize-y rounded border px-2 py-1 text-sm"
						@input="emitUpdate"
					></textarea>
					<button class="text-gray-600 underline" @click="resetEdit(row)">reset to standard text</button>
				</div>
				<p v-else-if="!row.is_custom && row.edited_text" class="mt-1 whitespace-pre-line text-gray-600">
					{{ row.edited_text }}
				</p>
			</div>
		</div>

		<div class="mt-3 flex gap-2">
			<input
				v-model="customText"
				placeholder="Add custom finding for this section"
				class="flex-1 rounded border px-2 py-1 text-xs"
				@keyup.enter="addCustom"
			/>
			<button class="rounded bg-gray-900 px-2 py-1 text-xs text-white" @click="addCustom">Add</button>
		</div>
		<p class="mt-1 text-[11px] text-gray-500">Custom findings are saved to the list for future reports.</p>
	</div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import FindingPicker from './FindingPicker.vue'
import { renderTemplate } from '../findingText'

const props = defineProps({
	section: { type: String, required: true },
	standardFindings: { type: Array, default: () => [] },
	rows: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:rows'])

const customText = ref('')
const editing = reactive(new Set())

function master(row) {
	return props.standardFindings.find((f) => f.name === row.finding)
}
function labelFor(findingName) {
	return props.standardFindings.find((f) => f.name === findingName)?.finding_label || findingName
}

function emitUpdate() {
	emit('update:rows', [...props.rows])
}

function toggleEdit(row) {
	if (editing.has(row)) {
		editing.delete(row)
		return
	}
	if (!row.edited_text) row.edited_text = renderTemplate(master(row)?.finding_template, row) || labelFor(row.finding)
	editing.add(row)
	emitUpdate()
}

function resetEdit(row) {
	row.edited_text = ''
	editing.delete(row)
	emitUpdate()
}

function addFinding(sf) {
	emit('update:rows', [
		...props.rows,
		{ section: props.section, finding: sf.name, is_custom: 0, side: '', tooth_number: '', level: '', edited_text: '' },
	])
}

function addCustom() {
	if (!customText.value.trim()) return
	emit('update:rows', [...props.rows, { section: props.section, is_custom: 1, custom_text: customText.value.trim() }])
	customText.value = ''
}

function removeRow(idx) {
	const next = [...props.rows]
	const [removed] = next.splice(idx, 1)
	editing.delete(removed)
	emit('update:rows', next)
}
</script>
```

Note: once `edited_text` is set, changing side/tooth/level no longer changes the output text — that is the "individualized" contract; "reset to standard text" returns to template rendering.

- [ ] **Step 4: Build**

```bash
cd /workspace/development/frappe-bench/apps/dental_opg/frontend && yarn build
```
Expected: build succeeds, no errors.

- [ ] **Step 5: Commit** (source only; bundle committed in Task 9)

```bash
cd .. && git add frontend/src/findingText.js frontend/src/components/FindingPicker.vue frontend/src/components/SectionCard.vue frontend/components.d.ts
git commit -m "Searchable A-Z finding picker and per-patient edit of section findings

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 7: ToothChart (multi-select edit, bigger box, child chart, custom name+description)

**Files:**
- Modify: `frontend/src/components/ToothChart.vue` (full rewrite below)

**Interfaces:**
- Consumes: `FindingPicker`, `fillToothNumber` (Task 6).
- Props/emit unchanged: `arch`, `toothFindings`, `toothFindingsMaster`, `update:toothFindings`.

- [ ] **Step 1: Replace `ToothChart.vue` with:**

```vue
<template>
	<div>
		<div class="mb-2 flex flex-wrap items-center gap-2">
			<div class="flex overflow-hidden rounded border text-xs">
				<button
					v-for="m in CHART_MODES"
					:key="m"
					class="px-2 py-1"
					:class="chartMode === m ? 'bg-gray-900 text-white' : ''"
					@click="chartMode = m"
				>
					{{ m }}
				</button>
			</div>
			<span class="text-xs text-gray-500">{{ multiSelect ? 'Click teeth to select multiple' : 'Click a tooth' }}</span>
			<button
				class="ml-auto rounded border px-2 py-1 text-xs"
				:class="multiSelect ? 'border-gray-900 bg-gray-900 text-white' : 'border-gray-300'"
				@click="toggleMultiSelect"
			>
				{{ multiSelect ? 'Multi-select on' : 'Select multiple teeth' }}
			</button>
		</div>

		<div class="space-y-1">
			<div v-for="(toothRow, r) in toothRows" :key="r" class="flex flex-wrap justify-center gap-1">
				<button
					v-for="tooth in toothRow"
					:key="tooth"
					class="relative h-9 w-9 rounded border text-xs font-medium hover:bg-gray-100"
					:class="[
						isHighlighted(tooth) ? 'border-gray-900 ring-1 ring-gray-900' : 'border-gray-300',
						countFor(tooth) ? 'border-red-300 bg-red-50 text-red-700' : '',
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
		</div>

		<div v-if="panelTeeth.length" class="mt-3 rounded border bg-gray-50 p-3">
			<div class="mb-2 text-sm font-medium">
				{{ panelTeeth.length > 1 ? `Teeth ${panelTeeth.join(', ')} findings` : `Tooth ${panelTeeth[0]} findings` }}
			</div>

			<div class="mb-3 space-y-3">
				<div v-for="tooth in panelTeeth" :key="tooth">
					<div v-if="panelTeeth.length > 1" class="mb-1 text-xs font-semibold text-gray-700">Tooth {{ tooth }}</div>
					<p v-if="!rowsFor(tooth).length" class="text-xs text-gray-400">No findings yet</p>
					<div v-for="(row, i) in rowsFor(tooth)" :key="i" class="mb-2 rounded border bg-white p-2 text-xs">
						<div class="mb-1 flex items-center justify-between gap-2">
							<span class="font-medium">{{ row.finding_name }}</span>
							<button class="text-red-600" @click="removeRow(row)">remove</button>
						</div>
						<textarea
							v-model="row.description"
							rows="5"
							class="w-full resize-y rounded border px-2 py-1 text-sm"
							@input="emitUpdate"
						></textarea>
					</div>
				</div>
			</div>

			<FindingPicker :items="toothFindingsMaster" label-field="finding_name" @pick="addFinding" />

			<div class="mt-3 space-y-1 border-t pt-3">
				<input v-model="customName" placeholder="Custom finding name" class="w-full rounded border px-2 py-1 text-xs" />
				<textarea
					v-model="customDescription"
					rows="3"
					placeholder="Description (leave empty to use the name)"
					class="w-full resize-y rounded border px-2 py-1 text-sm"
				></textarea>
				<div class="flex items-center justify-between">
					<span class="text-[11px] text-gray-500">Saved to the list for future reports.</span>
					<button class="rounded bg-gray-900 px-2 py-1 text-xs text-white" @click="addCustom">Add</button>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed } from 'vue'
import FindingPicker from './FindingPicker.vue'
import { fillToothNumber } from '../findingText'

const props = defineProps({
	arch: { type: String, required: true }, // 'Maxillary' | 'Mandibular'
	toothFindings: { type: Array, default: () => [] },
	toothFindingsMaster: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:toothFindings'])

const UPPER = ['18', '17', '16', '15', '14', '13', '12', '11', '21', '22', '23', '24', '25', '26', '27', '28']
const LOWER = ['48', '47', '46', '45', '44', '43', '42', '41', '31', '32', '33', '34', '35', '36', '37', '38']
const UPPER_CHILD = ['55', '54', '53', '52', '51', '61', '62', '63', '64', '65']
const LOWER_CHILD = ['85', '84', '83', '82', '81', '71', '72', '73', '74', '75']
const CHILD_TEETH = new Set([...UPPER_CHILD, ...LOWER_CHILD])
const CHART_MODES = ['Adult', 'Child', 'Mixed']

const chartMode = ref(props.toothFindings.some((r) => CHILD_TEETH.has(r.tooth_number)) ? 'Mixed' : 'Adult')

const toothRows = computed(() => {
	const adult = props.arch === 'Maxillary' ? UPPER : LOWER
	const child = props.arch === 'Maxillary' ? UPPER_CHILD : LOWER_CHILD
	if (chartMode.value === 'Adult') return [adult]
	if (chartMode.value === 'Child') return [child]
	// Deciduous row sits toward the occlusal plane: below upper, above lower.
	return props.arch === 'Maxillary' ? [adult, child] : [child, adult]
})

const multiSelect = ref(false)
const selectedTooth = ref(null)
const selectedTeeth = ref([])
const customName = ref('')
const customDescription = ref('')

const panelTeeth = computed(() =>
	multiSelect.value ? selectedTeeth.value : selectedTooth.value ? [selectedTooth.value] : [],
)

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

function emitUpdate() {
	emit('update:toothFindings', [...props.toothFindings])
}

function rowsForPanel(fields) {
	return panelTeeth.value.map((tooth) => ({ tooth_number: tooth, arch: props.arch, ...fields }))
}

function addFinding(masterFinding) {
	const newRows = rowsForPanel({
		finding: masterFinding.name,
		finding_name: masterFinding.finding_name,
		description: fillToothNumber(masterFinding.description_template, panelTeeth.value),
	})
	emit('update:toothFindings', [...props.toothFindings, ...newRows])
}

function addCustom() {
	const name = customName.value.trim()
	if (!name || !panelTeeth.value.length) return
	const newRows = rowsForPanel({
		finding: null,
		finding_name: name,
		description: customDescription.value.trim() || name,
	})
	emit('update:toothFindings', [...props.toothFindings, ...newRows])
	customName.value = ''
	customDescription.value = ''
}

function removeRow(row) {
	emit(
		'update:toothFindings',
		props.toothFindings.filter((r) => r !== row),
	)
}
</script>
```

Note: `arch` for a deciduous row is the card's arch (`Maxillary` card shows 51–65), consistent with server-side `validate` from Task 1.

- [ ] **Step 2: Build** — `cd frontend && yarn build` → succeeds.

- [ ] **Step 3: Commit**

```bash
cd .. && git add frontend/src/components/ToothChart.vue
git commit -m "Tooth chart: editable findings in multi-select, bigger text box, child/mixed chart, custom name + description

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 8: Annotation tools — Polyline, Landmark, Curve (viewer + baked image)

**Files:**
- Modify: `dental_opg/dental_opg_reporting/image_utils.py`
- Modify: `frontend/src/components/ImageViewer.vue`
- Test: `dental_opg/tests/test_image_utils.py`

**Interfaces:**
- Consumes: annotation types from Task 1.
- Produces: `catmull_rom_points(points: list[tuple[float, float]], samples_per_segment: int = 16) -> list[tuple[float, float]]` in `image_utils.py`; JS `curvePath(points)` in `ImageViewer.vue` using identical control-point math.

- [ ] **Step 1: Failing tests** — append to `TestImageUtils` (and import `catmull_rom_points` alongside `get_annotated_image_bytes`):

```python
	def _red_at(self, annotations, xy):
		self._attach_image(_make_test_jpeg_bytes())
		self.report.save_annotations(annotations=annotations)
		self.report.reload()
		pixel = Image.open(io.BytesIO(get_annotated_image_bytes(self.report))).convert("RGB").getpixel(xy)
		return pixel[0] > 150 and pixel[1] < 100 and pixel[2] < 100

	def test_polyline_draws_through_vertices(self):
		path = '[{"x": 0.1, "y": 0.5}, {"x": 0.5, "y": 0.5}, {"x": 0.5, "y": 0.9}]'
		self.assertTrue(self._red_at([{"annotation_type": "Polyline", "path_data": path, "color": "#ff0000"}], (30, 30)))

	def test_curve_draws_through_control_points(self):
		path = '[{"x": 0.1, "y": 0.2}, {"x": 0.5, "y": 0.5}, {"x": 0.9, "y": 0.2}]'
		self.assertTrue(self._red_at([{"annotation_type": "Curve", "path_data": path, "color": "#ff0000"}], (50, 30)))

	def test_landmark_draws_marker_at_point(self):
		self.assertTrue(
			self._red_at(
				[{"annotation_type": "Landmark", "x": 0.5, "y": 0.5, "label_text": "Go", "color": "#ff0000"}], (50, 30)
			)
		)

	def test_catmull_rom_passes_through_every_control_point(self):
		points = [(0.0, 0.0), (10.0, 5.0), (20.0, 0.0), (30.0, 8.0)]
		sampled = catmull_rom_points(points)
		for p in points:
			self.assertTrue(any(abs(s[0] - p[0]) < 1e-9 and abs(s[1] - p[1]) < 1e-9 for s in sampled), p)

	def test_curve_with_single_point_is_skipped(self):
		self.assertFalse(
			self._red_at([{"annotation_type": "Curve", "path_data": '[{"x": 0.5, "y": 0.5}]', "color": "#ff0000"}], (50, 30))
		)
```

(Test image is 100×60, so normalized (0.5, 0.5) = pixel (50, 30); polyline segment (0.1,0.5)→(0.5,0.5) passes pixel (30, 30).)

- [ ] **Step 2: Run, verify fail** — `bench --site dental_opg-test.localhost run-tests --module dental_opg.tests.test_image_utils` → ImportError on `catmull_rom_points`.

- [ ] **Step 3: Implement in `image_utils.py`:**

Extract font loading from `_draw_text` and add helpers:

```python
def _load_font(width, height):
	font_size = max(14, int(min(width, height) * 0.03))
	try:
		return ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
	except OSError:
		return ImageFont.load_default()


def _line_width(width, height):
	return max(2, int(min(width, height) * 0.003))


def _path_coords(ann, width, height):
	if not ann.path_data:
		return []
	return [_denormalize(p["x"], p["y"], width, height) for p in json.loads(ann.path_data)]


def catmull_rom_points(points, samples_per_segment=16):
	"""Sample a smooth curve passing through every control point (uniform
	Catmull-Rom expressed as cubic Beziers - same math as curvePath() in
	ImageViewer.vue, so the baked image matches what the dentist drew)."""
	if len(points) < 2:
		return list(points)
	out = [points[0]]
	for i in range(len(points) - 1):
		p0 = points[i - 1] if i > 0 else points[i]
		p1, p2 = points[i], points[i + 1]
		p3 = points[i + 2] if i + 2 < len(points) else p2
		c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
		c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
		for step in range(1, samples_per_segment + 1):
			t = step / samples_per_segment
			mt = 1 - t
			out.append(
				tuple(
					mt**3 * p1[k] + 3 * mt**2 * t * c1[k] + 3 * mt * t**2 * c2[k] + t**3 * p2[k]
					for k in (0, 1)
				)
			)
	return out
```

Rewrite `_draw_text` to use `_load_font(width, height)`, `_draw_freehand` to use `_path_coords` + `_line_width`, and add:

```python
def _draw_curve(draw, ann, width, height):
	coords = _path_coords(ann, width, height)
	if len(coords) > 1:
		draw.line(catmull_rom_points(coords), fill=ann.color or "#ff0000", width=_line_width(width, height))


def _draw_landmark(draw, ann, width, height):
	cx, cy = _denormalize(ann.x or 0, ann.y or 0, width, height)
	color = ann.color or "#ff0000"
	arm = max(6, int(min(width, height) * 0.015))
	line_width = _line_width(width, height)
	draw.line([cx - arm, cy, cx + arm, cy], fill=color, width=line_width)
	draw.line([cx, cy - arm, cx, cy + arm], fill=color, width=line_width)
	if ann.label_text:
		draw.text((cx + arm + 2, cy - arm), ann.label_text, fill=color, font=_load_font(width, height))


_DRAW_FUNCS = {
	"Point": _draw_point,
	"Arrow": _draw_arrow,
	"Text": _draw_text,
	"Freehand": _draw_freehand,
	"Polyline": _draw_freehand,  # straight segments between vertices, same as freehand
	"Curve": _draw_curve,
	"Landmark": _draw_landmark,
}
```

- [ ] **Step 4: Run image tests** — expected all pass. Then full app tests.

- [ ] **Step 5: ImageViewer.vue changes.**

Tools list:

```js
const tools = [
	{ value: 'pan', label: 'Pan' },
	{ value: 'Point', label: 'Point' },
	{ value: 'Landmark', label: 'Landmark' },
	{ value: 'Arrow', label: 'Arrow' },
	{ value: 'Text', label: 'Text' },
	{ value: 'Freehand', label: 'Freehand' },
	{ value: 'Polyline', label: 'Polyline' },
	{ value: 'Curve', label: 'Curve' },
]
const PATH_TOOLS = ['Polyline', 'Curve']
```

Under the tool buttons add a hint:

```vue
			<span v-if="PATH_TOOLS.includes(mode)" class="text-gray-500">Click points, double-click or Enter to finish, Esc to cancel</span>
```

Viewport element: add `tabindex="0"`, `@dblclick="finishPath"`, `@keydown.enter.prevent="finishPath"`, `@keydown.esc="cancelPath"`, and class `outline-none`.

Inside `<template v-for="(a, i) in annotations">` add after the Freehand polyline:

```vue
						<polyline
							v-else-if="a.annotation_type === 'Polyline'"
							:points="pathPoints(a)"
							fill="none"
							stroke="#ff0000"
							stroke-width="0.003"
						/>
						<path
							v-else-if="a.annotation_type === 'Curve'"
							:d="curvePath(parsePath(a))"
							fill="none"
							stroke="#ff0000"
							stroke-width="0.003"
						/>
						<g v-else-if="a.annotation_type === 'Landmark'">
							<line :x1="a.x - 0.012" :y1="a.y" :x2="a.x + 0.012" :y2="a.y" stroke="#ff0000" stroke-width="0.003" />
							<line :x1="a.x" :y1="a.y - 0.012" :x2="a.x" :y2="a.y + 0.012" stroke="#ff0000" stroke-width="0.003" />
							<text :x="a.x + 0.015" :y="a.y - 0.008" font-size="0.024" fill="#ff0000">{{ a.label_text }}</text>
						</g>
```

After the in-progress freehand `<polyline v-if="drawingPath.length" ...>` add the in-progress path preview:

```vue
					<polyline
						v-if="pendingPath.length && mode === 'Polyline'"
						:points="pendingPath.map((p) => `${p.x},${p.y}`).join(' ')"
						fill="none"
						stroke="#ff0000"
						stroke-width="0.003"
						stroke-dasharray="0.01 0.006"
					/>
					<path
						v-if="pendingPath.length && mode === 'Curve'"
						:d="curvePath(pendingPath)"
						fill="none"
						stroke="#ff0000"
						stroke-width="0.003"
						stroke-dasharray="0.01 0.006"
					/>
					<circle v-for="(p, k) in pendingPath" :key="`v${k}`" :cx="p.x" :cy="p.y" r="0.004" fill="#ff0000" />
```

Text-label bar placeholder becomes dynamic: `:placeholder="pendingText.annotation_type === 'Landmark' ? 'Landmark name, press Enter to place' : 'Annotation label, press Enter to place'"`.

Script additions/changes:

```js
const pendingPath = ref([])

// in onMouseDown, after `const point = getNormalizedPoint(e)`, extend the chain:
	} else if (mode.value === 'Landmark') {
		pendingText.value = { annotation_type: 'Landmark', x: point.x, y: point.y, label_text: '' }
		nextTick(() => textInput.value?.focus())
	} else if (PATH_TOOLS.includes(mode.value)) {
		viewport.value.focus()
		pendingPath.value = [...pendingPath.value, point]
	}

const SAME_POINT = 0.002

function distinctPoints(points) {
	// dblclick is preceded by two mousedowns on the same spot - collapse them.
	return points.filter((p, i) => {
		const prev = points[i - 1]
		return !prev || Math.hypot(p.x - prev.x, p.y - prev.y) > SAME_POINT
	})
}

function finishPath() {
	if (!PATH_TOOLS.includes(mode.value)) return
	const points = distinctPoints(pendingPath.value)
	if (points.length > 1) addAnnotation({ annotation_type: mode.value, path_data: JSON.stringify(points) })
	pendingPath.value = []
}

function cancelPath() {
	pendingPath.value = []
}

function parsePath(a) {
	try {
		return JSON.parse(a.path_data)
	} catch {
		return []
	}
}

// Same control-point math as image_utils.catmull_rom_points.
function curvePath(points) {
	if (points.length < 2) return ''
	let d = `M${points[0].x},${points[0].y}`
	for (let i = 0; i < points.length - 1; i++) {
		const p0 = points[i - 1] || points[i]
		const p1 = points[i]
		const p2 = points[i + 1]
		const p3 = points[i + 2] || p2
		const c1x = p1.x + (p2.x - p0.x) / 6
		const c1y = p1.y + (p2.y - p0.y) / 6
		const c2x = p2.x - (p3.x - p1.x) / 6
		const c2y = p2.y - (p3.y - p1.y) / 6
		d += ` C${c1x},${c1y} ${c2x},${c2y} ${p2.x},${p2.y}`
	}
	return d
}
```

Rewrite `pathPoints(a)` as:

```js
function pathPoints(a) {
	return parsePath(a)
		.map((p) => `${p.x},${p.y}`)
		.join(' ')
}
```

Clear an unfinished path when the tool changes: in the tool buttons replace `@click="mode = t.value"` with `@click="selectTool(t.value)"` and add:

```js
function selectTool(value) {
	mode.value = value
	pendingPath.value = []
}
```

- [ ] **Step 6: Build** — `cd frontend && yarn build` → succeeds.

- [ ] **Step 7: Commit**

```bash
cd .. && git add dental_opg/dental_opg_reporting/image_utils.py dental_opg/tests/test_image_utils.py frontend/src/components/ImageViewer.vue
git commit -m "Add Polyline, Landmark and Curve annotation tools, baked into print/DOCX image

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 9: ReportEditor (patient info, signatory memory), Times New Roman UI, build + ship bundle

**Files:**
- Modify: `frontend/src/api.js`
- Modify: `frontend/src/pages/ReportEditor.vue`
- Modify: `frontend/tailwind.config.js`
- Modify (build output): `dental_opg/public/frontend/**`, `dental_opg/www/dental_opg.html`

**Interfaces:**
- Consumes: `get_signatory_suggestions` (Task 5).

- [ ] **Step 1: `api.js` additions:**

```js
export function getPatient(name) {
	return frappeRequest({
		url: '/api/method/frappe.client.get',
		method: 'GET',
		params: { doctype: 'OPG Patient', name },
	})
}

export function getSignatorySuggestions() {
	return frappeRequest({
		url: '/api/method/dental_opg.api.get_signatory_suggestions',
		method: 'GET',
	})
}
```

- [ ] **Step 2: `ReportEditor.vue`.** Imports: add `getPatient, getSignatorySuggestions`. State:

```js
const patient = reactive({})
const signatories = reactive({ reported_by: [], verified_by: [] })
```

`onMounted` becomes:

```js
onMounted(async () => {
	const [reportData, setupData] = await Promise.all([getReport(props.reportId), getSetupData()])
	Object.assign(report, reportData)
	Object.assign(setup, setupData)
	sectionFindings.value = reportData.section_findings || []
	toothFindings.value = reportData.tooth_findings || []
	annotations.value = reportData.annotations || []
	loading.value = false
	// Header extras must not block the editor if they fail.
	if (reportData.patient) getPatient(reportData.patient).then((p) => Object.assign(patient, p)).catch(() => {})
	getSignatorySuggestions().then((s) => Object.assign(signatories, s)).catch(() => {})
})
```

Top bar, after `<h1 ...>{{ report.name }}</h1>`:

```vue
			<span v-if="patient.patient_name" class="text-sm text-gray-700">
				{{ patient.patient_name }}<template v-if="patient.age"> · {{ patient.age }} yrs</template><template v-if="patient.sex"> · {{ patient.sex }}</template>
			</span>
```

Report Details: replace the `Patient` block with three read-only blocks:

```vue
						<div>
							<label class="mb-1 block font-medium">Patient Name</label>
							<div class="rounded border bg-gray-50 px-2 py-1">{{ patient.patient_name || report.patient }}</div>
						</div>
						<div>
							<label class="mb-1 block font-medium">Age / Sex</label>
							<div class="rounded border bg-gray-50 px-2 py-1">{{ patient.age || '-' }} / {{ patient.sex || '-' }}</div>
						</div>
						<div>
							<label class="mb-1 block font-medium">Registration No</label>
							<div class="rounded border bg-gray-50 px-2 py-1">{{ patient.registration_no || '-' }}</div>
						</div>
```

Reported/Verified inputs get datalists:

```vue
						<div>
							<label class="mb-1 block font-medium">Reported By</label>
							<input v-model="report.reported_by" list="reported-by-options" class="w-full rounded border px-2 py-1" />
							<datalist id="reported-by-options">
								<option v-for="n in signatories.reported_by" :key="n" :value="n" />
							</datalist>
						</div>
						<div>
							<label class="mb-1 block font-medium">Verified By</label>
							<input v-model="report.verified_by" list="verified-by-options" class="w-full rounded border px-2 py-1" />
							<datalist id="verified-by-options">
								<option v-for="n in signatories.verified_by" :key="n" :value="n" />
							</datalist>
						</div>
```

Generated Report Text textarea: remove `font-mono` from its class list.

- [ ] **Step 3: Times New Roman** — `frontend/tailwind.config.js`:

```js
module.exports = {
	content: ['./index.html', './src/**/*.{vue,js,ts}', 'node_modules/frappe-ui/src/components/**/*.{vue,js,ts}'],
	theme: {
		extend: {
			fontFamily: {
				sans: ['"Times New Roman"', 'Times', 'serif'],
			},
		},
	},
	plugins: [],
}
```

Then `grep -rn "font-mono\|font-family" frontend/src` — remove any remaining `font-mono` and any hardcoded `font-family` that is not Times New Roman. If `frontend/src/index.css` imports frappe-ui styles that set `font-family` on `body`, add `body { font-family: "Times New Roman", Times, serif; }` at the end of `index.css`.

- [ ] **Step 4: Build**

```bash
cd /workspace/development/frappe-bench/apps/dental_opg/frontend && yarn build
cd .. && git status --short dental_opg/public dental_opg/www
```
Expected: new hashed asset files under `dental_opg/public/frontend/assets/`, old ones removed, `dental_opg/www/dental_opg.html` updated.

- [ ] **Step 5: Manual browser check** on `dev.localhost` (create your own test patient/report, delete after). Use the `run` / `claude-in-chrome` skill. Verify each:
  1. Header + Report Details show patient name, age, sex, reg no.
  2. Reported By input offers previously used names.
  3. Section card: search filters chips; chips A–Z; "edit" opens prefilled textarea; Generate Report shows edited text; "reset" restores template text.
  4. Tooth chart: Adult/Child/Mixed toggles; tooth 55 finding lands under Maxillary Arch after generate.
  5. Multi-select 16+17, add "Periodontitis": both teeth listed with editable textareas; `(tooth number)` replaced with `16, 17`.
  6. Custom tooth finding > 140 chars saves.
  7. Partial complement (Maxillary) tooth # 18 → Radiologic Impression has `PARTIALLY EDENTULOUS irt 18`; no "tooth number" words.
  8. Polyline / Curve: click 3 points, double-click → one annotation; Esc cancels. Landmark: click, type "Go", Enter.
  9. Export DOCX: open it — no big gaps, all text black Times New Roman, Coronally/Radicularly/Periapically on separate lines, footer centered; annotations visible in image.
  10. Print view: same footer + multi-line.
  11. Whole UI renders in Times New Roman.

- [ ] **Step 6: Full tests + commit**

```bash
cd /workspace/development/frappe-bench && bench --site dental_opg-test.localhost run-tests --app dental_opg
cd apps/dental_opg
git add frontend/src frontend/tailwind.config.js frontend/components.d.ts dental_opg/public/frontend dental_opg/www/dental_opg.html
git commit -m "Report editor: patient info, remembered signatories, Times New Roman UI; rebuild bundle

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 7: Migrate dev site** — `bench --site dev.localhost migrate` so fixtures/patch/schema apply to the human-used site. Report the active `OPG Tooth Finding` count back.
