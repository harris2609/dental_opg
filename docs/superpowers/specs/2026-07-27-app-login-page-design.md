# App Login Page — Design Spec

## Problem

The app currently has no login page of its own. To use it, a dentist has to
log in at Frappe's desk (`/app`) first, then manually change the URL to
`/dental_opg`. There's also no logout affordance anywhere in the app itself.

## Goal

A dedicated, app-branded login page reachable at `/dental_opg/login`, with a
server-side guard so unauthenticated visits to any other `/dental_opg/*`
route are redirected there automatically (and back again on success). Add a
matching logout action so the loop is complete.

## Non-goals

- No new DocType, no custom auth backend, no roles/permissions changes.
- No "forgot password", no OAuth/SSO, no remember-me — plain Frappe
  email+password login via the existing `/api/method/login` endpoint.
- No redesign of the existing report pages beyond adding a thin shared header.

## Architecture

### Backend guard (`dental_opg/www/dental_opg.py`)

The existing `get_context` unconditionally serves the SPA shell regardless of
session state. Add a guard, modeled directly on Frappe's own `/login` page
(`frappe/www/login.py:29-41`, which uses the `redirect-to` query param and
`frappe.local.flags.redirect_location` + `raise frappe.Redirect`):

- Compute `app_path = frappe.local.request.path` (e.g. `/dental_opg`,
  `/dental_opg/login`, `/dental_opg/OPG-REP-00042`).
- `is_login_path = app_path.rstrip("/") == "/dental_opg/login"`.
- If `frappe.session.user == "Guest"` and not `is_login_path`: redirect to
  `/dental_opg/login?redirect-to=<app_path>` (URL-encoded).
- If `frappe.session.user != "Guest"` and `is_login_path`: redirect to the
  sanitized `redirect-to` query param if present and it starts with
  `/dental_opg`, else to `/dental_opg`.
- Otherwise render normally (existing behavior: boot with `csrf_token` and
  `user`).

This is a full HTTP redirect (via `frappe.Redirect`), so there's no flash of
app UI for guests and no failed API calls on load — matches the earlier
confirmed answer ("Server redirects to login").

`get_csrf_token()` is already called unconditionally in `get_context` for
every request including Guest ones, which means the login page's own boot
already carries a valid CSRF token tied to the Guest session — no special
CSRF exemption needed for the login POST itself.

### Frontend routing (`frontend/src/router.js`)

Add one route:

```js
{ path: '/dental_opg/login', name: 'Login', component: Login }
```

### `Login.vue` (new)

Centered card, matching the existing plain Tailwind gray palette used
throughout (`ReportList.vue`'s `bg-gray-900` buttons, `rounded`, `text-sm`
conventions):

- Clinic name / app title as heading ("Yenepoya Dental College" / "OPG
  Reporting" subtitle).
- Email + password inputs, submit button.
- On submit: `frappeRequest({ url: '/api/method/login', method: 'POST',
  params: { usr, pwd } })`. frappe-ui's `frappeRequest` special-cases this
  exact URL to return the full response body instead of unwrapping
  `.message`, so a successful call resolves normally.
- On success: read `redirect-to` from the current URL's query string; if
  present and it starts with `/dental_opg`, do a full
  `window.location.href` redirect there; otherwise redirect to
  `/dental_opg`. Must be a full browser navigation, not a SPA route change —
  a fresh page load is what re-runs `get_context()` for the new
  (authenticated) session and hands back a fresh `csrf_token`.
- On failure: `frappeRequest` throws an `Error` with a `.messages` array
  (populated from `_server_messages` / `error.message`) — show the first
  message inline under the form (e.g. "Incorrect password").

### `AppHeader.vue` (new) + `App.vue` change

A thin header — app title on the left, a "Logout" button on the right —
shown on every route except `/login`. `App.vue` becomes:

```vue
<template>
  <AppHeader v-if="route.name !== 'Login'" />
  <router-view />
</template>
```

Logout button: `frappeRequest({ url: '/api/method/logout', method: 'POST'
})` then `window.location.href = '/dental_opg/login'`. The existing session
already carries a valid CSRF token (same mechanism as above), so no special
handling is needed for this authenticated POST.

## Data flow summary

1. Guest visits `/dental_opg/OPG-REP-00042` → server redirect to
   `/dental_opg/login?redirect-to=%2Fdental_opg%2FOPG-REP-00042`.
2. Dentist submits credentials → `POST /api/method/login` → cookie session
   set → full-page redirect to `/dental_opg/OPG-REP-00042`.
3. Fresh page load: `get_context` sees a real user, not login path → renders
   the SPA normally with correct boot data.
4. Dentist clicks Logout → `POST /api/method/logout` → full-page redirect to
   `/dental_opg/login`.

## Testing

- Python: a test hitting the `/dental_opg` and `/dental_opg/login` www routes
  as Guest and as a logged-in user, asserting the redirect (or lack of one)
  in each of the 4 combinations described above. Frappe's `IntegrationTestCase`
  supports issuing requests through `frappe.get_context`/test client; follow
  whatever pattern this app's existing tests use for hitting whitelisted
  endpoints, adapted for a www route's `get_context`.
- No dedicated JS test runner exists in this app (confirmed in the prior
  DOCX-export feature) — `Login.vue`/`AppHeader.vue` correctness is verified
  by building the frontend and manually exercising the full loop (guest
  redirect, login, redirect back, logout, redirect to login) in a browser,
  same verification approach used for every other frontend change in this
  app so far.

## Open risk / accepted trade-off

Only `Administrator` exists as a System User today. This feature doesn't
create additional users — it only changes the entry path into the app for
whichever users already exist. Not a gap introduced by this feature.
