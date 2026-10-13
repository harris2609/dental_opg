"""Standard finding templates used to read "... irt tooth number {tooth_number}",
so the export said "irt tooth number 16" and dentists deleted "tooth number"
by hand after every export. The fixture is fixed directly; this patch fixes
any non-fixture copies (e.g. promoted custom findings) already in the DB."""

import frappe

OLD = "irt tooth number {tooth_number}"
NEW = "irt {tooth_number}"


def execute():
	rows = frappe.get_all(
		"OPG Standard Finding",
		filters={"finding_template": ["like", "%irt tooth number%"]},
		fields=["name", "finding_template"],
	)
	for row in rows:
		if OLD in (row.finding_template or ""):
			frappe.db.set_value(
				"OPG Standard Finding",
				row.name,
				"finding_template",
				row.finding_template.replace(OLD, NEW),
				update_modified=False,
			)
