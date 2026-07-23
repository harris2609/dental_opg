import frappe

SECTION_ORDER = [
	"Condylar Morphology",
	"Styloid Process",
	"Maxillary Sinus",
	"Inferior Border of Mandible",
	"Maxillary Arch",
	"Mandibular Arch",
	"Radiologic Impression",
]

ARCH_TO_SECTION = {
	"Maxillary": "Maxillary Arch",
	"Mandibular": "Mandibular Arch",
}

SIDE_PHRASES = {
	"Left": "left",
	"Right": "right",
	"Bilateral": "bilateral",
}


class _SafeDict(dict):
	def __missing__(self, key):
		return ""


def _render_template(template, **kwargs):
	return " ".join(template.format_map(_SafeDict(**kwargs)).split())


def _section_finding_lines(report):
	standard_finding_names = {row.finding for row in report.section_findings if row.finding}
	templates = {}
	if standard_finding_names:
		templates = {
			row.name: row.finding_template
			for row in frappe.get_all(
				"OPG Standard Finding",
				filters={"name": ["in", list(standard_finding_names)]},
				fields=["name", "finding_template"],
			)
		}

	lines_by_section = {section: [] for section in SECTION_ORDER}
	for row in report.section_findings:
		if row.is_custom or not row.finding:
			text = (row.custom_text or "").strip()
		else:
			template = templates.get(row.finding, "")
			text = _render_template(
				template,
				side=SIDE_PHRASES.get(row.side, row.side or ""),
				tooth_number=row.tooth_number or "",
				level=(row.level or "").lower(),
			)
		if text and row.section in lines_by_section:
			lines_by_section[row.section].append(text)
	return lines_by_section


def _tooth_finding_lines(report):
	tooth_finding_names = {row.finding for row in report.tooth_findings if row.finding}
	templates = {}
	if tooth_finding_names:
		templates = {
			row.name: row.finding_template
			for row in frappe.get_all(
				"OPG Tooth Finding",
				filters={"name": ["in", list(tooth_finding_names)]},
				fields=["name", "finding_template"],
			)
		}

	lines_by_arch_section = {"Maxillary Arch": [], "Mandibular Arch": []}
	for row in report.tooth_findings:
		if row.is_custom or not row.finding:
			text = (row.custom_text or "").strip()
			if text:
				text = f"Tooth {row.tooth_number}: {text}"
		else:
			template = templates.get(row.finding, "")
			text = _render_template(template, tooth_number=row.tooth_number or "")
		section = ARCH_TO_SECTION.get(row.arch)
		if text and section:
			lines_by_arch_section[section].append(text)
	return lines_by_arch_section


def build_report_sections(report):
	"""Structured (section name, lines) pairs in fixed order, skipping empty
	sections. Used by the print format so each section heading can be styled
	(bold + underline) separately from its plain finding lines."""
	section_lines = _section_finding_lines(report)
	tooth_lines = _tooth_finding_lines(report)
	for section, extra_lines in tooth_lines.items():
		section_lines[section].extend(extra_lines)

	sections = []
	for section in SECTION_ORDER:
		lines = section_lines.get(section) or []
		if lines:
			sections.append({"name": section.upper(), "lines": lines})
	return sections


def build_report_text(report):
	"""Assemble deterministic, template-based narrative text from structured findings on an OPG Report doc."""
	blocks = [f"{section['name']}:\n" + "\n".join(section["lines"]) for section in build_report_sections(report)]
	return "\n\n".join(blocks)
