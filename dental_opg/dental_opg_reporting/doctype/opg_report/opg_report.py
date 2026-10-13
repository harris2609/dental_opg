import frappe
from frappe.model.document import Document

from dental_opg.dental_opg_reporting.report_builder import build_report_text


def _clear_missing_links(rows, master_doctype):
	"""Null every `finding` on `rows` that does not resolve to an existing
	`master_doctype` record. Shared by the save path and the data patch."""
	names = {row.finding for row in rows if row.finding}
	if not names:
		return
	live = set(frappe.get_all(master_doctype, filters={"name": ["in", list(names)]}, pluck="name"))
	for row in rows:
		if row.finding and row.finding not in live:
			row.finding = None


# FDI quadrants: 1, 2 permanent upper; 5, 6 deciduous upper.
MAXILLARY_QUADRANTS = ("1", "2", "5", "6")


class OPGReport(Document):
	def validate(self):
		# The tooth number is the source of truth for the arch. `arch` is a
		# Select with no blank option, so it always arrives pre-filled with
		# "Maxillary" - an "only if empty" check would never fire.
		for row in self.tooth_findings:
			quadrant = (row.tooth_number or "").strip()[:1]
			if quadrant:
				row.arch = "Maxillary" if quadrant in MAXILLARY_QUADRANTS else "Mandibular"

	@frappe.whitelist(methods=["POST"])
	def save_findings(self, section_findings: list | None = None, tooth_findings: list | None = None):
		if section_findings is not None:
			self.set("section_findings", section_findings)
		if tooth_findings is not None:
			self.set("tooth_findings", tooth_findings)
		self._drop_missing_finding_links()
		self._promote_custom_findings_to_master_lists()
		self.save()
		return {"name": self.name}

	def _drop_missing_finding_links(self):
		"""Clear any `finding` link pointing at a master that no longer exists,
		and discard tooth rows left with nothing usable.

		A deleted master would otherwise make `_validate_links` reject every
		save of the whole report. A row that keeps its finding_name/description
		snapshot survives (that snapshot is what generation reads); a tooth row
		with neither a live link nor a snapshot is not a finding at all and is
		dropped rather than left to fail mandatory-field validation."""
		_clear_missing_links(self.section_findings, "OPG Standard Finding")
		_clear_missing_links(self.tooth_findings, "OPG Tooth Finding")

		usable = [row for row in self.tooth_findings if row.finding or (row.finding_name and row.description)]
		if len(usable) != len(self.tooth_findings):
			self.set("tooth_findings", usable)

	def _promote_custom_findings_to_master_lists(self):
		"""Any custom finding a dentist typed into an 'add custom' box becomes a
		reusable master record the moment findings are saved - a side effect
		only, the row's own saved is_custom/custom_text/finding fields are
		never touched. Dedup by exact text match so repeat use doesn't create
		duplicate master entries."""
		for row in self.section_findings:
			if not row.is_custom:
				continue
			text = (row.custom_text or "").strip()
			if not text:
				continue
			exists = frappe.db.exists(
				"OPG Standard Finding", {"section_name": row.section, "finding_label": text}
			)
			if not exists:
				frappe.get_doc(
					{
						"doctype": "OPG Standard Finding",
						"section_name": row.section,
						"finding_label": text,
						"finding_template": text,
						"allow_side": 0,
						"allow_tooth": 0,
						"allow_level": 0,
						"active": 1,
					}
				).insert(ignore_permissions=True)

		for row in self.tooth_findings:
			if row.finding:
				continue
			finding_name = (row.finding_name or "").strip()
			description = (row.description or "").strip()
			if not (finding_name and description):
				continue
			exists = frappe.db.exists(
				"OPG Tooth Finding", {"finding_name": finding_name, "description_template": description}
			)
			if not exists:
				frappe.get_doc(
					{
						"doctype": "OPG Tooth Finding",
						"finding_name": finding_name,
						"description_template": description,
						"active": 1,
					}
				).insert(ignore_permissions=True)

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

	@frappe.whitelist(methods=["POST"])
	def add_incidental_finding(self, finding_type: str, side: str, severity: str) -> str:
		# run_doc_method only checks read permission on OPG Report before calling
		# this; the actual create-guard is finding.insert() checking create on
		# OPG Incidental Finding below. OPG Report stays System-Manager-only
		# while OPG Incidental Finding is open to all logged-in users (the
		# "no restrictions for incidental findings" ask) - that's fine here
		# because the OPG Report read-check is still the real gate: nobody
		# without System Manager can reach this method at all, since they
		# can't pass run_doc_method's read-permission check on the report.
		finding = frappe.get_doc(
			{
				"doctype": "OPG Incidental Finding",
				"report": self.name,
				"patient": self.patient,
				"reported_by": self.reported_by,
				"finding_type": finding_type,
				"side": side,
				"severity": severity,
			}
		)
		finding.insert()
		return finding.name


@frappe.whitelist(methods=["GET"])
def export_report_docx(name: str):
	from dental_opg.dental_opg_reporting.docx_export import build_docx

	report = frappe.get_doc("OPG Report", name)
	report.check_permission("read")

	content = build_docx(report)

	frappe.local.response.filename = f"{report.name}.docx"
	frappe.local.response.filecontent = content
	frappe.local.response.content_type = (
		"application/vnd.openxmlformats-officedocument.wordprocessingml.document"
	)
	frappe.local.response.type = "download"


@frappe.whitelist(methods=["GET"])
def get_annotated_report_image(name: str):
	from dental_opg.dental_opg_reporting.image_utils import get_annotated_image_bytes

	report = frappe.get_doc("OPG Report", name)
	report.check_permission("read")

	content = get_annotated_image_bytes(report)
	if content is None:
		frappe.throw(frappe._("Report {0} has no OPG image").format(name), frappe.DoesNotExistError)

	# type="binary" (as_binary) hardcodes application/octet-stream and
	# ignores content_type entirely - type="download" (as_raw) is what
	# actually honors it, same as export_report_docx above. Matters here
	# because wkhtmltopdf (used for the PDF print format, this endpoint's
	# primary consumer) is far less forgiving about content-type sniffing
	# than a modern browser.
	frappe.local.response.filename = f"{report.name}.jpg"
	frappe.local.response.filecontent = content
	frappe.local.response.content_type = "image/jpeg"
	frappe.local.response.display_content_as = "inline"
	frappe.local.response.type = "download"
