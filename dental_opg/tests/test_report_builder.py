import frappe
from frappe.tests import IntegrationTestCase

from dental_opg.dental_opg_reporting.report_builder import build_report_sections


class TestReportBuilderSectionFindings(IntegrationTestCase):
	def setUp(self):
		self.patient = frappe.get_doc(
			doctype="OPG Patient",
			patient_name="Section Finding Test",
			registration_no=frappe.generate_hash(length=8),
		).insert()
		self.report = frappe.get_doc(doctype="OPG Report", patient=self.patient.name).insert()

	def _standard_finding(self, section, label, template):
		return frappe.get_doc(
			doctype="OPG Standard Finding",
			section_name=section,
			finding_label=label,
			finding_template=template,
			active=1,
		).insert()

	def test_section_finding_renders_known_placeholders(self):
		finding = self._standard_finding(
			"Styloid Process", "Elongated one side", "Appears to be elongated on the {side} side"
		)
		self.report.save_findings(
			section_findings=[
				{"section": "Styloid Process", "finding": finding.name, "is_custom": 0, "side": "Left"}
			],
			tooth_findings=[],
		)
		self.report.reload()

		sections = build_report_sections(self.report)
		styloid = next(s for s in sections if s["name"] == "STYLOID PROCESS")
		self.assertIn("Appears to be elongated on the left side", styloid["lines"])

	def test_section_finding_template_with_stray_braces_does_not_crash_generation(self):
		"""A dentist's free-text custom finding is promoted verbatim into
		finding_template; text like 'approx {2}mm' must not blow up generation
		(str.format_map raises ValueError on positional/malformed fields)."""
		finding = self._standard_finding(
			"Maxillary Sinus", "Opacity measured", "Homogenous opacity approx {2}mm noted { unclosed"
		)
		self.report.save_findings(
			section_findings=[{"section": "Maxillary Sinus", "finding": finding.name, "is_custom": 0}],
			tooth_findings=[],
		)
		self.report.reload()

		sections = build_report_sections(self.report)
		sinus = next(s for s in sections if s["name"] == "MAXILLARY SINUS")
		self.assertTrue(any("Homogenous opacity approx" in line for line in sinus["lines"]))

	def test_selected_section_finding_that_renders_empty_falls_back_to_label(self):
		"""A selected (non-custom) finding must never silently vanish from the
		report. If its template renders to nothing (e.g. a promoted template
		that is only an unfilled placeholder), fall back to the finding label."""
		finding = self._standard_finding("Maxillary Arch", "Crowding noted", "{side}")
		self.report.save_findings(
			section_findings=[{"section": "Maxillary Arch", "finding": finding.name, "is_custom": 0}],
			tooth_findings=[],
		)
		self.report.reload()

		sections = build_report_sections(self.report)
		maxillary = next(s for s in sections if s["name"] == "MAXILLARY ARCH")
		self.assertIn("Crowding noted", maxillary["lines"])

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

	def test_empty_tooth_number_leaves_no_dangling_irt(self):
		finding = self._standard_finding("Maxillary Arch", "Partial", "Partial complement noted with missing irt {tooth_number}")
		self.report.save_findings(
			section_findings=[{"section": "Maxillary Arch", "finding": finding.name, "is_custom": 0, "tooth_number": ""}],
			tooth_findings=[],
		)
		self.report.reload()

		arch = next(s for s in build_report_sections(self.report) if s["name"] == "MAXILLARY ARCH")
		self.assertEqual(arch["lines"], ["Partial complement noted with missing"])


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
				{
					"tooth_number": "16",
					"arch": "Maxillary",
					"finding_name": "Dental Caries",
					"description": "desc A",
				},
				{
					"tooth_number": "17",
					"arch": "Maxillary",
					"finding_name": "Dental Caries",
					"description": "desc A",
				},
				{
					"tooth_number": "26",
					"arch": "Maxillary",
					"finding_name": "Dental Caries",
					"description": "desc B edited",
				},
			],
		)
		self.report.reload()

		sections = build_report_sections(self.report)
		maxillary = next(s for s in sections if s["name"] == "MAXILLARY ARCH")

		self.assertIn("irt 16, 17 - desc A", maxillary["lines"])
		self.assertIn("irt 26 - desc B edited", maxillary["lines"])

	def test_radiologic_impression_includes_tooth_numbers_and_splits_by_description(self):
		self.report.save_findings(
			section_findings=[],
			tooth_findings=[
				{
					"tooth_number": "16",
					"arch": "Maxillary",
					"finding_name": "Dental Caries",
					"description": "desc A",
				},
				{
					"tooth_number": "17",
					"arch": "Maxillary",
					"finding_name": "Dental Caries",
					"description": "desc A",
				},
				{
					"tooth_number": "26",
					"arch": "Maxillary",
					"finding_name": "Dental Caries",
					"description": "desc B edited",
				},
				{
					"tooth_number": "46",
					"arch": "Mandibular",
					"finding_name": "Root Stumps",
					"description": "desc C",
				},
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
				{
					"tooth_number": "16",
					"arch": "Maxillary",
					"finding_name": "Dental Caries",
					"description": "same text",
				},
				{
					"tooth_number": "46",
					"arch": "Mandibular",
					"finding_name": "Dental Caries",
					"description": "same text",
				},
			],
		)
		self.report.reload()

		sections = build_report_sections(self.report)
		impression = next(s for s in sections if s["name"] == "RADIOLOGIC IMPRESSION")

		self.assertEqual(impression["lines"].count("Dental Caries irt 16, 46"), 1)
