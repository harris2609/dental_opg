import frappe
from frappe.tests import IntegrationTestCase

from dental_opg.patches import fix_irt_tooth_number_templates, fix_tooth_finding_arch


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


class TestFixToothFindingArch(IntegrationTestCase):
	def test_backfills_arch_from_tooth_number(self):
		patient = frappe.get_doc(
			doctype="OPG Patient", patient_name="Arch Backfill", registration_no=frappe.generate_hash(length=8)
		).insert()
		report = frappe.get_doc(
			doctype="OPG Report",
			patient=patient.name,
			tooth_findings=[
				{"tooth_number": "46", "finding_name": "Caries", "description": "Caries"},
				{"tooth_number": "75", "finding_name": "Caries", "description": "Caries"},
				{"tooth_number": "16", "finding_name": "Caries", "description": "Caries"},
			],
		).insert()
		# Simulate rows stored before validate derived the arch.
		for row in report.tooth_findings:
			frappe.db.set_value("OPG Tooth Finding Entry", row.name, "arch", "Maxillary")

		fix_tooth_finding_arch.execute()

		arches = dict(
			frappe.get_all(
				"OPG Tooth Finding Entry",
				filters={"parent": report.name},
				fields=["tooth_number", "arch"],
				as_list=True,
			)
		)
		self.assertEqual(arches, {"46": "Mandibular", "75": "Mandibular", "16": "Maxillary"})
