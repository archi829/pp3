# Placement Portal — Viva Prep v3
### Additional theory Q&A + a full "changes they might ask you to make live" bank, all mapped onto YOUR actual codebase

This is a third pass, built from a much larger batch of real reports (665 submissions). Most of these reports are from a **different project** (a trek-booking app), but the proctors clearly draw from a **shared question/task bank** across projects — so every "trek" question below is translated into its placement-portal equivalent, and every coding task is answered with real, working code against your actual files.

---

## PART F — New Theory Questions (not covered in v1/v2), Answered for This Project

### SQLAlchemy relationship internals
- **`uselist=False`** — makes a `db.relationship()` return a single object instead of a list; used for a true **one-to-one** relationship (e.g., a `User` with exactly one `Profile`). **This project has none** — every relationship here (`Company.drives`, `Student.applications`, `Application.interviews`, `Application.status_log`) is genuinely one-to-many, so `uselist` is never set and defaults to `True` (list-returning). Good, honest answer if asked: *"I don't have a 1:1 relationship in this schema, so I haven't needed `uselist=False` — if I added e.g. a one-row `CompanyBillingProfile` per `Company`, that's where I'd use it."*
- **`cascade` values** — this project uses `'all, delete-orphan'` on 4 relationships (`Company.drives`, `Student.applications`, `PlacementDrive.applications`, `Application.interviews`, `Application.status_log`). `'all'` bundles save-update/merge/refresh-expire/expunge/delete; `'delete-orphan'` additionally deletes a child row the moment it's *disassociated* from its parent (not just when the parent itself is deleted). **What happens if cascade isn't used?** SQLAlchemy's default cascade is `'save-update, merge'` — deleting a parent (e.g. a `Company`) would **not** auto-delete its `PlacementDrive` rows; you'd either get a `FOREIGN KEY constraint failed` (if the DB enforces FKs, which SQLite does when `PRAGMA foreign_keys=ON`) or, worse, orphaned rows silently left pointing at a deleted company. This is exactly why `models.py` declares cascade explicitly everywhere a parent-delete should ripple down.
- **`lazy` values** (this project uses the default, `lazy=True` ≈ `'select'`, everywhere):
  - `'select'` (default) — separate query fired **only when you access the attribute** (e.g. `drive.company` fires a fresh query at that moment). Simple, but can cause N+1 queries in a loop.
  - `'joined'` — eager-loads via SQL `JOIN` in the *same* query as the parent. Fewer round-trips, but always pays the join cost even if you don't need the child.
  - `'subquery'` — eager-loads via a second query using a subquery, better than `'joined'` for one-to-many where a JOIN would duplicate parent rows.
  - `'dynamic'` — returns a **`Query` object**, not a list, so you can further `.filter()`/`.order_by()` it before executing. Useful for a relationship you never want to load in full (e.g., a company with thousands of drives) — **not used here** since the seeded dataset is small enough that `.all()`-style access everywhere is fine, but a legitimate improvement to flag for `Application.query.filter_by(drive_id=...)`-style large collections.

### Serialization pattern (not a single `to_dict()` here — worth explaining the difference)
This project does **not** put a `to_dict()` method on the models themselves. Instead, every route file defines its own **free-standing serializer functions** (`serialize_company()`, `serialize_drive()`, `serialize_student_summary()` vs `serialize_student_detail()`, `serialize_application()`, etc.) right above the routes that use them. If asked "why not `to_dict()` on the model," a defensible answer: *"Different roles need different views of the same row — e.g., `admin.py`'s `serialize_student_summary()` (list view) vs `serialize_student_detail()` (detail view, includes resume/education) vs `student.py`'s own `serialize_student()` (self-view, includes `is_active`). A single `to_dict()` on the model would either need to always return everything (leaking fields) or grow parameters for every view — keeping serializers in the route layer, one per shape-of-response, keeps the model itself dumb and the views explicit."* (Legitimate improvement to mention: this does cause some duplication — `serialize_company()` is defined near-identically in both `admin.py` and `company.py`; a shared `serializers.py` module would DRY this up.)

### Decorators / `@jwt_required` / `@admin_required`
- **What does `@jwt_required()` do?** A Flask-JWT-Extended decorator that runs before the view function: extracts the JWT from the `Authorization: Bearer <token>` header, verifies its signature against `JWT_SECRET_KEY`, checks it hasn't expired/been revoked, and populates `get_jwt_identity()`/`get_jwt()` for the view to use. If verification fails, it short-circuits straight to the `@jwt.unauthorized_loader`/`@jwt.invalid_token_loader`/`@jwt.expired_token_loader` handlers registered in `app.py` — the view function body never runs.
- **How does `@admin_required` work, concretely (walk the code)?**
```python
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()                    # step 1: same JWT verification as @jwt_required()
        if get_jwt().get('role') != 'admin':        # step 2: read the 'role' claim baked in at login
            return jsonify({'msg': 'Admins only.'}), 403
        return fn(*args, **kwargs)                  # step 3: only now does the real route run
    return wrapper
```
It's a **custom decorator that wraps `@jwt_required()`'s logic** (via `verify_jwt_in_request()`) plus an extra role check, rather than stacking two separate decorators — this lets it return a clean single `403` message instead of `@jwt_required` and a second role-check decorator each independently trying to short-circuit. `@wraps(fn)` (from `functools`) preserves the original function's `__name__`/docstring, which Flask needs for its URL-rule/endpoint-naming machinery to not collide.

### `db.session.add()` vs `db.session.commit()`
- **`add()`** stages an object into the current session as *pending* — it is now tracked/dirty but **not yet written to the database**. No SQL has run yet (aside from a possible `flush()` some ORMs trigger automatically before certain queries).
- **`commit()`** flushes all pending changes as SQL (INSERT/UPDATE/DELETE) inside a transaction and then commits that transaction — this is the point the row actually exists in `placement_portal.db` and other connections can see it. It's also the point auto-increment primary keys (like `application.id`) get populated onto your Python object.
- **Why does `student.py :: apply()` call `db.session.flush()` before `commit()`?**
```python
db.session.add(application)
db.session.flush()                       # forces an INSERT now, so application.id exists...
_log_status(application.id, None, 'Applied', 'student', student.id)   # ...needed here, as an FK
db.session.commit()                        # commits BOTH rows together, one transaction
```
`flush()` pushes pending SQL to the DB **without ending the transaction** — it's the tool for "I need this row's generated PK *right now*, to use as a foreign key on a second row I'm about to add in the same transaction," without prematurely committing (so if something later fails, the whole thing still rolls back together). Same pattern is used in `company.py :: select_application()` before creating a `Placement`.

### If you delete the SQLite file and rerun — **know your project's actual behavior here, it's a common trap question**
`app.py`'s `create_app()` calls `db.init_app(app)` but **never calls `db.create_all()`**. Only `init_db.py` calls `db.create_all()` (and `db.drop_all()` first). So: **if you delete `placement_portal.db` and just run `python app.py`, the tables will NOT be recreated** — every DB query will raise `sqlite3.OperationalError: no such table`. You must rerun `python init_db.py` to regenerate the schema (and it will also re-seed dummy data, since `drop_all()`+`create_all()`+the seed logic all live in that one script). **Be ready to say this exact thing if asked** — some other students' projects auto-create tables inside `create_app()` itself; this one deliberately doesn't, keeping "create schema" and "run server" as separate, explicit steps.

### CORS
- **What is CORS?** Cross-Origin Resource Sharing — a browser security mechanism that blocks a page loaded from origin A from making certain fetch/XHR requests to origin B unless B's server explicitly allows it via `Access-Control-Allow-Origin` (and related) response headers.
- **How is it configured here?**
```python
cors.init_app(app, origins=["http://localhost:5000"])
```
Since Flask serves both the API *and* the Vue SPA shell from the same host/port (`localhost:5000`), this app is technically **same-origin** already — CORS wouldn't even need to be enabled for the deployed setup to work. It's there (per `app.py`'s own comment) to support the alternate dev workflow of running the Vue files off a separate dev server (e.g. `http://localhost:5173`) while pointing at this Flask backend — the comment in the code literally says to add that origin to the list if you do that.

### Primary key vs unique key
- A **primary key** uniquely identifies a row, cannot be `NULL`, and a table can have only **one**. A **unique key/constraint** also enforces uniqueness but *can* allow one `NULL` (in most DBs) and a table can have **many** unique constraints. **Can a unique key be a primary key?** Every primary key *is* implicitly unique (that's part of its definition), but not every unique column is *the* primary key — e.g., `Student.email` has `unique=True` in this schema but `Student.id` is the primary key; `email` could theoretically have been chosen as the PK instead, but using a separate surrogate integer `id` is the more common/flexible pattern (emails can need to change; an immutable numeric id is cleaner as the thing every FK points to).
- **Foreign key** in this schema, concretely: `PlacementDrive.company_id → Company.id`, `Application.student_id → Student.id`, `Application.drive_id → PlacementDrive.id`, `Interview.application_id → Application.id`, `Placement.{student_id,company_id,drive_id}`, `ApplicationStatusLog.application_id → Application.id`.

### Many-to-many
- **Does this schema have a many-to-many relationship?** Conceptually yes: a Student can apply to many Drives, and a Drive can receive applications from many Students — classic M:N. But it's **not** implemented as a bare `db.Table` association/secondary table, because the relationship needs **extra columns** (`status`, `applied_at`, `offer_status`, `cover_letter`, `student_notes`) that a plain secondary table can't hold. Instead it's modeled as its own first-class entity: **`Application`**, with two separate one-to-many relationships (`Student → Application`, `PlacementDrive → Application`) plus the `UniqueConstraint(student_id, drive_id)` doing the job a M:N secondary table's composite key would normally do. This is the standard **"association object" pattern** (vs. a plain "association table") in SQLAlchemy — used specifically *because* you need attributes on the relationship itself, not just the link.

### Structured vs unstructured data
- **Structured**: fixed schema, tabular, strongly typed columns — this entire project (SQLite via SQLAlchemy models). **Unstructured/semi-structured**: no fixed schema (e.g. raw JSON blobs, log files, freeform text). This project keeps things structured throughout, though a few columns are loosely-structured freeform text used more like semi-structured data in practice — e.g. `Student.skills` and `Student.education` are just `db.Text` (comma-separated strings, not normalized into their own `Skill`/`Education` tables) — worth flagging as a design trade-off (simplicity vs. queryability — you can't efficiently query "all students who know Python" with a proper JOIN today; you'd need an `ilike('%Python%')` scan).

### Scaling
- **Vertical scaling**: give the *existing* single server more resources (more CPU/RAM/disk) — simple, but has a hard ceiling and is a single point of failure.
- **Horizontal scaling**: add *more* servers/instances and distribute load across them (e.g., multiple Flask app instances behind a load balancer, multiple Celery workers consuming from the same Redis broker). **This project is already structured to horizontally scale on the worker side** — you can run `celery -A celery_worker.celery worker` on multiple machines/processes against the same Redis broker with zero code changes, since Celery workers are stateless consumers of the queue. The Flask app itself would need session/JWT state to stay stateless (which it already is — JWT means no server-side session store) and the SQLite database would need to become a real client-server DB (Postgres/MySQL) since SQLite doesn't handle concurrent writers from multiple app servers well.

### Testing
- If asked "how did you test this": be honest about what actually exists. **There is no automated test suite in this repo** (no `tests/` folder, no pytest). Legitimate answer: *"Testing here was manual — exercising each role's flows through the UI, and I used the seeded data from `init_db.py` (Pending/Approved/Rejected companies, mixed application statuses) specifically so every state-dependent code path had a demo-able example without me hand-creating edge cases each time."* If pushed on "how would you add real tests" — pytest + Flask's test client, hitting the JSON endpoints directly (no need to render Vue at all, since backend is a pure API), plus a separate test SQLite DB (or in-memory `sqlite:///:memory:`) via a `TestConfig`.

### Logs / debugging a crash
- **"If the app crashes, what's the first thing you check?"** → **check the logs** (stated explicitly as the expected answer in one report). Concretely for this project: Flask's dev server console output (stack traces), and for background jobs, the **Celery worker's own console output** (since task exceptions don't surface to the HTTP response at all — a failed task just shows `FAILURE` when polled, with the real traceback only visible in the worker's log). This project's `app.py` also adds an `X-Response-Time` header via `before_request`/`after_request` hooks — not full logging, but a lightweight per-request timing signal that could be extended into real structured logging (e.g. Python's `logging` module writing to a file, or an APM tool) — a fair "industry standard" improvement to mention if a proctor pushes on this.

### JS fundamentals
- **`const`/`let`/`var`**: **This project's actual style is `var` + `function` everywhere inside component method bodies**, with `const` used only for the top-level `const ComponentName = {...}` declarations (verified: `Login.js`, `AdminLayout.js`, etc. all start with `const X = {`). If a proctor asks "why `const` and not `let`/`var` for that" — because the component object itself is **never reassigned** after being defined (only its *properties*, like `data()`'s return values, ever change at runtime) — `const` communicates "this binding won't be re-pointed at a different object," which is exactly true here. Internally, though, this codebase deliberately avoids `let`/arrow functions/template literals-as-syntax-only in method bodies and sticks to `var self = this; ... function(){...}` — almost certainly for **maximum browser compatibility with zero transpilation step**, since there's no Babel/webpack build (see Part on SPA/no-build-step in v1). Good talking point: *"I chose ES5-style `var`/`function` inside methods specifically because this app has no build step — it's loaded straight via `<script>` tags off a CDN, so whatever syntax I write is exactly what runs in the browser, unminified and untranspiled."*
- **JS typing**: JavaScript is **dynamically typed** (a variable's type is determined and can change at runtime, not declared ahead of time) and **weakly typed** (implicit coercion happens, e.g. `'5' + 3 === '53'`) — contrast with Python, which is dynamically but *strongly* typed (no implicit `str`+`int` coercion).
- **`=` vs `==` vs `===`**: `=` is assignment. `==` is loose equality (coerces types before comparing — e.g. `'5' == 5` is `true`). `===` is strict equality (no coercion — `'5' === 5` is `false`). This codebase's comparisons (e.g. `application.status === new_status` — actually that's Python `==`, since backend logic is Python; on the JS/Vue side, comparisons like `c.approval_status === 'Pending'` in `AdminCompanies.js`'s `pendingIds` computed property) consistently use `===`, which is the standard best practice specifically to avoid `==`'s coercion surprises.

### Vue-specific: props, directives, Vuex/Pinia, CLI vs CDN
- **Props** (real example from this exact codebase): `LoadingSpinner.js` and `ErrorAlert.js` are the **only two components in the entire app that declare `props`**:
```js
Vue.component('loading-spinner', {
  props: { label: { type: String, default: 'Loading…' } },
  template: '<div class="text-center py-5">...{{ label }}...</div>'
});
Vue.component('error-alert', {
  props: { message: { type: String, default: '' } },
  template: '<div v-if="message" ...>{{ message }}<button @click="$emit(\'dismiss\')">×</button></div>'
});
```
Usage elsewhere: `<error-alert :message="error" @dismiss="error = ''"></error-alert>` — this shows both **props down** (`:message="error"` passes the parent's `error` data down as the child's `message` prop) and **events up** (`@dismiss="..."` listens for the child's `$emit('dismiss')` and runs a parent handler) — the standard Vue "props down, events up" one-way data flow. Every *other* component in the app is a page-level route component with no children of its own, so this pair is your best (and only) real example to demo if asked to "show a prop."
- **Directives**: template attributes prefixed `v-` that apply reactive behavior to the DOM. Used throughout: `v-if`/`v-else` (conditional render), `v-for` (list render), `v-model` (two-way input binding), `v-bind`/`:` shorthand (bind an attribute to an expression), `v-on`/`@` shorthand (bind an event handler), `v-show` (toggle CSS display — rarely used here, see v2's Part C).
- **Vuex/Pinia**: **not used anywhere in this project.** There is no centralized store. Cross-component "shared state" is handled two ways instead: (1) `localStorage` via `window.auth` for the tiny bit of truly global state (JWT/role/user_id/email), and (2) every page-level component independently fetches its own data via `window.api` in its own `mounted()` hook — there's no Vuex `state`/`getters`/`mutations`/`actions` layer at all. If asked "Vuex mutation vs action" generically: a **mutation** synchronously and directly changes store state (the *only* sanctioned way to mutate Vuex state, so devtools can track every change); an **action** can contain async logic (e.g., an API call) and, once it resolves, **commits** a mutation to actually apply the result — actions orchestrate, mutations apply.
- **`data` vs `store`**: `data()` is state scoped to **one component instance**; a store (Vuex/Pinia) is state shared **globally** across every component without prop-drilling. This project has no store, so every component's `data()` is truly private to it — the closest thing to shared state is re-fetching from the backend on each page load (e.g., both `StudentDashboard.js` and `BrowseDrives.js` independently call `/student/drives`-related endpoints rather than reading from a shared client-side cache).
- **Options API vs Composition API**: This project uses **Options API exclusively** (`data()`, `methods: {}`, `computed: {}`, `watch: {}` as separate object keys) — the only API Vue 2 supports natively. Composition API (`setup()`, `ref()`, `reactive()`) is a Vue 3 concept (backported to Vue 2 via a plugin, not used here). If asked to compare: Composition API groups code **by logical concern** (all the state+logic for one feature together) rather than **by option type** (all `data` together, all `methods` together) — better for large components with many unrelated concerns, arguably unnecessary for this project's small, single-purpose page components.
- **`ref` vs `reactive`** (Vue 3 Composition API, not used here, but the generic answer): `ref()` wraps a *primitive* (or anything) in a reactive object with a `.value` accessor; `reactive()` makes an *object* deeply reactive directly, no `.value` needed, but can't wrap primitives directly (an ref itself is a `reactive`-wrapped `{value: x}` under the hood). Honest answer if asked: *"This project uses Vue 2 Options API, so I haven't used `ref`/`reactive` — Vue 2 achieves reactivity by walking `data()`'s object properties with `Object.defineProperty` getters/setters instead."*
- **Vue CLI vs Vue CDN**: CLI (`vue create`) scaffolds a full build pipeline (webpack/vite, `.vue` Single-File Components with `<template>`/`<script>`/`<style>` blocks, hot-module-reload, npm dependency management, a `dist/` build step). **This project uses the CDN approach** — Vue/Vue-Router/Axios loaded as plain `<script src="https://cdn...">` tags in `templates/index.html`, components are plain `.js` files with template-as-a-string, **no build step, no `.vue` files, no npm for the frontend at all.** Trade-off: zero tooling complexity and instant "just open the file and it works," at the cost of no `.vue` SFC ergonomics, no tree-shaking, no minification, and (as discussed above) no modern JS syntax you can't run unmodified in-browser.
- **`meta` in vue-router**: arbitrary metadata attached to a route definition, read later in navigation guards or components. This project's only use: `meta: { role: 'admin' | 'company' | 'student' }` on each top-level role route, consumed entirely inside `router.beforeEach()` to gate access. Other common uses elsewhere (not present here): `meta: { requiresAuth: true }`, `meta: { title: '...' }` for `document.title`, breadcrumb labels, transition names.

### Webhook
- A **webhook** is a server-to-server, event-driven HTTP callback: instead of Service A *polling* Service B for updates, B calls a URL A registered ahead of time the moment something happens (a "reverse API call"). **This project doesn't implement or consume any webhooks** — its background-job result delivery uses **polling** instead (`GET /export/status/<task_id>` called repeatedly by the frontend every 3 seconds — see v1/v2), which is the *opposite* pattern. If asked to compare directly: a webhook push is answered instantly and needs no repeated requests, but requires the receiver to expose a publicly reachable endpoint and handle the push (harder in a pure-frontend SPA); this project's polling approach is simpler to reason about and needs no public callback endpoint, at the cost of some latency (up to ~3s) and repeated wasted requests while a job is still pending.

### Cache vs memoize
- **Caching** is the general strategy of storing *any* expensive-to-recompute or expensive-to-fetch data somewhere faster to retrieve later — can be at any layer (HTTP responses, DB query results, computed values, whole pages) and can live outside the process (Redis, CDN). **Memoization** is a *specific technique*: caching the return value of a **pure function**, keyed by its input arguments, almost always in local process memory. This project's Redis caching (see v1 §8 / v2 Part C) caches **serialized HTTP response payloads** keyed by query-string parameters — closer to "response caching" than classical memoization, since the cached thing isn't a pure function's return value but a full DB-query-plus-serialization result, and it lives in Redis (out-of-process, shared across all workers) rather than in local memory.

### Why doesn't the app ask the user *where* to save the exported CSV?
This is a **browser-level concern, not something Flask controls.** The download endpoints use `send_from_directory(..., as_attachment=True)` (for offer letters) or the frontend just links to `/static/exports/<file>` — either way, the browser's native download behavior takes over: by default it saves to the OS's configured Downloads folder, or shows a Save-As dialog if the user's browser settings request one. The Flask app's job ends at setting the right `Content-Disposition: attachment` response header; it has no way to control OS-level file dialogs from server-side code, and doesn't need to — that's outside the HTTP request/response boundary entirely.

---

## PART G — The Big Coding-Task Bank (every "change" pattern seen, mapped to THIS project)

Organize your prep by pattern, not by literal question — proctors clearly reuse the same handful of task *shapes* across different students' different projects. Below: the pattern, then the exact code for **your** placement portal.

### G.1 — "Write a route to fetch all X with property Y" (the single most common ask)

**Pattern seen**: *"blacklisted trekkers/users", "trekkers who booked difficult trek", "fully booked treks", "shortlisted students"* — always "list of rows filtered by a status/flag."

```python
# GET /api/admin/students/blacklisted
@admin_bp.route('/students/blacklisted')
@admin_required
def blacklisted_students():
    students = Student.query.filter_by(is_blacklisted=True)\
        .order_by(Student.created_at.desc()).all()
    return jsonify([serialize_student_summary(s) for s in students]), 200


# GET /api/admin/students/shortlisted  — "which students are Shortlisted right now"
@admin_bp.route('/students/shortlisted')
@admin_required
def shortlisted_students():
    apps = Application.query.filter_by(status=ApplicationStatus.SHORTLISTED).all()
    student_ids = {a.student_id for a in apps}
    students = Student.query.filter(Student.id.in_(student_ids)).all()
    return jsonify([serialize_student_summary(s) for s in students]), 200


# GET /api/admin/drives/full — "fully booked" analog: drives whose applicant count
# has reached a capacity limit. NOTE: this project has NO capacity field today
# (PlacementDrive has no max_applicants column) — say this out loud if asked, then
# show the addition:
#   1. models.py: add  max_applicants = db.Column(db.Integer, nullable=True)
#   2. this route becomes:
@admin_bp.route('/drives/full')
@admin_required
def full_drives():
    drives = PlacementDrive.query.filter(
        PlacementDrive.max_applicants.isnot(None)
    ).all()
    full = [d for d in drives if len(d.applications) >= d.max_applicants]
    return jsonify([serialize_drive(d) for d in full]), 200
```
**Good thing to say explicitly**: *"My project computes applicant counts on the fly (`len(d.applications)`) rather than storing a counter column, so there's no counter that could accidentally drift or go negative — a structural difference from a naive slot-counting design that increments/decrements a stored integer."* This directly answers the recurring "how do you prevent overbooking / going negative" question family — **in this project the equivalent risk doesn't exist by construction**, because nothing is decremented; count is always derived fresh from the actual row count.

### G.2 — "Write a route parameterized by name/company_name, plus a frontend input + button to call it"

```python
# Backend
@admin_bp.route('/companies/by-name/<string:company_name>/drives')
@admin_required
def drives_by_company_name(company_name):
    company = Company.query.filter(Company.company_name.ilike(company_name)).first()
    if not company:
        return jsonify({'msg': 'Company not found.'}), 404
    drives = PlacementDrive.query.filter_by(company_id=company.id)\
        .order_by(PlacementDrive.created_at.desc()).all()
    return jsonify([serialize_drive(d) for d in drives]), 200
```
```js
// Frontend snippet — v-model input + button + rendered list, Options API style
// matching this project's conventions
const CompanyDriveLookup = {
  data: function () {
    return { companyName: '', drives: [], loading: false, error: '' };
  },
  methods: {
    getDrives: function () {
      var self = this;
      self.loading = true;
      self.error = '';
      window.api.get('/admin/companies/by-name/' + encodeURIComponent(self.companyName) + '/drives')
        .then(function (res) { self.drives = res.data; })
        .catch(function (err) {
          self.error = (err.response && err.response.data && err.response.data.msg) || 'Not found.';
        })
        .finally(function () { self.loading = false; });
    }
  },
  template:
    '<div class="container mt-4">' +
    '  <input v-model="companyName" placeholder="Company name" class="form-control mb-2">' +
    '  <button class="btn btn-dark" @click="getDrives">Get Drives</button>' +
    '  <error-alert :message="error" @dismiss="error = \'\'"></error-alert>' +
    '  <ul class="list-group mt-3">' +
    '    <li class="list-group-item" v-for="d in drives" :key="d.id">{{ d.job_title }}</li>' +
    '  </ul>' +
    '</div>'
};
```

### G.3 — "Simple POST route that accepts JSON, creates a row, commits"

```python
@admin_bp.route('/students', methods=['POST'])
@admin_required
def create_student():
    data = request.get_json(silent=True) or {}
    full_name = (data.get('full_name') or '').strip()
    email     = (data.get('email') or '').strip().lower()
    password  = data.get('password', '')

    if not full_name or not email or not password:
        return jsonify({'msg': 'full_name, email and password are required.'}), 400
    if Student.query.filter_by(email=email).first():
        return jsonify({'msg': 'Email already registered.'}), 409

    student = Student(
        full_name=full_name, email=email,
        password_hash=generate_password_hash(password),
    )
    db.session.add(student)
    db.session.commit()
    invalidate_namespace('admin_students')
    return jsonify({'id': student.id, 'msg': 'Student created.'}), 201
```
(This is literally the same shape as `auth.py :: register_student()` with the file-upload parts stripped out — good to point out you're reusing an existing pattern, not inventing new conventions.)

### G.4 — "Add a new Vue page + connect it via the router" (the "Hello.vue" / new-page task)

```js
// static/js/components/admin/AdminHello.js
const AdminHello = {
  template: '<div class="container mt-4"><h3>Hello, Admin!</h3></div>'
};
```
```html
<!-- templates/index.html, add before router.js -->
<script src="{{ url_for('static', filename='js/components/admin/AdminHello.js') }}"></script>
```
```js
// static/js/router.js — inside the /admin children array:
{ path: 'hello', component: AdminHello },
```
Now `/admin/hello` renders it. **Say the load-order rule out loud** — the component's `<script>` tag must appear *before* `router.js`'s tag in `index.html`, since `router.js` references the global `AdminHello` const at parse time.

### G.5 — "Placed student cannot apply to any further drive" ⭐ (by far the most-repeated single coding task across reports — practice this exact one)

This is the single most literal, directly-transferable task from the reports — do this one cold.

```python
# routes/student.py :: apply()  — add this check right after loading `drive`,
# before creating the Application row.
from models import Placement   # already imported at top of student.py

@student_bp.route('/applications', methods=['POST'])
@student_required
def apply():
    student = current_student()
    data = request.get_json(silent=True) or {}
    drive_id = data.get('drive_id')
    if not drive_id:
        return jsonify({'msg': 'drive_id is required.'}), 400

    # ── NEW: block already-placed students ──────────────────────────────
    already_placed = Placement.query.filter_by(student_id=student.id).first()
    if already_placed:
        return jsonify({
            'msg': 'You have already been placed and cannot apply to further drives.'
        }), 403
    # ──────────────────────────────────────────────────────────────────

    drive = PlacementDrive.query.get(drive_id)
    if not drive:
        return jsonify({'msg': 'Drive not found.'}), 404
    # ...rest unchanged
```
**Why check the `Placement` table and not `Application.status == 'Selected'`?** Because `Placement` is the record that's actually created the moment a company confirms selection (`company.py :: select_application()`), and a student could in principle be `Selected` for one drive's application row while the *canonical* "are they placed" fact lives in `Placement`. Checking `Placement` directly is the more robust source of truth.

**Frontend side** — disable/hide the Apply button once placed:
```js
// DriveDetail.js — in mounted(), also fetch /student/placements once,
// or simpler: pass an `already_placed` flag down from StudentDashboard's
// existing dashboard payload (student.applications don't currently carry it,
// so the cleanest fix is a tiny new field on GET /student/dashboard's response:
// 'is_placed': Placement.query.filter_by(student_id=student.id).first() is not None
```
```html
<button class="btn btn-dark" @click="apply" :disabled="already_placed">
  {{ already_placed ? 'You are already placed' : 'Apply Now' }}
</button>
```

### G.6 — "Password validation: min 8 chars, 1 uppercase, 1 digit, 1 special char"

```python
import re

def _valid_password(pw):
    if len(pw) < 8: return False
    if not re.search(r'[A-Z]', pw): return False
    if not re.search(r'[0-9]', pw): return False
    if not re.search(r'[^A-Za-z0-9]', pw): return False
    return True

# in register_student() / register_company(), replace the existing
#   if len(password) < 6: ...
# with:
if not _valid_password(password):
    return jsonify({'msg': 'Password must be 8+ chars with an uppercase letter, a digit, and a special character.'}), 400
```

### G.7 — "Add a Confirm Password field to the registration form + block mismatch"

**Good news**: `auth.py :: register_student()` and `register_company()` **already accept and check `confirm_password` server-side** (`if confirm and password != confirm: return 400`). So this task, for this project, is **purely a frontend addition** — add the field + client-side pre-check for instant feedback:
```html
<input type="password" v-model="confirmPassword" placeholder="Confirm Password" class="form-control mb-2">
```
```js
submit: function () {
  if (this.password !== this.confirmPassword) {
    this.error = 'Passwords do not match.';
    return;
  }
  // ...existing window.api.post('/auth/register/student', { ..., confirm_password: this.confirmPassword })
}
```

### G.8 — "Prevent negative numeric inputs" (form validation)

This project's numeric inputs are `Student.cgpa` (already validated 0–10 both at registration and profile update — point this out proactively) and, if you add `PlacementDrive.max_applicants` per G.1, that would need the same treatment:
```python
raw = data.get('max_applicants')
if raw is not None:
    try:
        val = int(raw)
        if val < 1:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({'msg': 'max_applicants must be a positive integer.'}), 400
```

### G.9 — "Add a Delete button on an admin management page" (backend + frontend)

Already exists as a pattern (`DELETE /admin/companies/<id>`, `DELETE /admin/students/<id>`) — practice writing the frontend half cold:
```html
<button class="btn btn-sm btn-outline-danger" @click="confirmDelete(student)">
  <i class="bi bi-trash"></i> Delete
</button>
```
```js
confirmDelete: function (student) {
  var self = this;
  if (!confirm('Delete ' + student.full_name + '? This cannot be undone.')) return;
  window.api.delete('/admin/students/' + student.id).then(function () {
    self.students = self.students.filter(function (s) { return s.id !== student.id; });
    window.showToast(student.full_name + ' deleted.');
  });
}
```

### G.10 — "Delete-all button" (bulk destructive action)

```python
@admin_bp.route('/companies/rejected', methods=['DELETE'])
@admin_required
def delete_all_rejected_companies():
    companies = Company.query.filter_by(approval_status=ApprovalStatus.REJECTED).all()
    count = len(companies)
    for c in companies:
        db.session.delete(c)
    db.session.commit()
    invalidate_namespace('admin_companies')
    return jsonify({'msg': f'{count} rejected companies deleted.'}), 200
```
(Scoped to a specific subset — e.g. "all rejected" — rather than a truly unscoped delete-everything, which is a good instinct to voice if asked "would you really ship an unscoped delete-all?")

### G.11 — Live cosmetic edits (background/text color, move elements, sidebar side)

- **Background color / global text color**: `templates/index.html`'s inline `<style>` block — `body { background-color: #...; }`; for "all text purple," add `body { color: purple; }` (or target specific elements with more specific selectors if headings/buttons should stay their Bootstrap colors).
- **Table row color by status** (asked explicitly in one report): use a `:class` binding in the row's template — this project already has a natural place for this in every admin/company table:
```html
<tr v-for="c in companies" :key="c.id"
    :class="{ 'table-success': c.approval_status === 'Approved',
              'table-danger': c.is_blacklisted,
              'table-warning': c.approval_status === 'Pending' }">
```
- **Move an element / shift sidebar to the right**: find the layout component (`AdminLayout.js`/`CompanyLayout.js`/`StudentLayout.js`) — these define the persistent navbar/sidebar wrapping `<router-view>`. Swap the flex order (Bootstrap: add `order-2`/`order-1` utility classes, or reorder the markup itself) to move the sidebar `<nav>` after the `<router-view>` content in a `d-flex` container.
- **Login page "print email" / "show part after @"**: trivial — a new `@click` handler in `Login.js`:
```js
showEmailPart: function () {
  console.log(this.email);                          // print full email
  console.log(this.email.split('@')[1] || '');       // part after @
}
```

### G.12 — Celery scheduling changes

- **Change a beat schedule's interval**, e.g. run `send_interview_reminders` every 2 minutes instead of daily at 8am:
```python
# config.py — CELERYBEAT_SCHEDULE
'daily-interview-reminders': {
    'task': 'tasks.send_interview_reminders',
    'schedule': timedelta(minutes=2),   # was: crontab(hour=8, minute=0)
},
```
(Needs `from datetime import timedelta` imported in `config.py`; `crontab` is for calendar-based schedules, `timedelta` for fixed-interval "every N seconds/minutes" schedules — know this distinction, it's exactly the kind of thing a proctor probes.)

- **New periodic task that prints a multiplication table every N seconds** (a generic Celery-mechanics demo task, unrelated to placement logic but a common literal ask):
```python
# tasks.py
@celery.task(name='tasks.print_table')
def print_table(n=5):
    for i in range(1, 11):
        print(f'{n} x {i} = {n*i}')
    return {'printed_for': n}

# config.py — add to CELERYBEAT_SCHEDULE
'print-table-every-30s': {
    'task': 'tasks.print_table',
    'schedule': timedelta(seconds=30),
    'args': (7,),
},
```

### G.13 — "Remove the id column from the exported CSV"

```python
# tasks.py :: export_applications_csv() — change the header row and the loop:
writer.writerow([
    'Job Title', 'Company', 'Location', 'Salary Range',
    'Applied On', 'Status', 'Offer Status', 'Cover Letter'
])   # dropped 'Application ID'
for a in apps:
    writer.writerow([
        a.drive.job_title if a.drive else '',
        # ... drop a.id from the front of this row too
    ])
```

### G.14 — Filter companies by industry (frontend + verify backend already supports it)

**Backend already supports this** — `admin.py :: companies()` filters `Company.industry.ilike(like)` as part of its general `q` search. So the "task" is really: demonstrate it, and/or add a **dedicated** industry-only filter dropdown if asked for something more explicit than the free-text search box:
```python
@admin_bp.route('/companies/by-industry/<string:industry>')
@admin_required
def companies_by_industry(industry):
    companies = Company.query.filter(Company.industry.ilike(f'%{industry}%')).all()
    return jsonify([serialize_company(c) for c in companies]), 200
```

---

## PART H — Quick-Fire Answer Card (skim this right before joining)

| Q | A (this project) |
|---|---|
| DB deleted, rerun `app.py` — tables back? | **No** — `create_app()` never calls `db.create_all()`; only `init_db.py` does. Must rerun `python init_db.py`. |
| Does JWT survive refresh? Browser close? | **Yes to both** — `localStorage` has no expiry and isn't tab-scoped; token dies only on explicit logout, `localStorage.clear()`, or (in prod) hitting a set expiry — this dev build sets `JWT_ACCESS_TOKEN_EXPIRES = False`, so it truly never expires here. |
| `db.session.add()` vs `commit()` | `add()` stages, no SQL yet; `commit()` flushes+commits, row now exists, PK now populated. |
| `flush()` used where and why | `apply()` and `select_application()` — get a just-added row's auto PK before adding a second, FK-dependent row, without ending the transaction early. |
| CORS origin allowed | `http://localhost:5000` only (same-origin already since Flask serves the SPA itself). |
| Vuex/Pinia used? | No — no central store; `localStorage` for auth, per-component `mounted()` fetches for everything else. |
| Vue CLI or CDN? | CDN — no build step, plain `.js` files, `const Component = {...}` globals. |
| `props` used anywhere? | Only in `LoadingSpinner.js` (`label`) and `ErrorAlert.js` (`message`) — the app's only two reusable child components. |
| `meta` in router used for? | Just `{ role: 'admin'|'company'|'student' }`, read in `router.beforeEach()`. |
| `uselist=False` anywhere? | No — no 1:1 relationships in this schema. |
| M:N relationship? | Student↔Drive, mediated through `Application` (association-object pattern, not a bare secondary table, because it needs extra columns: status, applied_at, etc). |
| Automated tests? | None currently — manual testing against seeded data; legitimate improvement to name if pushed. |
| Webhooks used? | No — background job results are delivered via **polling** (`/export/status/<task_id>`), the opposite pattern. |
| Placed-student-can't-reapply — implemented? | Not by default in the base repo — practice adding it live exactly as in G.5 (this is the single most-repeated coding ask across reports). |
