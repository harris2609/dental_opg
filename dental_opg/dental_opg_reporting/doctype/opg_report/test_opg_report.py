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
