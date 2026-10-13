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
				{
					"section": "Styloid Process",
					"is_custom": 1,
					"custom_text": "Unusual elongation noted bilaterally",
				},
			],
			tooth_findings=[],
		)

		matches = frappe.get_all(
			"OPG Standard Finding",
			filters={
				"section_name": "Styloid Process",
				"finding_label": "Unusual elongation noted bilaterally",
			},
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
			filters={
				"finding_name": "Unusual radiopacity",
				"description_template": "A distinct radiopaque focus noted near the apex",
			},
			fields=["name", "active"],
		)
		self.assertEqual(len(matches), 1)
		self.assertEqual(matches[0].active, 1)

	def test_save_findings_clears_tooth_finding_link_to_missing_master(self):
		"""A tooth finding whose `finding` master was deleted must not make the
		whole report unsaveable - drop the stale link, keep the row and its
		finding_name/description snapshot."""
		self.report.save_findings(
			section_findings=[],
			tooth_findings=[
				{
					"tooth_number": "36",
					"arch": "Mandibular",
					"finding": "master-that-was-deleted",
					"finding_name": "Mobility",
					"description": "Grade II mobility noted",
				},
			],
		)
		self.report.reload()

		self.assertEqual(len(self.report.tooth_findings), 1)
		self.assertFalse(self.report.tooth_findings[0].finding)
		self.assertEqual(self.report.tooth_findings[0].finding_name, "Mobility")

	def test_save_findings_drops_tooth_row_with_dead_link_and_no_snapshot(self):
		"""A tooth row with a dangling `finding` and no finding_name/description
		snapshot is not a finding - drop it instead of failing the whole save
		on mandatory fields."""
		self.report.save_findings(
			section_findings=[],
			tooth_findings=[
				{"tooth_number": "36", "arch": "Mandibular", "finding": "slug-from-old-schema"},
				{
					"tooth_number": "16",
					"arch": "Maxillary",
					"finding_name": "Dental Caries",
					"description": "keep me",
				},
			],
		)
		self.report.reload()

		self.assertEqual(len(self.report.tooth_findings), 1)
		self.assertEqual(self.report.tooth_findings[0].tooth_number, "16")

	def test_save_findings_clears_section_finding_link_to_missing_master(self):
		self.report.save_findings(
			section_findings=[
				{"section": "Styloid Process", "finding": "master-that-was-deleted", "is_custom": 0},
			],
			tooth_findings=[],
		)
		self.report.reload()

		self.assertEqual(len(self.report.section_findings), 1)
		self.assertFalse(self.report.section_findings[0].finding)

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
