import frappe
from frappe.tests import IntegrationTestCase


class TestOPGReportPrintFormat(IntegrationTestCase):
	def test_finding_text_is_escaped_and_line_breaks_kept(self):
		patient = frappe.get_doc(
			doctype="OPG Patient",
			patient_name="Print Escape Test",
			registration_no=frappe.generate_hash(length=8),
		).insert()
		report = frappe.get_doc(doctype="OPG Report", patient=patient.name).insert()
		report.save_findings(
			section_findings=[
				{
					"section": "Styloid Process",
					"is_custom": 1,
					"custom_text": "Line one <i>x</i>\nLine two",
				}
			],
			tooth_findings=[],
		)

		html = frappe.get_print("OPG Report", report.name, print_format="OPG Report")

		self.assertIn("Line one &lt;i&gt;x&lt;/i&gt;<br>Line two", html)
