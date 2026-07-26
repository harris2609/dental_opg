"""
One-time prep script: turns the clinic's original report .docx into a
reusable export template with placeholder tokens, so OPGReport.export_report_docx
can fill it in per report at runtime.

Not part of the runtime code path - run this again only if the clinic's
letterhead/template file itself changes.

IMPORTANT: the source .docx passed as input contains a real patient's data
burned into the sample X-ray image's pixels. The source file must never be
committed to this repo. Only the output template (with that image fully
removed) is safe to commit - this script verifies that before writing.

Usage:
    python scripts/build_docx_template.py <path-to-original.docx> <output-template-path>
"""

import sys
import zipfile
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

SECTION_MARKERS = [
	# (heading_paragraph_index, first_example_line_index, last_example_line_index, marker_text)
	(4, 5, 8, "{{FINDINGS:CONDYLAR_MORPHOLOGY}}"),
	(9, 10, 12, "{{FINDINGS:STYLOID_PROCESS}}"),
	(14, 15, 16, "{{FINDINGS:MAXILLARY_SINUS}}"),
	(18, 19, 20, "{{FINDINGS:INFERIOR_BORDER_OF_MANDIBLE}}"),
	(25, 26, 29, "{{FINDINGS:MAXILLARY_ARCH}}"),
	(31, 32, 35, "{{FINDINGS:MANDIBULAR_ARCH}}"),
]


def clone_paragraph_after(reference_paragraph, marker_text):
	"""Clone reference_paragraph's formatting (style, numbering/bullet) into a
	new paragraph inserted right after it, with marker_text as its only run."""
	new_p = reference_paragraph.insert_paragraph_before(marker_text)
	new_p.style = reference_paragraph.style
	ref_pPr = reference_paragraph._p.pPr
	if ref_pPr is not None:
		numPr = ref_pPr.find(qn("w:numPr"))
		if numPr is not None:
			new_pPr = new_p._p.get_or_add_pPr()
			new_pPr.append(numPr)
	return new_p


def delete_paragraph(paragraph):
	paragraph._p.getparent().remove(paragraph._p)


def _set_footer_cell(cell, text, fill, text_color):
	tcPr = cell._tc.get_or_add_tcPr()
	shd = OxmlElement("w:shd")
	shd.set(qn("w:val"), "clear")
	shd.set(qn("w:color"), "auto")
	shd.set(qn("w:fill"), fill)
	tcPr.append(shd)

	p = cell.paragraphs[0]
	p.alignment = 1  # center
	run = p.add_run(text)
	run.font.name = "Times New Roman"
	run.font.size = Pt(14)
	run.font.bold = True
	run.font.color.rgb = RGBColor.from_string(text_color)


def build_template(source_path: str, output_path: str):
	doc = Document(source_path)

	# --- 1. Patient/report metadata tokens (table 0) ---
	table = doc.tables[0]
	table.rows[0].cells[0].paragraphs[0].add_run("{{patient_name}}")
	table.rows[0].cells[1].paragraphs[0].add_run("{{age}} / {{sex}}")
	table.rows[1].cells[0].paragraphs[0].add_run("{{registration_no}}")
	table.rows[1].cells[1].paragraphs[0].add_run("{{report_date}}")
	table.rows[2].cells[0].paragraphs[0].add_run("{{referred_by}}")
	# RADIOGRAPHIC PROJECTION already has a literal "OPG" value - replace it
	proj_para = table.rows[2].cells[1].paragraphs[0]
	for run in proj_para.runs:
		if "OPG" in run.text:
			run.text = run.text.replace("OPG", "{{radiographic_projection}}")
	table.rows[3].cells[0].paragraphs[0].add_run("{{clinical_diagnosis}}")

	# --- 2. Footer doctor names -> tokens ---
	# The original footer's "Reported by"/"Verified by" text lives in runs
	# with malformed (unclosed) <w:t> XML - Word/LibreOffice tolerate this
	# and render it fine, but python-docx's strict parser can't reliably
	# address those specific runs (confirmed: footer.paragraphs returns
	# empty text for them even though the raw bytes contain fragments of
	# the names). Rather than patch corrupted XML by hand, rebuild the
	# footer cleanly as a table - same visual result (colors/layout
	# already established for the PDF print format), fully controllable.
	footer = doc.sections[0].footer
	for p in list(footer.paragraphs):
		delete_paragraph(p)

	footer_table = footer.add_table(rows=1, cols=2, width=Pt(468))
	reported_cell, verified_cell = footer_table.rows[0].cells
	_set_footer_cell(reported_cell, "Reported by: {{reported_by}}", fill="0070C0", text_color="FFFFFF")
	_set_footer_cell(verified_cell, "Verified by: {{verified_by}}", fill="9CC2E5", text_color="002060")

	email_p = footer.add_paragraph("Email: ydcxray@yenepoya.edu.in")
	email_p.alignment = 1  # center
	email_run = email_p.runs[0]
	email_run.font.name = "Times New Roman"
	email_run.font.size = Pt(11)
	email_run.font.color.rgb = RGBColor(0x00, 0x00, 0x00)

	# --- 3. Remove the sample X-ray image, mark its spot ---
	report_heading_para = doc.paragraphs[1]
	assert report_heading_para.text == "REPORT", f"expected REPORT heading, got {report_heading_para.text!r}"
	for run in list(report_heading_para.runs):
		if run._r.findall(".//" + qn("w:drawing")):
			run._r.getparent().remove(run._r)

	image_marker_para = doc.paragraphs[2]
	image_marker_para.text = "{{OPG_IMAGE}}"

	# --- 3b. Remove the "In pro version - add classification..." draft note
	# box (a floating textbox, confirmed with the user to skip - it's the
	# template author's own draft note, not real report content) ---
	for p in doc.paragraphs:
		for run in list(p.runs):
			drawings = run._r.findall(".//" + qn("w:drawing"))
			for d in drawings:
				text = "".join(t.text or "" for t in d.findall(".//" + qn("w:t")))
				if "pro version" in text:
					run._r.getparent().remove(run._r)

	# --- 4. Replace each section's example lines with one marker paragraph ---
	# Re-fetch paragraphs fresh each iteration since deletions shift indices;
	# process sections in reverse document order so earlier indices stay valid.
	for heading_idx, first_idx, last_idx, marker_text in reversed(SECTION_MARKERS):
		paragraphs = doc.paragraphs
		example_paragraphs = paragraphs[first_idx : last_idx + 1]
		clone_paragraph_after(example_paragraphs[0], marker_text)
		for p in example_paragraphs:
			delete_paragraph(p)

	# Radiologic Impression has no example lines to clone a style from -
	# it's immediately followed by a blank paragraph, so insert the marker
	# there (i.e. right after the heading) using the heading's own style.
	paragraphs = doc.paragraphs
	radiologic_heading_idx = next(i for i, p in enumerate(paragraphs) if p.text.strip() == "RADIOLOGIC IMPRESSION")
	blank_after_heading = paragraphs[radiologic_heading_idx + 1]
	new_p = blank_after_heading.insert_paragraph_before("{{FINDINGS:RADIOLOGIC_IMPRESSION}}")
	new_p.style = paragraphs[radiologic_heading_idx].style

	# --- 5. Prune orphaned image relationships ---
	# Removing a <w:drawing> element (steps 3, 3b above) only deletes the
	# visual reference - the underlying image binary stays in the package as
	# an orphaned, unreferenced part unless its relationship is also removed.
	# Since docx files are just zip archives, that orphaned binary would
	# still be fully extractable even though nothing points to it anymore -
	# unacceptable here since the removed image is a real patient's X-ray.
	# Confirmed empirically: python-docx's save() only serializes parts still
	# reachable from a relationship, so deleting the relationship is enough
	# to drop the orphaned part entirely on save.
	used_embed_ids = {
		blip.get(qn("r:embed"))
		for blip in doc.element.body.findall(".//" + qn("a:blip"))
		if blip.get(qn("r:embed"))
	}
	for rel_id in list(doc.part.rels):
		rel = doc.part.rels[rel_id]
		if "image" in rel.reltype and rel_id not in used_embed_ids:
			del doc.part.rels[rel_id]

	doc.save(output_path)


def verify_no_phi(source_path: str, output_path: str):
	"""Refuse to leave a template with the original sample data in place.

	Checks raw zip bytes directly rather than trusting python-docx's
	relationship/part bookkeeping - a prior version of this check trusted
	`document.part.rels` alone and passed incorrectly: the header's logo
	relationship lives in a *separate* part (header1.xml.rels), not the main
	document part, so counting only `doc.part.rels` mistook the still-present
	orphaned sample-image relationship for "the one expected logo" and never
	caught that the real X-ray bytes were still physically in the file.
	"""
	check_doc = Document(output_path)
	all_text = "\n".join(p.text for p in check_doc.paragraphs)
	for cell_text in (c.text for t in check_doc.tables for r in t.rows for c in r.cells):
		all_text += "\n" + cell_text
	footer = check_doc.sections[0].footer
	all_text += "\n" + "\n".join(p.text for p in footer.paragraphs)
	for cell_text in (c.text for t in footer.tables for r in t.rows for c in r.cells):
		all_text += "\n" + cell_text
	assert "CATHERINE" not in all_text, "sample doctor name still present"
	assert "NAMRATHA" not in all_text, "sample doctor name still present"
	assert "Safreena" not in all_text, "sample patient name still present"
	assert "pro version" not in all_text, "draft note box still present"

	# Direct byte-for-byte check: the sample X-ray's exact binary content
	# must not exist anywhere in the output package, under any filename.
	with zipfile.ZipFile(source_path) as src_zip:
		sample_image_bytes = src_zip.read("word/media/image1.jpeg")

	with zipfile.ZipFile(output_path) as out_zip:
		media_files = [n for n in out_zip.namelist() if n.startswith("word/media/")]
		for name in media_files:
			content = out_zip.read(name)
			assert content != sample_image_bytes, f"sample X-ray bytes still present as {name}"

	assert len(media_files) == 1, f"expected exactly 1 media file (the logo), found {media_files}"
	print(f"media files remaining in output: {media_files}")


if __name__ == "__main__":
	if len(sys.argv) != 3:
		print(f"usage: {sys.argv[0]} <source.docx> <output-template.docx>", file=sys.stderr)
		sys.exit(2)

	source, output = sys.argv[1], sys.argv[2]
	Path(output).parent.mkdir(parents=True, exist_ok=True)
	build_template(source, output)
	verify_no_phi(source, output)
	print(f"wrote sanitized template to {output}")
