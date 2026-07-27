import { frappeRequest } from 'frappe-ui'

const DOCTYPE = 'OPG Report'

// frappeRequest already unwraps the classic `/api/method` response's
// `message` key internally - do not unwrap it again here.
// Exception: run_doc_method also attaches a `docs` key (for client-side
// doc-cache sync) whenever the method saves the document, which makes
// frappeRequest bail out and return the raw {docs, message} envelope
// instead of unwrapping - so unwrap that one case explicitly.
function callDocMethod(name, method, args) {
	return frappeRequest({
		url: '/api/method/run_doc_method',
		method: 'POST',
		params: { dt: DOCTYPE, dn: name, method, args },
	}).then((r) => (r && r.docs ? r.message : r))
}

export function login(usr, pwd) {
	return frappeRequest({
		url: '/api/method/login',
		method: 'POST',
		params: { usr, pwd },
	})
}

export function logout() {
	return frappeRequest({
		url: '/api/method/logout',
		method: 'POST',
	})
}

export function getSetupData() {
	return frappeRequest({
		url: '/api/method/dental_opg.api.get_reporting_setup_data',
		method: 'GET',
	})
}

export function createReport(payload) {
	return frappeRequest({
		url: '/api/method/dental_opg.api.create_report',
		method: 'POST',
		params: payload,
	})
}

export function getReport(name) {
	return frappeRequest({
		url: '/api/method/frappe.client.get',
		method: 'GET',
		params: { doctype: DOCTYPE, name },
	})
}

export function listReports() {
	return frappeRequest({
		url: '/api/method/frappe.client.get_list',
		method: 'GET',
		params: {
			doctype: DOCTYPE,
			fields: JSON.stringify(['name', 'patient', 'report_date', 'status', 'modified']),
			order_by: 'modified desc',
			limit_page_length: 50,
		},
	})
}

export function saveReportDetails(name, fields) {
	return frappeRequest({
		url: '/api/method/frappe.client.set_value',
		method: 'POST',
		params: { doctype: DOCTYPE, name, fieldname: fields },
	})
}

export function saveFindings(name, sectionFindings, toothFindings) {
	return callDocMethod(name, 'save_findings', {
		section_findings: sectionFindings,
		tooth_findings: toothFindings,
	})
}

export function saveAnnotations(name, annotations) {
	return callDocMethod(name, 'save_annotations', { annotations })
}

export function generateReport(name) {
	return callDocMethod(name, 'generate_report', {})
}

export function getIncidentalFindings(reportName) {
	return frappeRequest({
		url: '/api/method/frappe.client.get_list',
		method: 'GET',
		params: {
			doctype: 'OPG Incidental Finding',
			filters: JSON.stringify({ report: reportName }),
			fields: JSON.stringify(['name', 'finding_type', 'side', 'severity', 'finding_date']),
			order_by: 'creation asc',
			limit_page_length: 0,
		},
	})
}

export function listAllIncidentalFindings() {
	return frappeRequest({
		url: '/api/method/frappe.client.get_list',
		method: 'GET',
		params: {
			doctype: 'OPG Incidental Finding',
			fields: JSON.stringify(['name', 'report', 'patient', 'finding_type', 'side', 'severity', 'finding_date', 'reported_by']),
			order_by: 'finding_date desc, creation desc',
			limit_page_length: 0,
		},
	})
}

export function addIncidentalFinding(reportName, { finding_type, side, severity }) {
	return callDocMethod(reportName, 'add_incidental_finding', { finding_type, side, severity })
}

export function deleteIncidentalFinding(name) {
	return frappeRequest({
		url: '/api/method/frappe.client.delete',
		method: 'POST',
		params: { doctype: 'OPG Incidental Finding', name },
	})
}

// upload_file only creates the File record (with attached_to_* metadata for
// the attachments list) - it does NOT write the file_url back into the
// parent doc's field. That's normally done by Desk's attach widget; since
// we're a custom SPA we have to do it ourselves with set_value.
export function uploadImage(file, docname) {
	const form = new FormData()
	form.append('file', file)
	form.append('doctype', DOCTYPE)
	form.append('docname', docname)
	form.append('fieldname', 'opg_image')
	form.append('is_private', '0')

	const headers = {}
	if (window.csrf_token && window.csrf_token !== '{{ csrf_token }}') {
		headers['X-Frappe-CSRF-Token'] = window.csrf_token
	}

	return fetch('/api/method/upload_file', {
		method: 'POST',
		headers,
		body: form,
		credentials: 'same-origin',
	})
		.then((r) => r.json())
		.then((r) => r.message.file_url)
		.then((fileUrl) => setOpgImage(docname, fileUrl).then(() => fileUrl))
}

function setOpgImage(name, fileUrl) {
	return frappeRequest({
		url: '/api/method/frappe.client.set_value',
		method: 'POST',
		params: { doctype: DOCTYPE, name, fieldname: 'opg_image', value: fileUrl },
	})
}
