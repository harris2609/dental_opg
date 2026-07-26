import copy
import io
from pathlib import Path

import frappe
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches
from docx.text.paragraph import Paragraph
from frappe.utils.file_manager import get_file

from dental_opg.dental_opg_reporting.report_builder import build_report_sections

TEMPLATE_PATH = Path(__file__).parent / "templates" / "opg_report_template.docx"

BULLET_SECTIONS = {"MAXILLARY_ARCH", "MANDIBULAR_ARCH"}

SECTION_HEADINGS = {
	"CONDYLAR_MORPHOLOGY": "CONDYLAR MORPHOLOGY:",
	"STYLOID_PROCESS": "STYLOID PROCESS:",
	"MAXILLARY_SINUS": "MAXILLARY SINUS:",
	"INFERIOR_BORDER_OF_MANDIBLE": "INFERIOR BORDER OF MANDIBLE",
	"MAXILLARY_ARCH": "MAXILLARY ARCH:",
	"MANDIBULAR_ARCH": "MANDIBULAR ARCH:",
	"RADIOLOGIC_IMPRESSION": "RADIOLOGIC IMPRESSION",
}


def build_docx(report) -> bytes:
	"""Fill the clinic's docx template with one OPG Report's data, return the
	resulting .docx file as bytes."""
	doc = Document(str(TEMPLATE_PATH))

	patient = frappe.get_doc("OPG Patient", report.patient) if report.patient else None
	_replace_tokens(doc, _metadata_replacements(report, patient))
	_insert_image(doc, report)
	_fill_sections(doc, report)

	buffer = io.BytesIO()
	doc.save(buffer)
	return buffer.getvalue()


def _metadata_replacements(report, patient) -> dict:
	return {
		"{{patient_name}}": (patient.patient_name if patient else "") or "",
		"{{age}}": str(patient.age) if patient and patient.age else "",
		"{{sex}}": (patient.sex or "")[:1] if patient else "",
		"{{registration_no}}": (patient.registration_no if patient else "") or "",
		"{{report_date}}": frappe.utils.formatdate(report.report_date) if report.report_date else "",
		"{{referred_by}}": report.referred_by or "",
		"{{radiographic_projection}}": report.radiographic_projection or "OPG",
		"{{clinical_diagnosis}}": report.clinical_diagnosis or "",
		"{{reported_by}}": report.reported_by or "",
		"{{verified_by}}": report.verified_by or "",
	}


def _iter_all_paragraphs(doc):
	yield from doc.paragraphs
	for table in doc.tables:
		for row in table.rows:
			for cell in row.cells:
				yield from cell.paragraphs


def _replace_tokens(doc, replacements: dict):
	for p in _iter_all_paragraphs(doc):
		for run in p.runs:
			if run.text in replacements:
				run.text = replacements[run.text]
			else:
				# Handle partial replacements for tokens embedded in text
				text = run.text
				for token, value in replacements.items():
					text = text.replace(token, value)
				run.text = text


def _insert_image(doc, report):
	marker = next((p for p in doc.paragraphs if p.text == "{{OPG_IMAGE}}"), None)
	if marker is None:
		return
	marker.text = ""
	if not report.opg_image:
		return
	_, content = get_file(report.opg_image)
	marker.alignment = 1  # center
	run = marker.add_run()
	run.add_picture(io.BytesIO(content), width=Inches(6))


def _fill_sections(doc, report):
	sections_by_key = {s["name"].replace(" ", "_"): s["lines"] for s in build_report_sections(report)}

	for key, heading_text in SECTION_HEADINGS.items():
		marker_text = "{{FINDINGS:%s}}" % key
		marker = next((p for p in doc.paragraphs if p.text == marker_text), None)
		if marker is None:
			continue

		lines = sections_by_key.get(key)
		if not lines:
			heading = next((p for p in doc.paragraphs if p.text.strip() == heading_text), None)
			if heading is not None:
				heading._p.getparent().remove(heading._p)
			marker._p.getparent().remove(marker._p)
			continue

		style = marker.style
		marker.text = lines[0]
		last = marker
		for line in lines[1:]:
			last = _insert_paragraph_after(last, line, style)
			if key in BULLET_SECTIONS:
				_copy_numbering(marker, last)


def _insert_paragraph_after(reference_paragraph, text, style):
	new_p_elem = OxmlElement("w:p")
	reference_paragraph._p.addnext(new_p_elem)
	new_p = Paragraph(new_p_elem, reference_paragraph._parent)
	new_p.text = text
	new_p.style = style
	return new_p


def _copy_numbering(from_paragraph, to_paragraph):
	from_pPr = from_paragraph._p.pPr
	if from_pPr is None:
		return
	numPr = from_pPr.find(qn("w:numPr"))
	if numPr is None:
		return
	to_pPr = to_paragraph._p.get_or_add_pPr()
	to_pPr.append(copy.deepcopy(numPr))
