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

	def test_add_incidental_finding_rejects_client_supplied_patient(self):
		"""patient/reported_by must come from the report, never from caller input -
		the method signature has no patient/reported_by parameter, so an injection
		attempt must fail loudly (TypeError) rather than silently succeed."""
		other_patient = frappe.get_doc(
			doctype="OPG Patient",
			patient_name="Other Patient",
			registration_no=frappe.generate_hash(length=8),
		).insert()

		self.assertRaises(
			TypeError,
			self.report.add_incidental_finding,
			finding_type="Retained root",
			side="Right",
			severity="Mild",
			patient=other_patient.name,
		)

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
