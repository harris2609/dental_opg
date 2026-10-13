import re

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


# Finding templates only ever use these three placeholders. Substitute them
# explicitly rather than via str.format_map, which raises ValueError on any
# stray "{"/"}" or positional field - and templates can contain arbitrary
# dentist-typed text (custom findings are promoted verbatim into a template),
# so a single "{" must not be allowed to abort the whole report.
_PLACEHOLDER = re.compile(r"\{(side|tooth_number|level)\}")


def _render_template(template, **kwargs):
	rendered = _PLACEHOLDER.sub(lambda m: str(kwargs.get(m.group(1), "")), template or "")
	return " ".join(rendered.split())


def _standard_finding_masters(report):
	names = {row.finding for row in report.section_findings if row.finding}
	if not names:
		return {}
	return {
		row.name: row
		for row in frappe.get_all(
			"OPG Standard Finding",
			filters={"name": ["in", list(names)]},
			fields=["name", "finding_template", "finding_label", "impression_label"],
		)
	}


def _section_finding_lines(report, masters):
	lines_by_section = {section: [] for section in SECTION_ORDER}
	for row in report.section_findings:
		if row.is_custom or not row.finding:
			text = (row.custom_text or "").strip()
		elif (row.edited_text or "").strip():
			# Dentist individualized this finding for this patient only.
			text = row.edited_text.strip()
		else:
			master = masters.get(row.finding)
			text = _render_template(
				(master and master.finding_template) or "",
				side=SIDE_PHRASES.get(row.side, row.side or ""),
				tooth_number=row.tooth_number or "",
				level=(row.level or "").lower(),
			)
			# A finding the dentist explicitly selected must never silently
			# vanish - fall back to its label if the template rendered empty.
			if not text and master:
				text = (master.finding_label or "").strip()
		if text and row.section in lines_by_section:
			lines_by_section[row.section].append(text)
	return lines_by_section


def _impression_label_lines(report, masters):
	"""One "{impression_label} irt {teeth}" line per distinct label, teeth from
	every row of that label merged in first-seen order across both arches - so
	"Partial complement" picked in each arch yields one PARTIALLY EDENTULOUS
	line. Rows without tooth numbers contribute nothing."""
	teeth_by_label = {}
	for row in report.section_findings:
		master = masters.get(row.finding) if row.finding and not row.is_custom else None
		label = ((master and master.impression_label) or "").strip()
		teeth = [t.strip() for t in (row.tooth_number or "").split(",") if t.strip()]
		if not (label and teeth):
			continue
		bucket = teeth_by_label.setdefault(label, [])
		bucket.extend(t for t in teeth if t not in bucket)
	return [f"{label} irt {', '.join(teeth)}" for label, teeth in teeth_by_label.items()]


def _tooth_finding_lines(report):
	"""One line per distinct (arch section, finding_name, description) group,
	tooth numbers merged in first-seen order - so selecting the same finding
	with the same (possibly edited) description on multiple teeth produces one
	combined "irt 16, 17 - ..." line instead of a separate line per tooth. If
	a dentist edits one tooth's description independently afterward, that
	entry naturally falls out of the group (its text no longer matches) and
	prints as its own line - no explicit "linked group" state to maintain."""
	groups = {}
	order = []
	for row in report.tooth_findings:
		section = ARCH_TO_SECTION.get(row.arch)
		if not section:
			continue
		key = (section, row.finding_name, row.description)
		if key not in groups:
			groups[key] = []
			order.append(key)
		groups[key].append(row.tooth_number)

	lines_by_arch_section = {"Maxillary Arch": [], "Mandibular Arch": []}
	for key in order:
		section, finding_name, description = key
		if not (finding_name and description):
			continue
		tooth_numbers = ", ".join(groups[key])
		lines_by_arch_section[section].append(f"irt {tooth_numbers} - {description}")
	return lines_by_arch_section


def _impression_finding_lines(report):
	"""One "{finding_name} irt {tooth_numbers}" line per distinct (finding_name,
	description) pair, tooth numbers merged in first-seen order - across BOTH
	arches combined, since Radiologic Impression is one unified section with
	no arch boundary (unlike _tooth_finding_lines, which keeps the two arch
	sections separate). Two teeth sharing an identical finding name but a
	genuinely different (edited) description produce two separate lines,
	mirroring how the arch section itself already treats them."""
	groups = {}
	order = []
	for row in report.tooth_findings:
		if not (row.finding_name and row.description):
			continue
		key = (row.finding_name, row.description)
		if key not in groups:
			groups[key] = []
			order.append(key)
		groups[key].append(row.tooth_number)

	lines = []
	for key in order:
		finding_name, _ = key
		tooth_numbers = ", ".join(groups[key])
		lines.append(f"{finding_name} irt {tooth_numbers}")
	return lines


def build_report_sections(report):
	"""Structured (section name, lines) pairs in fixed order, skipping empty
	sections. Used by the print format so each section heading can be styled
	(bold + underline) separately from its plain finding lines."""
	masters = _standard_finding_masters(report)
	section_lines = _section_finding_lines(report, masters)
	tooth_lines = _tooth_finding_lines(report)
	for section, extra_lines in tooth_lines.items():
		section_lines[section].extend(extra_lines)

	section_lines["Radiologic Impression"].extend(_impression_label_lines(report, masters))
	section_lines["Radiologic Impression"].extend(_impression_finding_lines(report))

	sections = []
	for section in SECTION_ORDER:
		lines = section_lines.get(section) or []
		if lines:
			sections.append({"name": section.upper(), "lines": lines})
	return sections


def build_report_text(report):
	"""Assemble deterministic, template-based narrative text from structured findings on an OPG Report doc."""
	blocks = [
		f"{section['name']}:\n" + "\n".join(section["lines"]) for section in build_report_sections(report)
	]
	return "\n\n".join(blocks)
