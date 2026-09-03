"""Repair OPG Report child rows that break the parent report's validation.

Rows left over from earlier schema iterations (a `finding` link to a master
that no longer exists, and/or a missing finding_name/description snapshot) make
`_validate_links` / mandatory validation reject every save of the whole report,
so it can no longer be edited or generated.

- a tooth row with neither a live `finding` link nor a finding_name+description
  snapshot is not a finding at all and is deleted
- any other row just loses its dead `finding` link; its snapshot text (which is
  what report generation reads) is kept
"""

import frappe


def execute():
	_repair(
		child_doctype="OPG Tooth Finding Entry",
		master_doctype="OPG Tooth Finding",
		snapshot_fields=("finding_name", "description"),
		delete_without_snapshot=True,
	)
	_repair(
		child_doctype="OPG Report Finding",
		master_doctype="OPG Standard Finding",
		snapshot_fields=("custom_text",),
		delete_without_snapshot=False,
	)


def _repair(child_doctype, master_doctype, snapshot_fields, delete_without_snapshot):
	rows = frappe.get_all(
		child_doctype,
		filters={"parenttype": "OPG Report"},
		fields=["name", "finding", *snapshot_fields],
	)
	if not rows:
		return

	linked = {row.finding for row in rows if row.finding}
	live = set()
	if linked:
		live = set(frappe.get_all(master_doctype, filters={"name": ["in", list(linked)]}, pluck="name"))

	to_delete, to_clear = [], []
	for row in rows:
		has_snapshot = all(row.get(f) for f in snapshot_fields)
		link_ok = bool(row.finding) and row.finding in live
		if delete_without_snapshot and not has_snapshot and not link_ok:
			to_delete.append(row.name)
		elif row.finding and not link_ok:
			to_clear.append(row.name)

	if to_delete:
		frappe.db.delete(child_doctype, {"name": ["in", to_delete]})
	if to_clear:
		frappe.db.set_value(child_doctype, {"name": ["in", to_clear]}, "finding", None, update_modified=False)
	if to_delete or to_clear:
		frappe.db.commit()
