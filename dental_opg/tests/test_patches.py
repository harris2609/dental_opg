import frappe
from frappe.tests import IntegrationTestCase

from dental_opg.patches import fix_irt_tooth_number_templates


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
