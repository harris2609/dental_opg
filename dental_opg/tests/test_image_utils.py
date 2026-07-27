import io

import frappe
from frappe.tests import IntegrationTestCase
from PIL import Image

from dental_opg.dental_opg_reporting.image_utils import get_annotated_image_bytes


def _make_test_jpeg_bytes():
	buffer = io.BytesIO()
	Image.new("RGB", (100, 60), color=(200, 200, 200)).save(buffer, format="JPEG")
	return buffer.getvalue()


class TestImageUtils(IntegrationTestCase):
	def setUp(self):
		self.patient = frappe.get_doc(
			doctype="OPG Patient",
			patient_name="Image Utils Test",
			registration_no=frappe.generate_hash(length=8),
		).insert()
		self.report = frappe.get_doc(
			doctype="OPG Report",
			patient=self.patient.name,
		).insert()

	def test_no_image_returns_none(self):
		self.assertIsNone(get_annotated_image_bytes(self.report))

	def test_image_with_no_annotations_returns_original_bytes(self):
		original_bytes = _make_test_jpeg_bytes()
		self._attach_image(original_bytes)

		result = get_annotated_image_bytes(self.report)
		self.assertEqual(result, original_bytes)

	def test_image_with_annotations_differs_from_original(self):
		original_bytes = _make_test_jpeg_bytes()
		self._attach_image(original_bytes)
		self.report.save_annotations(
			annotations=[{"annotation_type": "Point", "x": 0.5, "y": 0.5, "color": "#ff0000"}]
		)
		self.report.reload()

		result = get_annotated_image_bytes(self.report)
		self.assertNotEqual(result, original_bytes)

	def _attach_image(self, content):
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"attached_to_doctype": "OPG Report",
				"attached_to_name": self.report.name,
				"attached_to_field": "opg_image",
				"file_name": "test_opg.jpg",
				"content": content,
				"is_private": 0,
			}
		).insert()
		self.report.opg_image = file_doc.file_url
		self.report.save()
