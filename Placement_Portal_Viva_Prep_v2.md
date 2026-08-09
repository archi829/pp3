# Placement Portal — Viva Prep v2
### (Route-by-route connections + real-pattern theory Qs + likely coding tasks + improvement suggestions)

This builds on the first prep doc. It's structured around what actually happens in these vivas, based on real proctor-experience reports: **ID check → demo → full code walkthrough (backend then frontend, uninterrupted) → live coding change → rapid-fire theory questions**, roughly in that order, almost always followed by a small live coding task and a short set of near-identical theory questions from a shared question bank.

---

## PART A — How the Viva Actually Runs (from real reports)

1. **ID verification** — have your ID ready on camera immediately.
2. **GitHub check** — proctor may ask to see the repo / collaborator status. Know your repo URL and that it's `archi829/pp2`.
3. **Setup proof** — some proctors want you to download a fresh zip / clone and run it live, others skip this entirely if you already have it running. **Have `python init_db.py` + `python app.py` ready to run in under 30 seconds.** Keep a terminal + VS Code open beforehand.
4. **Full demo** — walk through login as each role, core actions per role. Most proctors say "explain as you go, I'll stay muted" — **use the silence**, narrate thoroughly, don't rush. Several reports explicitly say the proctor rewarded people who explained *why* (CORS, JWT, caching, CSV pipeline) unprompted, not just *what*.
5. **Code walkthrough** — backend first (models → routes → auth), then frontend (components → router → axios config). Be ready to have them say "stop, explain this specific line."
6. **One live coding task** — almost universal. Typically one of:
   - Write a new Flask/Flask-RESTful route (e.g., "list all X for a given Y")
   - Write/modify a Vue component or add a route
   - A small full-stack change: new backend route + a frontend view that consumes it
   - A cosmetic CSS/content change (background color, text color, move an element)
   - Make a form field editable end-to-end (frontend + backend)
7. **Theory rapid-fire** — pulled from a fairly fixed pool (see Part C). Very often near-identical across different proctors/projects: HTTP status codes, ORM, Git vs VCS, storage types, SPA, Vue basics, `v-if` vs `v-show`, computed vs watch, authentication vs authorization, caching, Celery/Redis.

**Meta-advice pulled from the reports:**
- Don't wait to be interrupted — explain thoroughly and proactively; several proctors literally didn't ask a single follow-up because the demo+explanation was thorough.
- Know **every line of your own code** — several reports stress "know what every line means," not just the big picture.
- Practice writing a route and a Vue component/route **cold, without autocomplete** — several reports had this as a required live task.
- Be ready to make a **small live change and show it reflected on both ends** (e.g., "change X in backend, show it's reflected in frontend").

---

## PART B — Full Route-by-Route Connection Map

Format for each row: **Vue trigger → Axios call → Flask route (file:function) → DB/model touched → side effects → response → UI update.**

### B.1 — Auth (`routes/auth.py`, prefix `/api/auth`)

| Vue trigger | Axios call | Flask handler | DB / models | Side effects | Response → UI |
|---|---|---|---|---|---|
| `Login.js :: submit()` | `POST /auth/login {email,password,role}` | `auth.py :: login()` | `Admin`/`Company`/`Student` (branch on `role`) | none (read-only + password check) | `access_token, role, user_id, email` → `window.auth.login(data)` stores in `localStorage` → `router.push` to role dashboard |
| `Register.js` (student mode) | `POST /auth/register/student` (multipart if resume attached) | `auth.py :: register_student()` | INSERT `Student` | `invalidate_namespace('admin_students')`; resume saved to `UPLOAD_FOLDER` via `secure_filename` | Immediate JWT returned — student is auto-logged-in on registration |
| `Register.js` (company mode) | `POST /auth/register/company` | `auth.py :: register_company()` | INSERT `Company` (`approval_status='Pending'`) | `invalidate_namespace('admin_companies')` | **No token returned** — company must wait for admin approval before first login |
| any authenticated page load | (implicit) | `auth.py :: me()` behind `@jwt_required()` | reads own row from Admin/Company/Student by JWT identity | none | used to rehydrate profile info |
| logout button | `POST /auth/logout` | `auth.py :: logout()` | none | none (JWT isn't server-side revoked — it's stateless) | frontend clears `localStorage` and redirects |

### B.2 — Admin (`routes/admin.py`, prefix `/api/admin`, all behind `@admin_required`)

| Component | Call | Handler | Notes |
|---|---|---|---|
| `AdminDashboard.js` (`mounted`) | `GET /admin/dashboard` | `dashboard()` | Counts + 5 most-recent pending companies/drives — **not cached** (dashboard needs to always be fresh) |
| `AdminCompanies.js` (`watch: '$route.query'`) | `GET /admin/companies?q=&status=` | `companies()` | **Cached** via `admin_companies_key(q,status)`; cache-hit skips the whole DB query and `ilike` filter block |
| approve/reject/blacklist buttons | `PUT /admin/companies/<id>/approve|reject|blacklist` | respective handlers | Each calls `invalidate_namespace('admin_companies')` right after commit — next list fetch is guaranteed fresh |
| bulk-approve checkbox row | `POST /admin/companies/bulk-status {company_ids, action}` | `bulk_company_status()` | Loops IDs, updates, single invalidation call at the end (not per-row) |
| `AdminDrives.js` | `GET /admin/drives?status=&company_id=` | `drives()` | **Not cached** (drives list is lower-traffic than companies/students lists) |
| drive approve/reject | `PUT /admin/drives/<id>/approve|reject` | | Calls `safe_delete(student_drives_key(''))` — because approving a drive is exactly the write that makes the *cached student drives list* stale |
| `AdminStudents.js` (`watch`) | `GET /admin/students?q=` | `students()` | **Cached**, same pattern as companies |
| `AdminStudentDetail.js` | `GET /admin/students/<id>` | `student_detail()` | Also returns that student's full application list inline (`serialize_application_for_student`) |
| blacklist student toggle | `PUT /admin/students/<id>/blacklist` | | `invalidate_namespace('admin_students')` |
| resume "view" icon | `GET /admin/students/<id>/resume` | `download_student_resume()` | `send_from_directory` — **admin can view ANY student's resume, no scoping check** (unlike company's version — see B.3) |
| `AdminApplications.js` (`mounted`) | `GET /admin/applications?history=1` | `applications()` | Optionally bundles each app's `status_log` inline if `history=1` |
| application row expand | `GET /admin/applications/<id>/history` | `application_history()` | Just the log rows for one app |
| global search bar | `GET /admin/search?q=&type=company|student` | `search()` | One endpoint, branches server-side on `type` — reuses the same serializers as the dedicated list endpoints |

### B.3 — Company (`routes/company.py`, prefix `/api/company`, all behind `@company_required`)

| Component | Call | Handler | Notes |
|---|---|---|---|
| `CompanyDashboard.js` | `GET /company/dashboard` | `dashboard()` | Computes `active_drives`/`pending_drives`/`total_applicants` in Python from the company's own drives — not separate queries |
| `CompanyProfile.js` (`mounted`) then edit form | `GET /company/profile` then `PUT /company/profile` | `get_profile()` / `update_profile()` | **`company_name` and `email` are intentionally NOT editable** — only hr_contact/industry/website/description |
| `CompanyDrives.js` (create mode) | `POST /company/drives` | `create_drive()` | Validates `deadline > today`; gated by `approval_status == Approved`; status forced to `Pending` — even an approved company's new drive needs fresh admin sign-off |
| `CompanyDrives.js` (edit mode, `:id/edit` route) | `GET /company/drives/<id>` then `PUT /company/drives/<id>` | `get_drive()` / `edit_drive()` | Same Vue component handles both create and edit — branches on whether `route.params.id` exists |
| close/reopen drive toggle | `PUT /company/drives/<id>/status {action}` | `update_drive_status()` | Only `Approved→Closed` or `Closed→Approved` allowed; also busts the student drives cache |
| delete drive | `DELETE /company/drives/<id>` | `delete_drive()` | Cascades to delete all Applications on that drive (DB-level `cascade='all, delete-orphan'` on `PlacementDrive.applications`) |
| `DriveApplicants.js` (tabs + sort dropdown, `watch`) | `GET /company/drives/<id>/applications?sort=&tab=` | `drive_applications()` | Server computes per-status `counts` dict for the tab badges in the same call — no separate count endpoint |
| status dropdown per row | `PUT /company/applications/<id>/status {status,note}` | `update_status()` | Validated against `FORWARD_TRANSITIONS`; writes log + notification; auto-cancels stale scheduled interviews if rejecting |
| bulk status action | `POST /company/applications/bulk-status {app_ids,status}` | `bulk_update_status()` | Same transition rules, reports `skipped_ids` separately from `updated_ids` |
| "Mark Selected" modal (position/salary/joining date) | `PUT /company/applications/<id>/select` | `select_application()` | Creates a `Placement` row (idempotent — checks for an existing one first via `.flush()`), sends congrats notification |
| "Schedule Interview" modal | `POST /company/interviews {application_id,scheduled_at,...}` | `create_interview()` | **Implicitly** advances `Application.status` to `Interview Scheduled` (unless already Selected/Rejected/Placed) — this is why you *can't* set that status via the plain dropdown |
| `CompanyInterviews.js` (`mounted`) | `GET /company/interviews` | `list_interviews()` | Joined across Interview→Application→PlacementDrive, filtered to this company, ordered by upcoming time |
| interview edit (reschedule/mark complete) | `PUT /company/interviews/<id>` | `update_interview()` | Partial update — only fields present in the payload are touched |
| `CompanyStudentProfile.js` | `GET /company/student/<id>/profile` | `view_student_profile()` | Access gated by `_has_applied_to_company()` — a company can only view students who applied to **its own** drives |
| resume view (scoped) | `GET /company/student/<id>/resume` | `view_resume()` | Same `_has_applied_to_company()` gate — **stricter than the admin version** (B.2) |
| "Export CSV" button | `POST /company/export` → poll `GET /company/export/status/<task_id>` | `trigger_export()` / `export_status()` | Fire-and-forget Celery job; 202 + task_id; frontend polls every few seconds until `SUCCESS`/`FAILURE` |
| `CompanyNotifications.js` (`mounted`) | `GET /company/notifications` | `notifications()` | **Side effect:** marks every fetched notification `is_read=True` on read — visiting the page "consumes" the unread badge |

### B.4 — Student (`routes/student.py`, prefix `/api/student`, all behind `@student_required`)

| Component | Call | Handler | Notes |
|---|---|---|---|
| `StudentDashboard.js` (`mounted`) | `GET /student/dashboard` | `dashboard()` | Bundles: profile, stats (available/applied/shortlisted/selected counts), 5 latest open drives not yet applied to, 5 recent applications, 5 unread notifications — one call for the whole page |
| `StudentProfile.js` | `GET /student/profile` then `PUT /student/profile` | `get_profile()` / `update_profile()` | `email` not editable; CGPA re-validated 0–10 server-side even though it was validated at registration too |
| resume upload button | `POST /student/profile/resume` (multipart) | `upload_resume()` | Filename becomes `student_<id>_<original>`; overwrites `resume_path` pointer (old file is NOT deleted from disk — worth noting as a gap, see Part D) |
| `BrowseDrives.js` (`watch: $route.query.q`) | `GET /student/drives?q=` | `list_drives()` | **The most cache-aware endpoint in the app**: unfiltered view is Redis-cached (shared across all students); `applied_drive_ids` is *separately* cached per-student (`student_applied_ids_<id>`) so the "already applied" badge stays correct without invalidating the shared drives cache; search queries bypass cache entirely |
| `DriveDetail.js` (`watch: route.params.id`) | `GET /student/drives/<id>` | `get_drive()` | Returns `already_applied` (the full application object) inline if one exists, so the "Apply" button can flip to "View Application" without a second call |
| "Apply" button | `POST /student/applications {drive_id,cover_letter}` | `apply()` | DB unique constraint prevents duplicates → `IntegrityError` → `409`; on success busts `student_applied_ids_<id>` |
| `StudentApplications.js` (`mounted`) | `GET /student/applications` | `list_applications()` | Also returns `status_counts` for the stat cards, computed server-side in one pass |
| "Export CSV" button (see exact code below) | `POST /student/applications/export` → poll `GET .../export/status/<task_id>` | `trigger_export()` / `export_status()` | Same fire-and-forget pattern as company export |
| cover letter modal / note save | `PUT /student/applications/<id>/note {student_notes}` | `save_note()` | Purely student-private scratch notes, no notification/log generated |
| status history expand | `GET /student/applications/<id>/history` | `application_history()` | Ownership-checked (`app.student_id != student.id` → 404, not 403 — deliberately doesn't leak existence of other students' apps) |
| Accept/Decline offer buttons | `PUT /student/applications/<id>/offer {action}` | `respond_offer()` | Only legal when `status == Selected`; sets `offer_status` to Accepted/Declined |
| `StudentInterviews.js` (`mounted`) | `GET /student/interviews` | `list_interviews()` | Serializer deliberately omits the student's own name (they know who they are) unlike the company-facing version |
| `StudentPlacements.js` (`mounted`) | `GET /student/placements` | `list_placements()` | Joins Company/PlacementDrive per placement row inside the serializer (not a single SQL join — N+1-ish but fine at this scale) |
| offer letter download | `GET /student/placements/<id>/offer-letter` | `download_offer_letter()` | `as_attachment=True` (forces download) — the only download endpoint that does this; others use `as_attachment=False` (view inline) |
| `StudentNotifications.js` (`mounted`) | `GET /student/notifications` | `list_notifications()` | Same "mark read on view" side effect as company notifications |

**Exact CSV-export click-to-done flow (good to know cold — it's asked as a live demo item):**
```
1. User clicks "Export CSV" → StudentApplications.js exportCSV()
2. POST /student/applications/export  → tasks.py: export_applications_csv.delay(student.id)
3. Backend returns 202 { task_id }  → self.exporting = true, toast shown
4. Frontend starts setInterval polling every 3000ms:
     GET /student/applications/export/status/<task_id>
5. Celery worker (separate process) picks the job off Redis, builds the CSV,
   writes it to static/exports/applications_student_<id>.csv,
   creates a Notification row, commits.
6. Poll sees status == 'SUCCESS' → clearInterval, exporting = false,
   toast: "CSV ready! Check your notifications for the download link."
7. User opens Notifications page → sees the message with the /static/exports/... link.
```
**If asked to demo this live and Celery/Redis isn't running**: the `.delay()` call will raise, caught by the `except Exception` in the route, returns `503` — demo this as the graceful-degradation path if you can't spin up a worker on the spot.

### B.5 — Generic API (`routes/api.py`, prefix `/api`, **no auth**)
`GET/POST /api/students`, `GET/PUT/DELETE /api/students/<id>`, `GET/POST /api/drives`, `GET/PUT/DELETE /api/drives/<id>`, `GET /api/stats`. Built with Flask-RESTful `Resource` + `reqparse`. Thin, no business rules, **not used by the actual Vue frontend** — this is almost certainly present to demonstrate Flask-RESTful specifically (a taught technique) separately from the "real" hand-rolled JSON routes. Good to mention proactively: *"this is a separate, simpler Flask-RESTful CRUD layer, distinct from the role-scoped API the frontend actually uses."*

### B.6 — Vue SPA catch-all (`app.py`)
```python
@app.route('/')
@app.route('/<path:path>')
def serve_vue(path=''):
    if path.startswith('api/') or path.startswith('static/'):
        return jsonify({"msg": "Not found."}), 404
    return render_template('index.html')
```
Every non-API, non-static path returns the **same** `index.html`; Vue Router (in `history` mode) then reads `window.location.pathname` and renders the matching component. This is *why* a hard refresh on `/student/drives` still works instead of 404ing.

---

## PART C — Theory Question Bank (from real reports, answered for THIS project)

### HTTP & REST
- **200** OK — successful GET/PUT with body. **201** Created — successful POST that creates a row (e.g., register, apply, create drive). **202** Accepted — used uniquely for the two `/export` endpoints: work queued, not finished yet. **400** Bad Request — validation failure (missing fields, bad date format). **401** Unauthorized — missing/invalid/expired JWT (handled centrally in `app.py`'s `@jwt.unauthorized_loader` etc.). **403** Forbidden — valid JWT but wrong role, blacklisted, or not yet approved. **404** Not Found — resource doesn't exist or (deliberately) to hide existence of another user's private resource. **409** Conflict — duplicate application (unique constraint violation). **422** — flask-jwt-extended's code for a structurally invalid token. **500** — generic server error handler (JSON, not HTML, per MAD2's error-handler philosophy). **503** — Celery/Redis broker unreachable, degrade gracefully instead of crashing.
- **Can Flask return a boolean?** A Python `bool` isn't a valid Flask response by itself — you must wrap it (`jsonify({'is_blacklisted': True})` or convert to string/JSON). Flask response objects need to be str/dict/tuple/Response, not a bare bool.
- **GET vs POST**: GET is idempotent/side-effect-free/cacheable, parameters in query string (e.g. `/admin/companies?q=&status=`); POST creates/mutates and carries data in the body (e.g. login, apply, register). This project also uses PUT (partial/full update, idempotent) and DELETE.

### ORM / Database
- **What is ORM?** Object-Relational Mapping — lets you manipulate DB rows as Python objects (`Student.query.get(id)`) instead of writing raw SQL, while SQLAlchemy translates method calls to SQL under the hood.
- **`db.Model`**: the SQLAlchemy declarative base every table class inherits from; give it `__tablename__` and `db.Column(...)` attributes and it auto-generates the CREATE TABLE DDL and the query interface.
- **Where is `db` initialized?** `models.py`: `db = SQLAlchemy()` (uninitialized/unbound). It's bound to the actual Flask app in `app.py`'s `create_app()` via `db.init_app(app)` — this two-step split (instantiate in `models.py`, bind in `app.py`) is exactly what avoids circular imports.
- **relationship() / backref**: e.g. `Company.drives = db.relationship('PlacementDrive', backref='company', ...)` — lets you do `company.drives` (forward) and `drive.company` (backref, auto-generated on the other side) without writing a second explicit relationship. `backref` is the older, implicit, one-line way of declaring both directions; `back_populates` is the newer, explicit, two-line way (declared on *both* models, each pointing at the other by name) — this project uses `backref` everywhere.
- **`lazy=True`**: default (in this SQLAlchemy version equivalent to `'select'`) — the related rows are fetched with a separate query *only when the relationship attribute is accessed*, not eagerly joined at load time. Trade-off: fewer surprise big joins, but potential N+1 query patterns if you loop and access `.company` on many rows.
- **`cascade='all, delete-orphan'`**: used on `Company.drives`, `Student.applications`, `Application.interviews`, `Application.status_log`. Means deleting the parent row auto-deletes its children (deleting a Company deletes its Drives, which cascades again to delete their Applications, etc.) — without this you'd get a FK constraint error or orphaned rows.
- **`UniqueConstraint`**: `Application(student_id, drive_id)` — see Part B / doc v1.
- **`db.Index`**: `Notification` has a composite index on `(user_type, user_id)` for fast per-user notification lookups.
- **like vs ilike**: `LIKE` is a case-sensitive (on most DBs; SQLite's `LIKE` is actually case-insensitive for ASCII by default) pattern match with `%`/`_` wildcards; `ILIKE` is explicitly **case-insensitive** LIKE (Postgres syntax; SQLAlchemy's `.ilike()` normalizes this across backends). This project uses `.ilike(f'%{q}%')` everywhere search is implemented (admin companies/students/search, student drive search) specifically so "python" matches "Python".
- **Normalization / 3NF** (generic, but map it to this schema if asked): this schema is roughly 3NF — e.g., `company_name` isn't duplicated on every `PlacementDrive` row, just `company_id` (FK), and you join to get the name at read time (see every `serialize_drive()` calling `d.company.company_name`). Denormalization would mean storing `company_name` directly on `PlacementDrive` for read speed at the cost of update anomalies if a company renames itself.
- **What happens querying an empty table?** `Model.query.all()` → `[]` (empty list, not `None`, not an error); `Model.query.first()` → `None`; `Model.query.get(id)` on a non-existent id → `None` (this project mostly checks explicitly with `if not X: return 404` rather than relying on `get_or_404` everywhere — a couple of endpoints do use `get_or_404`, e.g. `Application.query.get_or_404(app_id)`).

### MVC
- **Model** = `models.py` (data + schema). **View** — in a classic Flask/Jinja app this is the templates; here, because it's a JSON API, the "View" role is effectively taken over by the **Vue frontend** (it renders the JSON). **Controller** = the route handler functions in `routes/*.py` — they receive the request, talk to the Model, and hand data back to be "viewed." Worth stating explicitly: *"MAD1 was closer to classic server-rendered MVC with Jinja2 as the View; MAD2 splits View out entirely into a separate SPA, so the backend is really just Model + Controller (a JSON API), and Vue owns the View layer."*

### Auth: Authentication vs Authorization
- **Authentication** = "who are you" — here, `POST /api/auth/login` verifying email+password and issuing a JWT.
- **Authorization** = "what are you allowed to do" — here, the three decorators in `routes/decorators.py` (`admin_required`/`company_required`/`student_required`) checking the JWT's `role` claim, and further business-rule checks (blacklist, approval status) layered on top.
- **Where in code**: authentication lives in `auth.py`'s `login()`; authorization lives in `decorators.py`, applied via `@admin_required` etc. on every protected route.

### SPA / Vue.js
- **SPA (Single Page Application)**: the browser loads one HTML shell once; all subsequent "navigation" is JS swapping components in/out and updating the URL via the History API — no full-page reload, no fresh server round-trip for HTML on every click. Here: `templates/index.html` is the *only* HTML file Flask ever serves for a page view; Vue Router handles everything after that.
- **Vue.js**: a progressive JS framework for building reactive UIs via components with declarative templates (`v-model`, `v-if`, `v-for`, etc.) bound to a `data()` object; changes to `data` automatically re-render the relevant DOM. This project uses **Vue 2 (Options API)**, not Vue 3/Composition API.
- **Vue lifecycle hooks** (this project uses `mounted` and rarely anything else): `beforeCreate → created → beforeMount → mounted → beforeUpdate → updated → beforeDestroy → destroyed`. `created` fires after reactive data/computed/methods are set up but *before* the component is in the DOM (no `this.$el` yet) — good for API calls that don't touch the DOM. `mounted` fires *after* the component is inserted into the DOM — this project's near-universal pattern is `mounted: function () { this.fetchX(); }`, i.e., fire the initial data load once the component exists. `beforeMount` is the instant before the render happens — practically identical timing to `created` for most purposes but with the render function compiled; **the practical difference asked in vivas**: `created` = data ready, DOM not yet touched; `mounted` = DOM now exists and is queryable.
- **`v-if` vs `v-show`**: `v-if` actually adds/removes the element from the DOM (and destroys/recreates any component state under it) — better when the condition rarely flips or the content is expensive. `v-show` always renders the element but toggles CSS `display:none` — cheaper for frequently-toggled UI since no re-render/DOM patch cost, but the element (and any listeners) always exist. This project uses `v-if` almost everywhere (e.g., `v-if="loading"` spinners, `v-if="error"` alerts) since those states don't flip rapidly.
- **`computed` vs `watch`**: `computed` properties are cached, declarative, derived values recalculated only when their reactive dependencies change (e.g., `AdminCompanies.js`'s `pendingIds`/`isAllSelected` — pure functions of `companies`/`selected`). `watch` is imperative — you write a handler that runs a side effect (an API call, a state reset) *in response to* a specific reactive value changing — used throughout for reacting to `$route.query` changes (see `AdminCompanies.js`, `BrowseDrives.js`, `DriveDetail.js`) to refetch data whenever the URL's query/params change. Rule of thumb often stated in vivas: *"use computed when you need a value, watch when you need to do something."*
- **`$route` vs `$router`**: `$route` is the **current** route object (read-only-ish — `.query`, `.params`, `.path` of where you are right now); `$router` is the **router instance** you call methods on to navigate (`$router.push(...)`, `$router.replace(...)`). `AdminCompanies.js` reads `this.$route.query.q` on load and calls (indirectly, via URL update) navigation; `Login.js`/others call `self.$router.push(dest)` after a successful action.
- **Axios**: a promise-based HTTP client used instead of raw `fetch` for its **interceptors** (see `config.js` — request interceptor injects the JWT header on every call automatically; response interceptor centrally handles 401/403 across the whole app without repeating that logic in every component) and automatic JSON (de)serialization.
- **`const` vs `let`**: `const` — binding cannot be reassigned after declaration (used for the Axios instance `var api = axios.create(...)` — actually this project mostly uses `var`, since it's written in an ES5-compatible, no-build-step style for broad browser compatibility without transpilation; but for any modern JS asked about generically: `const` = block-scoped, no reassignment; `let` = block-scoped, reassignable; both fix `var`'s function-scoping/hoisting quirks). *(Note: check your actual component files — most of this codebase deliberately uses `var`/`function` syntax, not `const`/`let`/arrow functions, likely for CDN/no-transpiler compatibility. Know this if asked "why var and not let/const here.")*

### Storage types
- **Local Storage**: persists until explicitly cleared, no expiry, ~5-10MB, accessible from any tab/window of the same origin, **synchronous** API. This project stores the JWT + role + user_id + email here (`config.js`'s `window.auth`).
- **Session Storage**: same API, but scoped to a single tab and cleared when that tab closes.
- **Cookies**: sent automatically with every HTTP request to the matching domain (can be marked `httpOnly`/`Secure`/`SameSite`), much smaller (~4KB), can carry an expiry. **This project deliberately does NOT use cookies for the JWT** — a legitimate discussion point: cookie+httpOnly would be more XSS-resistant than localStorage, but requires more CSRF-protection plumbing and doesn't play as simply with "attach header via Axios interceptor."

### Git
- **Git vs VCS**: VCS (Version Control System) is the general category of tools/concepts for tracking changes to files over time (centralized like SVN, or distributed like Git/Mercurial). **Git is one specific, distributed implementation of a VCS** — "another name for VCS" isn't really accurate; Git is *a* VCS, not a synonym for the whole category. Distributed means every clone has the full history (vs. centralized VCS where only the server does).
- **Client-server vs distributed architecture** (generic CS, but tie back): client-server = clients depend on one central authority to function (e.g., a centralized VCS server, or this app's Flask backend that all Vue clients depend on); distributed = no single authoritative node, every peer has a full copy/can operate independently (e.g., Git).

### Celery / Redis / Caching — see doc v1 §8 and §10 for the detailed version; short answers:
- **What are you caching?** Three read-heavy endpoints: unfiltered student drives list, admin companies search results, admin students search results (`cache_keys.py`).
- **Where's the caching code?** `cache_keys.py` (key naming + safe wrappers + namespace invalidation), used from `routes/admin.py` and `routes/student.py`; configured via `Config.CACHE_TYPE='redis'` in `config.py`, initialized via `cache.init_app(app)` in `app.py`.
- **Celery config/mechanism**: `extensions.py`'s `make_celery()` builds a `Celery` instance bound to Redis (broker + result backend), wraps every task in a Flask app-context (`ContextTask`), and beat-schedules are declared declaratively in `config.py`'s `CELERYBEAT_SCHEDULE`. Run via `celery -A celery_worker.celery worker` / `... beat`.

---

## PART D — Likely Live Coding Tasks (practice these cold)

Based on the pattern "write a route that returns X for Y" / "add a Vue route/component" seen repeatedly:

**1. Backend — "list all drives posted by a specific company" (admin-facing variant of an existing filter):**
```python
@admin_bp.route('/companies/<int:company_id>/drives')
@admin_required
def company_drives(company_id):
    company = Company.query.get(company_id)
    if not company:
        return jsonify({'msg': 'Company not found.'}), 404
    drives = PlacementDrive.query.filter_by(company_id=company_id)\
        .order_by(PlacementDrive.created_at.desc()).all()
    return jsonify([serialize_drive(d) for d in drives]), 200
```
(Note: `admin.py :: drives()` already supports `?company_id=`, so this is really "extract that into its own dedicated path" — good to point that out if asked to justify the design.)

**2. Backend — "list applications for a given student, admin view" (already exists as `student_detail`, but practice writing it standalone):**
```python
@admin_bp.route('/students/<int:student_id>/applications')
@admin_required
def student_applications(student_id):
    apps = Application.query.filter_by(student_id=student_id)\
        .order_by(Application.applied_at.desc()).all()
    return jsonify([serialize_application_for_student(a) for a in apps]), 200
```

**3. Frontend — new Vue route + component showing a filtered list, `vue-router` navigation by id:**
```js
// routes array addition:
{ path: 'companies/:id/drives', component: AdminCompanyDrives },

// AdminCompanyDrives.js
const AdminCompanyDrives = {
  data: function () { return { drives: [], loading: true, error: '' }; },
  mounted: function () { this.fetch(); },
  watch: { '$route.params.id': function () { this.fetch(); } },
  methods: {
    fetch: function () {
      var self = this;
      self.loading = true;
      window.api.get('/admin/companies/' + this.$route.params.id + '/drives')
        .then(function (res) { self.drives = res.data; })
        .catch(function (err) { self.error = 'Failed to load.'; })
        .finally(function () { self.loading = false; });
    }
  },
  template: '<div>...</div>'
};
```
Practice writing an **invalid-id guard** too (several reports explicitly ask for this): if the fetch 404s, show an error state instead of a blank/broken page.

**4. Cosmetic changes** (asked very frequently — practice finding these fast):
- Background color → `templates/index.html`'s inline `<style>` block, `body { background-color: ... }`.
- Text color → likely a Bootstrap utility class swap in a component's template string (e.g. add `text-purple`/inline `style` to a heading), or a new rule in the same `<style>` block.
- Move an element (e.g. "login link to top-right of Register page") → find `Register.js`'s template string, relocate the `<router-link>` markup, likely wrapping it in a flex/position utility.

**5. Making a field editable end-to-end** (asked explicitly in one report — "edit info entered at signup"): e.g. adding `education` editing to `StudentProfile.js` if it weren't already there — pattern to follow: (a) confirm backend `PUT /student/profile` already accepts the field (`update_profile()` does, via `if 'education' in data:`), (b) add the input + `v-model` in the frontend template, (c) include it in the payload sent by the save handler, (d) confirm the serializer returns it so the UI reflects the save.

**6. Full-stack toy example seen in reports** ("Vue route + list + detail + conditional color"): practice building, from scratch, a two-route mini feature — `/things` (list, click a row) → `/things/:id` (detail, color a number red/green by threshold) — with an invalid-id fallback. This project's `BrowseDrives.js` → `DriveDetail.js` pair is structurally the same pattern; use it as your mental template.

---

## PART E — Logical Additions / Improvements Worth Mentioning (short)

If asked "how would you improve this," these are honest, defensible answers grounded in what's actually in the code:

1. **JWT has no expiry** (`JWT_ACCESS_TOKEN_EXPIRES = False`) — fine for dev, but production should set a real expiry + refresh-token flow, since a stolen token currently never dies on its own.
2. **JWT stored in `localStorage`**, not an httpOnly cookie — XSS-vulnerable (any injected script can read `localStorage` and steal the token). A cookie-based approach trades this for needing CSRF protection instead.
3. **Old resume/offer-letter files are never deleted** when a new one is uploaded (`upload_resume()` just overwrites the `resume_path` pointer) — disk usage grows unbounded; a cleanup step (`os.remove` on the old path before saving the new one) is a natural addition.
4. **Admin resume download has no extra scoping check** (any admin can view any resume — arguably fine since it's admin, but inconsistent with the company version which is tightly scoped via `_has_applied_to_company()`) — worth explicitly calling out the *asymmetry* as a deliberate design choice you can defend either way.
5. **No pagination** on any list endpoint (`Student.query.all()`, `Application.query.all()`, etc.) — fine at demo scale (10 students), but would need `LIMIT`/`OFFSET` or cursor pagination for a real institute with thousands of students/applications.
6. **Email sending silently no-ops without SMTP creds** — good for dev, but there's no admin-facing indicator in the UI that emails aren't actually being sent; a small "email delivery: disabled (dev mode)" banner in the admin dashboard would be an easy, visible improvement.
7. **No rate limiting** on `/api/auth/login` — brute-force protection (e.g., Flask-Limiter) is a natural addition given passwords are checked directly.
8. **The generic `/api/*` Flask-RESTful layer (`routes/api.py`) has zero auth** — if it's meant to stay in the final app rather than be a standalone teaching example, it should get the same `@admin_required`-style protection as everything else; as-is, it's an unauthenticated read/write surface onto Students/Drives.
9. **Cache/DB race window** (documented honestly in `cache_keys.py` itself) — between `db.session.commit()` and the invalidation call, a concurrent read could populate the cache with soon-to-be-stale data; the 5-minute TTL is the stated backstop, not a full fix. A message-queue-based invalidation (or shorter TTL) would tighten this further.
10. **No soft-delete** — `delete_company`/`delete_student`/`delete_drive` are hard deletes that cascade-remove all related Applications/Interviews/Placements permanently; an institute would likely want an audit-preserving soft-delete (`is_deleted` flag) instead, especially since `ApplicationStatusLog` already shows the project cares about audit trails elsewhere.
