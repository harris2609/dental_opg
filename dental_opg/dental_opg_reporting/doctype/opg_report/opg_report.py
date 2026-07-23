import frappe
from frappe.model.document import Document

from dental_opg.dental_opg_reporting.report_builder import build_report_text


class OPGReport(Document):
	def validate(self):
		for row in self.tooth_findings:
			if not row.arch:
				row.arch = "Maxillary" if row.tooth_number and row.tooth_number.strip()[:1] in "12" else "Mandibular"

	@frappe.whitelist(methods=["POST"])
	def save_findings(self, section_findings: list | None = None, tooth_findings: list | None = None):
		if section_findings is not None:
			self.set("section_findings", section_findings)
		if tooth_findings is not None:
			self.set("tooth_findings", tooth_findings)
		self.save()
		return {"name": self.name}

	@frappe.whitelist(methods=["POST"])
	def save_annotations(self, annotations: list):
		self.set("annotations", annotations)
		self.save()
		return {"name": self.name}

	@frappe.whitelist(methods=["POST"])
	def generate_report(self):
		self.generated_report_text = build_report_text(self)
		self.save()
		return self.generated_report_text
