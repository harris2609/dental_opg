import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import set_request
from frappe.website.serve import get_response


class TestDentalOpgWwwGuard(IntegrationTestCase):
	def setUp(self):
		self._clear_request()

	def tearDown(self):
		frappe.set_user("Administrator")
		self._clear_request()

	def _clear_request(self):
		if hasattr(frappe.local, "request"):
			delattr(frappe.local, "request")

	def test_guest_visiting_app_path_is_redirected_to_login_with_redirect_to(self):
		frappe.set_user("Guest")
		set_request(method="GET", path="/dental_opg/OPG-REP-00001")

		response = get_response()

		self.assertEqual(response.status_code, 301)
		self.assertEqual(response.headers["Location"], "/dental_opg/login?redirect-to=/dental_opg/OPG-REP-00001")

	def test_guest_visiting_bare_app_root_is_redirected_to_login(self):
		frappe.set_user("Guest")
		set_request(method="GET", path="/dental_opg")

		response = get_response()

		self.assertEqual(response.status_code, 301)
		self.assertEqual(response.headers["Location"], "/dental_opg/login?redirect-to=/dental_opg")

	def test_guest_visiting_login_path_is_not_redirected(self):
		frappe.set_user("Guest")
		set_request(method="GET", path="/dental_opg/login")

		response = get_response()

		self.assertEqual(response.status_code, 200)

	def test_logged_in_user_visiting_login_path_is_redirected_to_app_root(self):
		frappe.set_user("Administrator")
		set_request(method="GET", path="/dental_opg/login")

		response = get_response()

		self.assertEqual(response.status_code, 301)
		self.assertEqual(response.headers["Location"], "/dental_opg")

	def test_logged_in_user_visiting_login_path_with_valid_redirect_to_is_sent_there(self):
		frappe.set_user("Administrator")
		set_request(method="GET", path="/dental_opg/login", query_string="redirect-to=/dental_opg/OPG-REP-00007")

		response = get_response()

		self.assertEqual(response.status_code, 301)
		self.assertEqual(response.headers["Location"], "/dental_opg/OPG-REP-00007")

	def test_logged_in_user_visiting_login_path_with_unsafe_redirect_to_falls_back_to_app_root(self):
		frappe.set_user("Administrator")
		set_request(method="GET", path="/dental_opg/login", query_string="redirect-to=https://evil.example.com")

		response = get_response()

		self.assertEqual(response.status_code, 301)
		self.assertEqual(response.headers["Location"], "/dental_opg")

	def test_logged_in_user_visiting_app_path_is_not_redirected(self):
		frappe.set_user("Administrator")
		set_request(method="GET", path="/dental_opg")

		response = get_response()

		self.assertEqual(response.status_code, 200)
