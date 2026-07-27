from urllib.parse import quote

import frappe
from frappe.sessions import get_csrf_token

no_cache = 1

LOGIN_PATH = "/dental_opg/login"
APP_ROOT = "/dental_opg"


def get_context(context):
	app_path = frappe.local.request.path.rstrip("/") or "/"
	is_login_path = app_path == LOGIN_PATH

	if frappe.session.user == "Guest":
		if not is_login_path:
			frappe.local.flags.redirect_location = f"{LOGIN_PATH}?redirect-to={quote(app_path)}"
			raise frappe.Redirect
	elif is_login_path:
		redirect_to = frappe.local.request.args.get("redirect-to")
		if not redirect_to or not redirect_to.startswith(APP_ROOT):
			redirect_to = APP_ROOT
		frappe.local.flags.redirect_location = redirect_to
		raise frappe.Redirect

	context.boot = {
		"csrf_token": get_csrf_token(),
		"user": frappe.session.user,
	}
	return context
