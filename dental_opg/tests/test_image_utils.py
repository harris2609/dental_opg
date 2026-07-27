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

	def test_image_with_no_annotations_returns_same_pixels_as_jpeg(self):
		"""Bytes aren't expected to be identical - the function always
		re-encodes to JPEG (see test_png_source_with_no_annotations_is_served_as_jpeg
		for why) - but the pixel content must be unchanged."""
		original_bytes = _make_test_jpeg_bytes()
		self._attach_image(original_bytes)

		result = get_annotated_image_bytes(self.report)
		result_image = Image.open(io.BytesIO(result))
		self.assertEqual(result_image.format, "JPEG")
		self.assertEqual(result_image.convert("RGB").getpixel((50, 30)), (200, 200, 200))

	def test_png_source_with_no_annotations_is_served_as_jpeg(self):
		"""The print endpoint hardcodes content_type=image/jpeg and a .jpg
		filename - if the source upload was a PNG and this function just
		passed the original bytes through untouched, wkhtmltopdf would
		receive PNG bytes mislabeled as JPEG."""
		buffer = io.BytesIO()
		Image.new("RGB", (100, 60), color=(200, 200, 200)).save(buffer, format="PNG")
		png_bytes = buffer.getvalue()
		self._attach_image(png_bytes, file_name="test_opg.png")

		result = get_annotated_image_bytes(self.report)
		result_image = Image.open(io.BytesIO(result))
		self.assertEqual(result_image.format, "JPEG")

	def test_image_with_annotations_differs_from_original(self):
		"""Asserting the raw bytes differ isn't enough - re-encoding as JPEG at
		a different quality setting alone guarantees a byte difference even if
		every _draw_* function were a silent no-op. Check the actual pixel
		color at the Point annotation's known location instead, so this test
		would genuinely fail if drawing stopped happening."""
		original_bytes = _make_test_jpeg_bytes()
		self._attach_image(original_bytes)
		self.report.save_annotations(
			annotations=[{"annotation_type": "Point", "x": 0.5, "y": 0.5, "color": "#ff0000"}]
		)
		self.report.reload()

		result = get_annotated_image_bytes(self.report)
		annotated_image = Image.open(io.BytesIO(result)).convert("RGB")

		# center of the 100x60 test image, where the Point annotation was placed
		center_pixel = annotated_image.getpixel((50, 30))
		self.assertGreater(center_pixel[0], 150, f"expected red-dominant pixel at center, got {center_pixel}")
		self.assertLess(center_pixel[1], 100, f"expected red-dominant pixel at center, got {center_pixel}")
		self.assertLess(center_pixel[2], 100, f"expected red-dominant pixel at center, got {center_pixel}")

		# a corner far from the annotation should still be close to the
		# original gray (200, 200, 200), confirming only the annotated area changed
		corner_pixel = annotated_image.getpixel((2, 2))
		self.assertGreater(corner_pixel[0], 150)
		self.assertGreater(corner_pixel[1], 150)
		self.assertGreater(corner_pixel[2], 150)

	def _attach_image(self, content, file_name="test_opg.jpg"):
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"attached_to_doctype": "OPG Report",
				"attached_to_name": self.report.name,
				"attached_to_field": "opg_image",
				"file_name": file_name,
				"content": content,
				"is_private": 0,
			}
		).insert()
		self.report.opg_image = file_doc.file_url
		self.report.save()
