app_name = "dental_opg"
app_title = "Dental OPG Reporting"
app_publisher = "Dental Clinic"
app_description = "Standalone Frappe app for dental OPG X-ray structured reporting"
app_email = "tools.zenpivot@gmail.com"
app_license = "mit"

fixtures = ["OPG Standard Finding", "OPG Tooth Finding", "Print Format"]

website_route_rules = [
	{"from_route": "/dental_opg/<path:app_path>", "to_route": "dental_opg"},
	{"from_route": "/dental_opg", "to_route": "dental_opg"},
]

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "dental_opg",
# 		"logo": "/assets/dental_opg/logo.png",
# 		"title": "Dental OPG Reporting",
# 		"route": "/dental_opg",
# 		"has_permission": "dental_opg.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/dental_opg/css/dental_opg.css"
# app_include_js = "/assets/dental_opg/js/dental_opg.js"

# include js, css files in header of web template
# web_include_css = "/assets/dental_opg/css/dental_opg.css"
# web_include_js = "/assets/dental_opg/js/dental_opg.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "dental_opg/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "dental_opg/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

jinja = {
	"methods": ["dental_opg.dental_opg_reporting.report_builder.build_report_sections"],
}

# Installation
# ------------

# before_install = "dental_opg.install.before_install"
# after_install = "dental_opg.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "dental_opg.uninstall.before_uninstall"
# after_uninstall = "dental_opg.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "dental_opg.utils.before_app_install"
# after_app_install = "dental_opg.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "dental_opg.utils.before_app_uninstall"
# after_app_uninstall = "dental_opg.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "dental_opg.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "dental_opg.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"dental_opg.tasks.all"
# 	],
# 	"daily": [
# 		"dental_opg.tasks.daily"
# 	],
# 	"hourly": [
# 		"dental_opg.tasks.hourly"
# 	],
# 	"weekly": [
# 		"dental_opg.tasks.weekly"
# 	],
# 	"monthly": [
# 		"dental_opg.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "dental_opg.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "dental_opg.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	"frappe.utils.print_format.download_pdf": "dental_opg.print_utils.download_pdf",
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "dental_opg.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["dental_opg.utils.before_request"]
# after_request = ["dental_opg.utils.after_request"]

# Job Events
# ----------
# before_job = ["dental_opg.utils.before_job"]
# after_job = ["dental_opg.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"dental_opg.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

