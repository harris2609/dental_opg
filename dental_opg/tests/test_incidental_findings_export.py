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
