"""Tooth finding rows created through the API before OPGReport.validate
derived the arch from the tooth number could carry the Select's default
"Maxillary" for a lower tooth. Save corrects a report, but untouched old
reports kept the wrong arch, so this backfills every stored row."""

import frappe

from dental_opg.dental_opg_reporting.doctype.opg_report.opg_report import arch_for_tooth


def execute():
	rows = frappe.get_all(
		"OPG Tooth Finding Entry",
		filters={"parenttype": "OPG Report"},
		fields=["name", "tooth_number", "arch"],
	)
	for row in rows:
		arch = arch_for_tooth(row.tooth_number)
		if arch and arch != row.arch:
			frappe.db.set_value("OPG Tooth Finding Entry", row.name, "arch", arch, update_modified=False)
