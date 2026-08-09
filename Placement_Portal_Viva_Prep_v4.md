# Placement Portal — Viva Prep v4
### Fundamentals-level Q&A + live-coding tasks, from a deep architectural-style viva report

This proctor's style is different from the ones in v1–v3: fewer "sheet" questions, much more **first-principles drilling** — Node/npm, the DOM, HTTP itself, REST theory, sessions vs tokens, what "in-memory" physically means, `__init__.py` mechanics, hash routing. Assume "why" follow-ups on every answer. Everything below is checked against your actual code, not generic.

---

## PART J — Fundamentals Q&A (verified against this project)

### Node.js / npm — **this project uses neither, and that's a legitimate answer**
- **What is Node.js?** A JavaScript runtime built on Chrome's V8 engine that lets JS run **outside the browser** (on a server, in a CLI tool, in a build pipeline) — it adds things the browser JS environment doesn't have (filesystem access, process management, networking modules) while removing things it doesn't need (DOM, `window`).
- **What is npm?** Node.js's package manager — installs/manages JS dependencies (`package.json`, `node_modules/`), and runs build/dev scripts (`npm run build`, `npm run dev`).
- **Use case of Node in your project?** **Honest answer: none — I don't use Node.js or npm anywhere in this project.** Verified: no `package.json`, no `node_modules/`, no `.vue` Single-File Components, no Vite/webpack config anywhere in the repo. The entire frontend is Vue 2, Vue Router, and Axios loaded as plain `<script src="https://cdn...">` tags in `templates/index.html`, and every component is a plain `.js` file (`const ComponentName = {...}`) parsed directly by the browser with **zero build step**. If pushed on "so how did you get Vue at all without npm" — CDN delivery: the browser downloads Vue's pre-built bundle straight from a CDN URL at page-load time, exactly like it would download jQuery from a CDN — no local Node toolchain is involved at any point, dev or prod.
- **If asked "wouldn't Node help you here?"** — a fair, honest answer: *"Yes, a Node-based build step (Vite/webpack + `.vue` SFCs) would give me hot-module-reload, code-splitting, and cleaner component files with real `<template>`/`<script>`/`<style>` separation. I chose the CDN approach specifically to keep the project's toolchain minimal — no `npm install`, no build step, anyone can clone the repo and it runs immediately — a deliberate trade-off of developer ergonomics for zero-friction setup, appropriate for this project's scale."*

### Vue.js — why a framework at all, and could this be done in plain JS?
- **Why use a framework instead of plain JS?** Manually keeping the DOM in sync with changing data (re-querying elements, manually updating `innerText`/`innerHTML`/classes every time state changes, manually re-attaching event listeners after re-renders) becomes error-prone and verbose past a trivial app. Vue gives you **declarative, reactive templates** — you describe *what* the UI should look like as a function of `data`, and Vue's reactivity system (getter/setter interception in Vue 2) figures out *which* DOM nodes need to change and does it for you.
- **Can everything in this app be done in plain JS?** **Yes, fundamentally — Vue itself is just JavaScript, compiled down to `document.createElement`/`appendChild`/event-listener calls under the hood.** Nothing Vue does is impossible in vanilla JS; it's a productivity/maintainability layer, not a capability Vue uniquely grants. The honest cost of doing this project in plain JS: you'd hand-write the "diffing" (figuring out what changed and touching only that DOM), hand-manage every event listener's lifecycle (attach/detach to avoid leaks on re-render), and hand-build your own tiny router (listening to `popstate`, matching `window.location.pathname` against routes, swapping which markup is in the DOM) — all of which Vue + Vue Router give you out of the box.
- **Directive substitutes in plain JS** (know these cold — this is a very literal, answerable question):
  - `v-if="cond"` → conditionally `element.remove()` / re-`appendChild` it, or toggle it via building the DOM node only when `cond` is true.
  - `v-show="cond"` → `element.style.display = cond ? '' : 'none'`.
  - `v-for="x in list"` → a manual loop building/appending one element per item, and re-running that loop (after clearing the container) whenever `list` changes.
  - `v-model="x"` → manually: `input.addEventListener('input', e => { x = e.target.value; render(); })` **plus** setting `input.value = x` on every render — i.e., you have to hand-wire *both directions* of the binding yourself, which is exactly what `v-model` automates.
  - `@click`/`v-on:click` → `element.addEventListener('click', handler)`.
  - `:class`/`v-bind:class` → `element.className = cond ? 'a' : 'b'`, recomputed on every render.
  - `@mouseover`/hover → `element.addEventListener('mouseenter', handler)` / `mouseleave`.

### The DOM
- **What is the DOM?** The Document Object Model — the browser's in-memory, tree-structured **object representation** of the HTML page, where every tag becomes a node object with properties/methods. It's what JavaScript actually manipulates — JS never edits the raw HTML text; it edits DOM node objects, and the browser re-paints the screen to match.
- **What does it give you beyond just rendering HTML?** A **live, queryable, mutable object tree**: you can traverse it (`parentNode`, `children`, `querySelector`), attach behavior to it (`addEventListener`), read/write its state (`.value`, `.textContent`, `.style`, `.classList`), and it fires **events** (clicks, input changes, form submits) that JS can react to — none of which exists in the static HTML text itself; the DOM is the *live, interactive* version of the page.

### HTTP / REST
- **What is HTTP?** HyperText Transfer Protocol — the request/response protocol the entire web (and this app's frontend↔backend communication) runs over: client sends a request (method + URL + headers + optional body) to a server, server sends back a response (status code + headers + optional body).
- **Communication protocol between Flask and Vue in this project?** They talk over **HTTP, carrying JSON payloads** (Axios makes the HTTP calls; Flask's `jsonify()` produces the JSON responses). Since this app serves both the API and the Vue shell from the **same Flask process/port**, in production there's really only one server involved, not two separate ones talking cross-network — the "communication" is same-origin `fetch`/XHR calls from the loaded page back to the same host. (If run in the alternate dev setup — Vue files off a separate dev server pointed at Flask — then yes, it'd be two literal server processes, still communicating over plain HTTP/JSON, which is exactly why `flask-cors` exists in this project at all — see v1/v2's CORS section.)
- **HTTP methods and their use**: `GET` — retrieve, no body semantics, idempotent, safe/no side effects (e.g. `GET /student/drives`). `POST` — create/submit, has a body, not idempotent (calling twice can create two things) (e.g. `POST /student/applications`). `PUT` — replace/update a resource, idempotent (calling it twice with the same body leaves the same end state) (e.g. `PUT /student/profile`). `DELETE` — remove a resource, idempotent (e.g. `DELETE /admin/companies/<id>`). `PATCH` — partial update (this project mostly uses `PUT` even for partial updates, e.g. `update_interview()` only touches fields present in the payload — a defensible but slightly loose use of `PUT` where `PATCH` would be the textbook-correct verb).
- **Can you send a body on all methods? Should you?** Technically, HTTP doesn't forbid a body on any method — but by convention/spec-intent: `GET`, `DELETE`, `HEAD` are conventionally treated as **not carrying a semantically meaningful body** (many servers/proxies/caches will ignore or strip a `GET` body), while `POST`/`PUT`/`PATCH` are exactly the methods meant to carry one. **In this project**: every list/search endpoint (`GET /admin/companies?q=...`) deliberately puts its parameters in the **query string**, not a body, precisely because `GET` requests shouldn't carry bodies — `PUT`/`POST` routes (`apply()`, `update_profile()`, `create_drive()`, etc.) are exactly where `request.get_json()` is used.
- **What is a REST API — what must it follow to be "RESTful"?** The defining constraints (Roy Fielding's dissertation): **client-server** separation, **statelessness** (no server-side session state between requests — each request carries everything needed to understand it), **cacheability** (responses declare whether they're cacheable), **uniform interface** (resources identified by URLs, manipulated via standard HTTP methods, self-descriptive messages), **layered system** (client can't tell if it's talking directly to the server or through intermediaries), and optionally **code-on-demand**. **Is this project truly stateless?** Yes — JWT auth means the server stores **no session state** for any client; every request carries its own auth (the token) and is fully self-contained. *"How is statelessness actually helpful?"* — no server-side session store needed (simpler infra, nothing to synchronize if you horizontally scale to multiple Flask instances — any instance can handle any request since none of them are holding per-user session state), and it removes a whole class of "sticky session" load-balancing complexity.
- **Other API architectural styles, and why REST over them?** **SOAP** (older, XML-based, strict contracts via WSDL, heavier). **GraphQL** (client specifies exactly which fields it wants in a single query, avoids over/under-fetching, but adds query-complexity/caching challenges). **gRPC** (binary protocol over HTTP/2, very fast, great for service-to-service, less natural for a browser client). **Benefit of REST here**: simplicity and ubiquity — every HTTP client (Axios, curl, Postman) speaks it natively with zero extra tooling, URL-based resources map naturally onto this app's entities (`/students`, `/drives`, `/applications`), and its statelessness (above) is a good fit for a JWT-secured SPA.

### `jsonify`
- **What does `jsonify()` do?** Converts a Python `dict`/`list` into a proper Flask `Response` object: serializes it to a JSON string **and** sets `Content-Type: application/json` on the response headers automatically (returning a raw `dict` from newer Flask versions also auto-jsonifies, but this project calls `jsonify()` explicitly everywhere for clarity and because it also lets you chain `, 201`/`, 404` status-code tuples cleanly).

### Sessions vs Tokens (JWT)
- **What auth does this project actually use?** **Token-based (JWT)**, not session-based — verified: no `session[...]` usage anywhere in the codebase; `flask_jwt_extended`'s `create_access_token()`/`verify_jwt_in_request()` handle everything (see v1 §6, v3 Part F).
- **If asked "how does session-based auth work" anyway (generic, be ready even though it's not what you built)**: on login, the server creates a session record **server-side** (in memory, a DB, or Redis) keyed by a random session ID, and sends that ID to the browser as a **cookie**. On every subsequent request, the browser automatically re-sends that cookie; the server looks up the session ID against its store to know who's logged in. This is **stateful** — the server must retain session data for every logged-in user, and if you scale to multiple server instances, they all need access to a **shared** session store (or you need sticky sessions), which is exactly the operational complexity token-based auth avoids.
- **Why token-based over session-based here?** Fits a decoupled SPA + REST API cleanly: no server-side session store to maintain/scale, works naturally with Axios's `Authorization` header pattern, and matches the REST statelessness constraint above. Trade-off (be ready to state honestly): a session can be instantly revoked server-side (just delete the session record); **this project's JWT has no expiry and no revocation mechanism** (`JWT_ACCESS_TOKEN_EXPIRES = False`) — a logged-out or blacklisted user's *old* token stays cryptographically valid forever, only the live re-check in `company_required`/`student_required` (querying current blacklist/approval status on every request) closes that gap for role-account-level blocks; a stolen-but-not-blacklisted token has no server-side kill switch in this dev build.

### "In-memory" — what does it mean, physically?
- **What is "in-memory"?** Data held in **RAM**, not on disk. RAM is volatile (cleared on process restart/power loss) but orders of magnitude faster to read/write than disk I/O — which is exactly why Redis (an in-memory data store) is used here for caching and as the Celery broker: both need very fast read/write of small pieces of data, and don't need the durability guarantees of a real disk-backed database. **Physically**: it lives in the RAM of whatever machine `redis-server` is running on (your laptop, in dev) — Redis *can* optionally persist snapshots to disk (RDB/AOF) for durability across restarts, but the live working data set it serves reads/writes from is RAM.
- **Do you always need to store cached results in Redis DB index 1?** **No — that's purely this project's own config choice, not a Redis requirement.** Redis ships with **16 logical databases by default (index 0–15)**, all in the same physical Redis instance/process, just logically namespaced. This project's `config.py` puts the Celery broker/result-backend on `/0` and the Flask-Caching store on `/1` **specifically so a `FLUSHDB` or key collision in one doesn't affect the other** — but you could use index 3 and 7, or even the same index with different key *prefixes*, and it would work identically. Nothing about Redis or Celery mandates index 1 specifically.
- **Three servers (Celery, Flask, Vite) interacting — how, in your project?** Slight correction to make if asked this exact way: **there's no Vite here** (no build tool, see the Node/npm section above) — so it's really: **Flask** (the WSGI app serving both the JSON API and the Vue shell), the **Celery worker** (a separate OS process consuming queued jobs), **Celery beat** (a separate OS process that just enqueues scheduled jobs on a timer), and **Redis** (a separate process both Flask and Celery talk to — Flask writes cache entries and enqueues jobs into it, Celery workers pull jobs off it and write results back to it). Flask and Celery **never call each other directly** — they only ever communicate *through* Redis (Flask calls `.delay()` which serializes the task call into a Redis queue; the worker, running as an entirely separate process, polls that queue independently). This decoupling is exactly why Flask's HTTP response for `POST /export` can return in milliseconds regardless of how long the actual CSV export takes.

### `__init__.py`
- **What is `routes/__init__.py` for?** It marks the `routes/` directory as a Python **package**, so `from routes.admin import admin_bp` (or the equivalent import style used in `app.py`) works. **Verified: this project's `routes/__init__.py` is a completely empty file (0 bytes)** — it exists purely as the "this is a package" marker, with no re-exports or package-level logic inside it.
- **Is there a way to make it a package without `__init__.py`?** **Yes** — since Python 3.3, **implicit namespace packages (PEP 420)** let any directory be imported as a package with **no `__init__.py` at all**, as long as it's on the import path. The practical difference: a directory *with* `__init__.py` is a "regular package" (can hold package-level init code, `__all__`, explicit re-exports); a directory *without* one is a "namespace package" (more flexible for splitting one logical package across multiple directories/distributions, but you lose the ability to run code at import time or centrally control what's exported). This project uses the traditional, explicit `__init__.py` style — the more common/conventional choice for a self-contained app like this rather than a distributed/pluggable package.

### `__tablename__`
- **Is `__tablename__` needed on each model?** **Not strictly** — if omitted, Flask-SQLAlchemy auto-generates one from the class name (converting `CamelCase` → `snake_case`, e.g. `PlacementDrive` → `placement_drive`). **Verified: every single model in `models.py` explicitly sets `__tablename__`** (`'admin'`, `'company'`, `'student'`, `'notification'`, `'placement_drive'`, `'application'`, `'application_status_log'`, `'interview'`, `'placement'`) — and notably, **every one of these explicit names is exactly what auto-generation would have produced anyway.** So: *"If I commented out every `__tablename__` line, the schema would very likely still work identically, since Flask-SQLAlchemy's auto-naming convention happens to match what I wrote by hand."* Good, honest, verifiable answer if asked to prove it live — comment one out, rerun `init_db.py`, show it still works.

### Enums
- **What are ENUMs, what's their use?** A type that restricts a value to one of a fixed, named set of options (e.g. `Applied | Shortlisted | Selected | Rejected`) — enforced either at the **language level** (Python's `enum.Enum`) or the **database level** (a SQL `ENUM` column type / `CHECK` constraint), preventing invalid/typo'd values from ever being stored.
- **⚠️ Does this project actually use true Enums? Check before claiming it does.** Verified: `constants.py` defines `ApplicationStatus`, `DriveStatus`, `ApprovalStatus`, `InterviewStatus`, `OfferStatus` as **plain Python classes with string class-attributes** (e.g. `class ApplicationStatus: APPLIED = 'Applied'`), **not** Python's `enum.Enum` and **not** SQLAlchemy's `db.Enum` column type. The corresponding `models.py` columns (e.g. `Application.status`) are plain `db.String`/`db.Text` columns with **no DB-level constraint** enforcing the value is actually one of the five allowed strings. **Honest answer if asked "what enums did you use" — say exactly this**: *"I used plain string-constant classes for readability and IDE autocomplete (`ApplicationStatus.SELECTED` instead of the magic string `'Selected'`), but I did not use a true `enum.Enum` or a DB-level `Enum` type — so nothing stops a bad actor with raw DB access from writing an arbitrary string into `Application.status`. A stronger version would use SQLAlchemy's `db.Enum(ApplicationStatus)` (or Python's `enum.Enum` classes wrapped that way) to get a real DB-level `CHECK` constraint enforcing valid values."* This is a genuinely fair, specific self-critique to have ready — much stronger than pretending you have real enums when you don't.

### Limiting password length **at the database level** (not frontend/backend validation)
This is a subtly tricky question — think it through carefully, because passwords aren't stored raw here.
- **The trap**: `Student.password_hash`/`Company.password_hash`/`Admin.password_hash` store a **Werkzeug hash** (e.g. a scrypt/pbkdf2 digest string), not the plaintext password — so a DB-level length constraint on the `password_hash` column constrains the **hash's** length (which is roughly fixed regardless of input password length), **not** the original password's length. You genuinely cannot enforce "original password ≤ 13 chars" purely from a constraint on the hash column, because the hash doesn't preserve input length information in a checkable way.
- **A real DB-level answer, if truly required to check the raw password length before it gets hashed**: you'd need a `CheckConstraint` on a column that actually holds the raw (or length-preserving) value — architecturally unusual for a password, but demonstrable: e.g. a `db.CheckConstraint('length(raw_password_staging) <= 13')` on a **transient staging column** you populate right before hashing and never persist afterward — genuinely awkward, and a good thing to point out as awkward rather than pretend it's clean.
- **The honest, better answer**: *"Enforcing a password's raw length is fundamentally an application-layer concern, not a database-layer one, precisely because the DB never sees the raw password in a well-designed system (only its hash) — so the correct place for this check is exactly where I currently do CGPA-range validation: in the Flask route, before calling `generate_password_hash()`."* If the proctor insists on "DB level, not app level" as a hard constraint, the honest answer is: *"With hashed storage, that's not really achievable cleanly at the DB layer — the closest DB-level approximation is a `CHECK` constraint on the hash column's length, but that doesn't actually constrain the input password's length, it constrains the hash algorithm's fixed output length, which isn't the same thing."*

### Hash-based routing (`#` in the URL) — **this project deliberately doesn't use it**
- **What's the `#` in `http://localhost:8080/#/login`?** That's Vue Router's **hash mode** — the default mode if you don't explicitly configure otherwise. Everything after the `#` is **not sent to the server at all** (it's a pure browser/client-side fragment); Vue Router listens to the `hashchange` event and swaps components based on what's after the `#`, meaning the server never needs to know how to respond to `/login`, `/admin/dashboard`, etc. — it only ever needs to serve one static file at `/`.
- **Does this project use hash mode?** **No — verified: `router.js` explicitly sets `mode: 'history'`.** URLs here look like `http://localhost:5000/admin/dashboard`, with **no `#`.** History mode uses the browser's native History API (`pushState`/`popstate`) to change the URL bar **without a page reload**, but the URL now genuinely *looks* like a real server path — which is exactly why Flask needs that catch-all route (`@app.route('/<path:path>')` → always serves `index.html`) discussed in v1 §14/v2 B.6: without it, a hard refresh on `/admin/dashboard` would hit Flask directly asking for a real `/admin/dashboard` resource and 404, since history mode's URLs *are* real-looking server paths that the server must be taught to redirect back to the SPA shell.
- **"Where would you change it?"** → `static/js/router.js`'s `mode: 'history'` line — flipping it to `mode: 'hash'` (or omitting `mode` entirely, since hash is the default) would immediately reintroduce the `#` and simultaneously make the Flask catch-all route unnecessary (since hash-mode URLs never leave the initial `/` as far as the server is concerned).

---

## PART K — Live Coding Tasks From This Report (solved for the placement portal)

### K.1 — Dummy frontend-only feature: search "IITM" → show a welcome message via `v-if`

Applied to your actual admin search context (`AdminCompanies.js`/`AdminStudents.js`, or a standalone demo):
```js
data: function () {
  return { searchQuery: '', /* ...existing fields */ };
},
computed: {
  showIitmWelcome: function () {
    return this.searchQuery.trim().toUpperCase() === 'IITM';
  }
}
```
```html
<input v-model="searchQuery" placeholder="Search..." class="form-control">
<div v-if="showIitmWelcome" class="alert alert-success mt-2">
  Welcome, IITM! 🎉
</div>
```
(Using a `computed` here rather than a `watch`+manual flag is the cleaner Vue idiom — and ties directly back to the "computed vs watch" theory question from prep v2/v3: this is a pure derived boolean from `searchQuery`, so `computed` is the textbook-correct choice.)

### K.2 — Backend-only: block a specific company name from being the *first* registrant

The exact task, translated: *"If no companies exist yet AND the incoming registration's `company_name` is `'AppDevTeam'`, reject it and log `'Cannot register'` to the server terminal."*

```python
# routes/auth.py :: register_company()  — add this check before creating the Company row
@auth_bp.route('/register/company', methods=['POST'])
def register_company():
    data = request.get_json(silent=True) or {}
    company_name = (data.get('company_name') or '').strip()
    # ...existing extraction of email/password/etc.

    # ── NEW CHECK ─────────────────────────────────────────────────────
    if Company.query.count() == 0 and company_name == 'AppDevTeam':
        print('Cannot register')
        return jsonify({'msg': 'This company name cannot be the first registrant.'}), 400
    # ──────────────────────────────────────────────────────────────────

    if Company.query.filter_by(email=email).first():
        return jsonify({'msg': 'Email already registered.'}), 409
    # ...rest unchanged
```
**Better status code than 404** (the reported student used `404`, which is semantically wrong here — 404 means "resource not found," not "request rejected by a business rule"): **`400 Bad Request`** (malformed/disallowed input) or **`403 Forbidden`** (understood but refused) are both more correct; be ready to explain this distinction if a proctor pushes on it, even if you initially reach for 404 under pressure like the reporting student did.

**Show the error in the browser dev console** (what "show it in the developer console" actually means — surface the failed request's response, not just swallow it silently):
```js
// Register.js — company registration handler
submitCompany: function () {
  var self = this;
  window.api.post('/auth/register/company', { company_name: self.companyName, /* ... */ })
    .then(function (res) { /* success path */ })
    .catch(function (err) {
      console.error('Registration failed:', err.response && err.response.data);
      self.error = (err.response && err.response.data && err.response.data.msg) || 'Registration failed.';
    });
}
```
Opening DevTools → Console (or Network tab → the failed request's Response) shows exactly this. **Explicitly state "what logical change did you add"** if asked: *"A guard clause checking `Company.query.count() == 0` combined with a name match, placed before any row is created — a pure additive check, no existing logic touched."*

### K.3 — Full Vue Router task (this exact task shape has now appeared **twice** across different reports — memorize this cold)

```
users = [{id,name,importance_score}, ...]
- list view with v-for, click a user → navigate to /users/:id
- detail component reads id from the URL, shows name + score
- score < 50 → red, else green
- invalid id → "User not found"
```

Solved in this project's exact conventions (Options API, Vue 2, `var self = this`, template-as-string):

```js
// static/js/components/UserList.js
const UserList = {
  data: function () {
    return {
      users: [
        { id: 1, name: 'proctor1', importance_score: 10 },
        { id: 2, name: 'proctor2', importance_score: 20 },
        { id: 3, name: 'proctor3', importance_score: 30 }
      ]
    };
  },
  methods: {
    goToUser: function (id) {
      this.$router.push('/users/' + id);
    }
  },
  template:
    '<div class="container mt-4">' +
    '  <h3>Users</h3>' +
    '  <ul class="list-group">' +
    '    <li class="list-group-item list-group-item-action" ' +
    '        style="cursor:pointer" ' +
    '        v-for="u in users" :key="u.id" ' +
    '        @click="goToUser(u.id)">' +
    '      {{ u.name }}' +
    '    </li>' +
    '  </ul>' +
    '</div>'
};

// static/js/components/UserDetail.js
const UserDetail = {
  data: function () {
    return {
      users: [
        { id: 1, name: 'proctor1', importance_score: 10 },
        { id: 2, name: 'proctor2', importance_score: 20 },
        { id: 3, name: 'proctor3', importance_score: 30 }
      ]
    };
  },
  computed: {
    user: function () {
      var id = Number(this.$route.params.id);
      return this.users.find(function (u) { return u.id === id; }) || null;
    }
  },
  template:
    '<div class="container mt-4">' +
    '  <div v-if="user">' +
    '    <h3>{{ user.name }}</h3>' +
    '    <p :style="{ color: user.importance_score < 50 ? \'red\' : \'green\' }">' +
    '      Score: {{ user.importance_score }}' +
    '    </p>' +
    '  </div>' +
    '  <div v-else class="alert alert-warning">User not found</div>' +
    '</div>'
};
```
```js
// router.js — add to the routes array
{ path: '/users', component: UserList },
{ path: '/users/:id', component: UserDetail },
```
```html
<!-- index.html — load both before router.js -->
<script src="{{ url_for('static', filename='js/components/UserList.js') }}"></script>
<script src="{{ url_for('static', filename='js/components/UserDetail.js') }}"></script>
```
**Key design choices to narrate out loud while writing this** (proctors reward narration):
- `computed` for `user`, not a `data()` field set in `mounted()` — because it's a pure derivation of `$route.params.id` against a static list; if you navigate directly from `/users/1` to `/users/2` (same component instance reused by Vue Router, not destroyed/recreated), a `computed` automatically re-derives, while a `mounted()`-only assignment would go stale — this is a classic Vue Router gotcha, and pointing it out proactively is a strong signal.
- `v-if="user"` / `v-else` cleanly handles the not-found case — no separate loading/error flags needed since the data is synchronous/local here (this task uses a static array, not an API call — if it were an API call, you'd want the loading/error pattern from every other component in your real app, e.g. `DriveDetail.js`).
- `:style` binding for the conditional color rather than `:class` — either works; `:class` with two Bootstrap-style utility classes (`text-danger`/`text-success`) is arguably cleaner and more consistent with the rest of this project's styling approach (which leans on Bootstrap utility classes rather than inline styles) — mention you'd normally do it that way in your real app, but inline `:style` is fine for a quick demo task.

---

## PART L — "Give me a quick overview of all files and folders" — have a 60-second script ready

Say this fluently, don't read it — but have the shape memorized:

> "At the root: `app.py` builds the Flask app via an application-factory pattern, `config.py` holds all configuration, `extensions.py` holds the shared extension instances plus the Celery-Flask bridge, `constants.py` holds every status value used across the app, `models.py` has all 9 database tables, `cache_keys.py` handles Redis cache key naming and invalidation, `tasks.py` has the four Celery background jobs, `celery_worker.py` is the CLI entry point for running those, `reports.py` renders the HTML/PDF report content, and `init_db.py` builds and seeds the database. Inside `routes/`, I've got one blueprint file per role — `auth.py`, `admin.py`, `company.py`, `student.py` — plus a small separate `api.py` that's an unauthenticated Flask-RESTful demo layer, and `decorators.py` with the three role-guard decorators. On the frontend, `static/js/` has one plain `.js` file per Vue component, organized into `admin/`, `company/`, `student/`, and `common/` subfolders, plus `router.js` for routing and `config.js` for the shared Axios instance and auth-token handling — loaded via plain script tags off `templates/index.html`, with no build step at all."

That's your file-tour answer, ready to go regardless of which proctor or phrasing asks for it.
