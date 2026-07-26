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

	def test_build_docx_fills_footer_tokens(self):
		"""The footer (Reported by / Verified by) is a separate docx part
		from the body - not reachable via result_doc.paragraphs alone. A
		prior version of this test only checked body paragraphs and missed
		that these tokens were going unfilled."""
		content = build_docx(self.report)
		result_doc = DocxDocument(io.BytesIO(content))
		footer = result_doc.sections[0].footer

		footer_text = "\n".join(p.text for p in footer.paragraphs)
		for table in footer.tables:
			for row in table.rows:
				for cell in row.cells:
					footer_text += "\n" + cell.text

		self.assertIn("Dr. Test Reporter", footer_text)
		self.assertIn("Dr. Test Verifier", footer_text)
		self.assertNotIn("{{", footer_text)
