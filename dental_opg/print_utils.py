import frappe
from frappe.utils.print_format import download_pdf as _core_download_pdf


def _clean(value):
	"""Frappe's own /printview 'Get PDF' link (frappe/www/printview.html)
	builds its href with Jinja placeholders like {{letterhead|e}}. When the
	context var is unset (Python None), Jinja renders it as the literal
	string "None" into the URL. download_pdf's pdf_generator param is
	strictly typed Literal["wkhtmltopdf", "chrome"] | None, so that literal
	string fails validation and every print format's Get PDF button 500s.
	Normalize the string back to real None before delegating to core."""
	return None if value in (None, "None", "") else value


@frappe.whitelist()
def download_pdf(
	doctype: str,
	name: str,
	format=None,
	doc=None,
	no_letterhead=None,
	language=None,
	letterhead=None,
	pdf_generator: str | None = None,
):
	return _core_download_pdf(
		doctype=doctype,
		name=name,
		format=_clean(format),
		doc=doc,
		no_letterhead=_clean(no_letterhead) or 0,
		language=_clean(language),
		letterhead=_clean(letterhead),
		pdf_generator=_clean(pdf_generator),
	)
