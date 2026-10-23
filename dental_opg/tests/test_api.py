import frappe
from frappe.tests import IntegrationTestCase

from dental_opg.api import get_signatory_suggestions


class TestSignatorySuggestions(IntegrationTestCase):
	def _report(self, reported_by, verified_by):
		patient = frappe.get_doc(
			doctype="OPG Patient", patient_name="Signatory Test", registration_no=frappe.generate_hash(length=8)
		).insert()
		return frappe.get_doc(
			doctype="OPG Report", patient=patient.name, reported_by=reported_by, verified_by=verified_by
		).insert()

	def test_returns_distinct_names_newest_first(self):
		older = frappe.generate_hash(length=6)
		newer = frappe.generate_hash(length=6)
		self._report(f"Dr {older}", f"Dr V{older}")
		self._report(f"Dr {older}", "")
		self._report(f"Dr {newer}", f"Dr V{newer}")

		result = get_signatory_suggestions()

		reported = result["reported_by"]
		self.assertEqual(reported.count(f"Dr {older}"), 1)
		self.assertLess(reported.index(f"Dr {newer}"), reported.index(f"Dr {older}"))
		self.assertIn(f"Dr V{older}", result["verified_by"])
		self.assertNotIn("", result["verified_by"])
		self.assertLessEqual(len(reported), 50)

	def test_names_differing_only_in_surrounding_spaces_are_one_suggestion(self):
		name = f"Dr {frappe.generate_hash(length=6)}"
		self._report(f"  {name} ", "")
		self._report(name, "")

		reported = get_signatory_suggestions()["reported_by"]

		self.assertEqual(reported.count(name), 1)
		self.assertNotIn(f"  {name} ", reported)
