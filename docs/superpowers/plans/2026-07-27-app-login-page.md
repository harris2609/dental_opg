# App Login Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the `dental_opg` app its own login page at `/dental_opg/login`, with a server-side guard redirecting unauthenticated visits to it and back, plus a logout action - so a dentist never has to touch Frappe's desk login to use this app.

**Architecture:** A guard added to the existing `dental_opg/www/dental_opg.py` `get_context` (the single SPA entrypoint all `/dental_opg/*` routes already resolve to via `website_route_rules`) issues a full HTTP redirect for Guests to `/dental_opg/login?redirect-to=<path>`, and redirects already-logged-in users away from the login path. The login page is a new route inside the existing Vue Router SPA (`Login.vue`), calling Frappe's standard `/api/method/login` and `/api/method/logout` endpoints via `frappeRequest` (already used throughout `api.js`). A new `AppHeader.vue` adds a Logout button, shown on every route except login.

**Tech Stack:** Frappe Framework (Python www page + `frappe.Redirect`), Vue 3 + vue-router + frappe-ui (existing frontend stack, no new dependencies).

## Global Constraints

- Login path is exactly `/dental_opg/login` (trailing slash tolerated via `rstrip("/")`).
- Redirect query param name is `redirect-to` (hyphenated - matches Frappe's own `/login` page convention in `frappe/www/login.py`).
- Any `redirect-to` value used as a redirect target must be validated to start with `/dental_opg` - otherwise fall back to `/dental_opg`. This prevents open-redirect via a crafted query param.
- Redirects use `frappe.local.flags.redirect_location = <path>; raise frappe.Redirect` (default HTTP 301), exactly as `frappe/www/login.py` does - no custom status code.
- Post-login and post-logout navigation on the frontend MUST be a full browser navigation (`window.location.href = ...`), never a SPA `router.push`/`router.replace`. A full page load is what re-runs `get_context()` for the new session and hands back a fresh `csrf_token` in `window.csrf_token`.
- No new DocType, no permission/role changes, no new backend dependencies.
- Frontend styling matches the existing plain Tailwind gray palette already used in `ReportList.vue` (`bg-gray-900` primary buttons, `rounded`, `text-sm`, `text-gray-500` for secondary text) - no new component library, no color scheme changes.
- This project has no JS test runner - frontend correctness is verified by `yarn build` succeeding plus manual/curl/Playwright verification of real HTTP behavior, not a new test framework.
- Every task that changes frontend source MUST rebuild and commit `dental_opg/public/frontend/**` and `dental_opg/www/dental_opg.html` in the same commit as the source change. This exact class of bug (source committed, stale bundle shipped) was the Critical finding in a prior feature's final review - do not repeat it.

---

### Task 1: Backend redirect guard in `dental_opg/www/dental_opg.py` (TDD)

**Files:**
- Modify: `apps/dental_opg/dental_opg/www/dental_opg.py`
- Create: `apps/dental_opg/dental_opg/tests/test_www_dental_opg.py`

**Interfaces:**
- Consumes: nothing new - `frappe.session.user`, `frappe.local.request.path`, `frappe.local.request.args`, `frappe.local.flags.redirect_location`, `frappe.Redirect` (all existing Frappe framework surface).
- Produces: `get_context(context)` (existing function, same signature) - now redirects Guests away from any non-login `/dental_opg/*` path to `/dental_opg/login?redirect-to=<path>`, and redirects authenticated users away from `/dental_opg/login` to `/dental_opg` (or a validated `redirect-to`). Non-redirect case is unchanged: `context.boot = {"csrf_token": ..., "user": ...}`.

- [ ] **Step 1: Write the failing tests**

Create `apps/dental_opg/dental_opg/tests/test_www_dental_opg.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.tests.test_www_dental_opg`

Expected: failures on every redirect test - the current `get_context` never redirects, so `response.status_code` is `200` in every case instead of `301`.

- [ ] **Step 3: Rewrite `dental_opg/www/dental_opg.py`**

Replace the full contents of `apps/dental_opg/dental_opg/www/dental_opg.py` with:

```python
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
```

`quote(app_path)` keeps its default `safe='/'`, so slashes in the path stay literal (e.g. `/dental_opg/OPG-REP-00001` stays as-is rather than becoming `%2Fdental_opg%2F...`), matching the exact `Location` header the tests above assert.

- [ ] **Step 4: Run tests to verify they pass**

Run: `bench --site dental_opg-test.localhost run-tests --module dental_opg.tests.test_www_dental_opg`

Expected: `OK`, all 7 tests passing.

- [ ] **Step 5: Commit**

```bash
cd /workspace/development/frappe-bench/apps/dental_opg
git add dental_opg/www/dental_opg.py dental_opg/tests/test_www_dental_opg.py
git commit -m "Add server-side login guard to the dental_opg www route"
```

---

### Task 2: `Login.vue` page + `login`/`logout` API functions + route (frontend)

**Files:**
- Modify: `apps/dental_opg/frontend/src/api.js`
- Modify: `apps/dental_opg/frontend/src/router.js`
- Create: `apps/dental_opg/frontend/src/pages/Login.vue`

**Interfaces:**
- Consumes: `frappeRequest` from `frappe-ui` (existing import already used throughout `api.js`).
- Produces: `login(usr, pwd)` and `logout()` exported from `api.js`, used by `Login.vue` (this task) and `AppHeader.vue` (Task 3). Route named `Login` at path `/dental_opg/login`, consumed by `App.vue`'s header-visibility check (Task 3).

- [ ] **Step 1: Add `login`/`logout` to `api.js`**

Add to `apps/dental_opg/frontend/src/api.js` (near the top, after the existing `callDocMethod` helper - no changes to any existing exported function):

```javascript
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
```

- [ ] **Step 2: Add the login route to `router.js`**

Modify `apps/dental_opg/frontend/src/router.js` to:

```javascript
import { createRouter, createWebHistory } from 'vue-router'
import ReportList from './pages/ReportList.vue'
import NewReport from './pages/NewReport.vue'
import ReportEditor from './pages/ReportEditor.vue'
import Login from './pages/Login.vue'

const routes = [
	{ path: '/dental_opg', name: 'ReportList', component: ReportList },
	{ path: '/dental_opg/new', name: 'NewReport', component: NewReport },
	{ path: '/dental_opg/login', name: 'Login', component: Login },
	{ path: '/dental_opg/:reportId', name: 'ReportEditor', component: ReportEditor, props: true },
]

export default createRouter({
	history: createWebHistory('/'),
	routes,
})
```

Note the `Login` route is declared before the catch-all `/dental_opg/:reportId` route, so `/dental_opg/login` resolves to `Login`, not `ReportEditor` with `reportId: "login"`. Vue Router matches routes in declaration order for equally-specific static-vs-dynamic segments, but declare it first regardless to remove any ambiguity.

- [ ] **Step 3: Create `Login.vue`**

Create `apps/dental_opg/frontend/src/pages/Login.vue`:

```vue
<template>
	<div class="flex min-h-screen items-center justify-center bg-gray-50">
		<div class="w-full max-w-sm rounded border bg-white p-6 shadow-sm">
			<h1 class="text-lg font-semibold text-gray-900">Yenepoya Dental College</h1>
			<p class="mb-6 text-sm text-gray-500">OPG Reporting</p>

			<form @submit.prevent="submit">
				<div class="mb-3">
					<label class="mb-1 block text-xs font-medium text-gray-700">Email</label>
					<input
						v-model="usr"
						type="text"
						autocomplete="username"
						required
						class="w-full rounded border px-3 py-2 text-sm"
					/>
				</div>
				<div class="mb-4">
					<label class="mb-1 block text-xs font-medium text-gray-700">Password</label>
					<input
						v-model="pwd"
						type="password"
						autocomplete="current-password"
						required
						class="w-full rounded border px-3 py-2 text-sm"
					/>
				</div>

				<div v-if="error" class="mb-4 text-sm text-red-600">{{ error }}</div>

				<button
					type="submit"
					:disabled="submitting"
					class="w-full rounded bg-gray-900 px-3 py-2 text-sm text-white hover:bg-gray-700 disabled:opacity-50"
				>
					{{ submitting ? 'Logging in...' : 'Login' }}
				</button>
			</form>
		</div>
	</div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { login } from '../api'

const route = useRoute()
const usr = ref('')
const pwd = ref('')
const error = ref('')
const submitting = ref(false)

async function submit() {
	error.value = ''
	submitting.value = true
	try {
		await login(usr.value, pwd.value)
		const redirectTo = route.query['redirect-to']
		const target = typeof redirectTo === 'string' && redirectTo.startsWith('/dental_opg') ? redirectTo : '/dental_opg'
		window.location.href = target
	} catch (e) {
		error.value = e.messages?.[0] || 'Login failed'
		submitting.value = false
	}
}
</script>
```

- [ ] **Step 4: Build and verify no compiler errors**

Run: `cd /workspace/development/frappe-bench/apps/dental_opg/frontend && yarn build`

Expected: `✓ built in <N>s`, no Vue compiler or import errors.

- [ ] **Step 5: Commit**

```bash
cd /workspace/development/frappe-bench && bench build --app dental_opg
cd /workspace/development/frappe-bench/apps/dental_opg
git add frontend/src/api.js frontend/src/router.js frontend/src/pages/Login.vue \
        dental_opg/public/frontend dental_opg/www/dental_opg.html
git commit -m "Add Login page, route, and login/logout API functions"
```

---

### Task 3: `AppHeader.vue` + logout wiring in `App.vue`

**Files:**
- Create: `apps/dental_opg/frontend/src/components/AppHeader.vue`
- Modify: `apps/dental_opg/frontend/src/App.vue`

**Interfaces:**
- Consumes: `logout()` from `api.js` (Task 2), `route.name` from vue-router (to detect the `Login` route by the name declared in Task 2's `router.js`).
- Produces: a header shown on every route except `Login`, with a working Logout button. No new exports consumed by later tasks - this is the last frontend task.

- [ ] **Step 1: Create `AppHeader.vue`**

Create `apps/dental_opg/frontend/src/components/AppHeader.vue`:

```vue
<template>
	<div class="flex items-center justify-between border-b bg-white px-6 py-3">
		<router-link to="/dental_opg" class="text-sm font-semibold text-gray-900">
			Yenepoya Dental College &middot; OPG Reporting
		</router-link>
		<button
			@click="handleLogout"
			:disabled="loggingOut"
			class="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 disabled:opacity-50"
		>
			{{ loggingOut ? 'Logging out...' : 'Logout' }}
		</button>
	</div>
</template>

<script setup>
import { ref } from 'vue'
import { logout } from '../api'

const loggingOut = ref(false)

async function handleLogout() {
	loggingOut.value = true
	try {
		await logout()
	} finally {
		window.location.href = '/dental_opg/login'
	}
}
</script>
```

The `finally` block redirects even if the `logout()` call itself throws (e.g. session already expired server-side) - the user's intent is to leave the app either way, and a stale/expired session means the backend guard will just bounce them to login on the next full-page load regardless.

- [ ] **Step 2: Wire it into `App.vue`**

Replace the full contents of `apps/dental_opg/frontend/src/App.vue` with:

```vue
<template>
	<AppHeader v-if="route.name !== 'Login'" />
	<router-view />
</template>

<script setup>
import { useRoute } from 'vue-router'
import AppHeader from './components/AppHeader.vue'

const route = useRoute()
</script>
```

- [ ] **Step 3: Build**

Run: `cd /workspace/development/frappe-bench/apps/dental_opg/frontend && yarn build`

Expected: `✓ built in <N>s`, no Vue compiler errors.

- [ ] **Step 4: Commit**

```bash
cd /workspace/development/frappe-bench && bench build --app dental_opg
cd /workspace/development/frappe-bench/apps/dental_opg
git add frontend/src/components/AppHeader.vue frontend/src/App.vue \
        dental_opg/public/frontend dental_opg/www/dental_opg.html
git commit -m "Add AppHeader with logout button, shown on every route except login"
```

---

### Task 4: Final verification - full login/logout loop on `dev.localhost`

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `bench --site dental_opg-test.localhost run-tests --app dental_opg`

Expected: `OK`, all tests passing (includes the new `test_www_dental_opg.py` alongside every pre-existing test).

- [ ] **Step 2: Confirm the built frontend actually contains the new UI**

```bash
grep -c "Yenepoya Dental College" /workspace/development/frappe-bench/apps/dental_opg/dental_opg/public/frontend/assets/*.js
```

Expected: at least 2 matches (Login.vue's heading and AppHeader.vue's link text both contain this string) - guards against the exact "committed source but not the rebuilt bundle" mistake flagged as a Global Constraint above.

- [ ] **Step 3: Full end-to-end curl verification of the redirect loop on `dev.localhost`**

```bash
cd /tmp

# Guest visiting the app root gets redirected to login
curl -s -o /dev/null -w "guest app root: %{http_code} -> %{redirect_url}\n" "http://dev.localhost:8000/dental_opg"

# Guest visiting the login path directly gets 200, not redirected
curl -s -o /dev/null -w "guest login path: %{http_code}\n" "http://dev.localhost:8000/dental_opg/login"

# Log in for real, following the app's own login endpoint
curl -s -c cookies_login.txt -X POST "http://dev.localhost:8000/api/method/login" \
  -d "usr=Administrator&pwd=<the current dev.localhost Administrator password>" \
  -o /dev/null -w "login: %{http_code}\n"

# Logged-in user visiting /dental_opg/login gets redirected away, not shown the form
curl -s -b cookies_login.txt -o /dev/null -w "loggedin login path: %{http_code} -> %{redirect_url}\n" "http://dev.localhost:8000/dental_opg/login"

# Logged-in user visiting the app root gets a normal 200
curl -s -b cookies_login.txt -o /dev/null -w "loggedin app root: %{http_code}\n" "http://dev.localhost:8000/dental_opg"

# Logout, using the CSRF token from the now-authenticated page load
TOKEN=$(curl -s -b cookies_login.txt "http://dev.localhost:8000/dental_opg" | grep -oP 'window\["csrf_token"\] = "\K[^"]+')
curl -s -b cookies_login.txt -X POST "http://dev.localhost:8000/api/method/logout" \
  -H "X-Frappe-CSRF-Token: $TOKEN" -H "Referer: http://dev.localhost:8000/dental_opg" \
  -o /dev/null -w "logout: %{http_code}\n"

# Post-logout, the same cookies should be treated as Guest again
curl -s -b cookies_login.txt -o /dev/null -w "post-logout app root: %{http_code} -> %{redirect_url}\n" "http://dev.localhost:8000/dental_opg"
```

Expected: `guest app root: 301 -> .../dental_opg/login?redirect-to=/dental_opg`, `guest login path: 200`, `login: 200`, `loggedin login path: 301 -> .../dental_opg`, `loggedin app root: 200`, `logout: 200`, `post-logout app root: 301 -> .../dental_opg/login?redirect-to=/dental_opg`.

If the current `dev.localhost` Administrator password isn't known, reset it first with `bench --site dev.localhost set-admin-password <new-password>` and use that value - this mirrors how the previous feature's Playwright verification handled the same situation.

- [ ] **Step 4: Report to the user it's ready for manual browser testing**

Report to the user: visit `http://dev.localhost:8000/dental_opg` while logged out (or in an incognito window) - confirm you land on the new branded login page, not Frappe's desk login. Log in - confirm you're taken to the report list. Click Logout in the header - confirm you're returned to the login page. Try visiting a specific report URL directly while logged out - confirm you're redirected to login and, after logging in, land back on that exact report.

---
