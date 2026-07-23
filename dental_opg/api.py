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


@frappe.whitelist(methods=["GET"])
def get_reporting_setup_data():
	"""Master data the Vue reporting screen needs once: standard findings grouped by
	section, and tooth-level findings, so the UI can render pick-lists without a
	round trip per section."""
	standard_findings = frappe.get_all(
		"OPG Standard Finding",
		filters={"active": 1},
		fields=["name", "section_name", "finding_label", "allow_side", "allow_tooth", "allow_level"],
		order_by="section_name asc, finding_label asc",
	)
	findings_by_section = {section: [] for section in SECTION_ORDER}
	for row in standard_findings:
		findings_by_section.setdefault(row.section_name, []).append(row)

	tooth_findings = frappe.get_all(
		"OPG Tooth Finding",
		filters={"active": 1},
		fields=["name", "finding_name"],
		order_by="finding_name asc",
	)

	return {
		"section_order": SECTION_ORDER,
		"standard_findings_by_section": findings_by_section,
		"tooth_findings": tooth_findings,
	}


@frappe.whitelist(methods=["POST"])
def create_report(
	patient_name: str,
	age: int | None = None,
	sex: str | None = None,
	registration_no: str | None = None,
	patient: str | None = None,
):
	"""Create (or reuse) an OPG Patient and a fresh Draft OPG Report in one call,
	so the Vue 'new report' screen only needs a single request."""
	if patient:
		if not frappe.db.exists("OPG Patient", patient):
			frappe.throw(frappe._("Patient {0} not found").format(patient))
	else:
		patient_doc = frappe.get_doc(
			{
				"doctype": "OPG Patient",
				"patient_name": patient_name,
				"age": age,
				"sex": sex,
				"registration_no": registration_no,
			}
		)
		patient_doc.insert()
		patient = patient_doc.name

	report = frappe.get_doc({"doctype": "OPG Report", "patient": patient, "status": "Draft"})
	report.insert()
	return {"report": report.name, "patient": patient}
