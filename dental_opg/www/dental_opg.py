import frappe
from frappe.sessions import get_csrf_token

no_cache = 1


def get_context(context):
	context.boot = {
		"csrf_token": get_csrf_token(),
		"user": frappe.session.user,
	}
	return context
