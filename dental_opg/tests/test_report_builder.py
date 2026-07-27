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
