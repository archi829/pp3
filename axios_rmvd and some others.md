Based on the changes documented in the uploaded file, these are the **important things you should document for the project**—especially for your report, viva, and video. 

### 1. Eligibility & application validation

* Added structured **`min_cgpa`** field to `PlacementDrive`.
* CGPA is now stored as an actual numeric value rather than free-text eligibility criteria.
* Company can specify/update minimum CGPA when creating/editing a drive.
* `min_cgpa` is included in API responses.
* Student application now checks:

  * **Minimum CGPA eligibility**
  * **Application deadline**
* Applications are rejected with `400` when either condition fails.
* Seed data updated with `min_cgpa` values for all 8 drives.
* This was **tested live**, not just syntax-checked. 

### 2. API security / RBAC

* Secured the previously unauthenticated `/api/*` Flask-RESTful endpoints.
* Added `admin_required` protection to all 5 admin CRUD resources.
* Prevents unauthenticated users from creating/editing/deleting students and drives.
* Reuses the existing authentication/authorization mechanism rather than introducing another security library. 

### 3. Resume file management

* When a student uploads a new resume:

  * Old resume is deleted first.
  * New resume is saved.
* Prevents orphaned/unused resume files from accumulating on disk. 

### 4. Background-job email reliability

This is a **good section to document prominently**.

* Email helper functions now return explicit **success/failure status** instead of only printing errors.
* Interview reminder task tracks:

  * Emails attempted
  * Emails successfully delivered
  * Emails skipped/failed
* Monthly report task similarly tracks email delivery.
* Admin receives an **in-app summary notification** rather than relying on console logs.
* Notifications are aggregated into a summary instead of generating one notification per student. 

### 5. Admin notification system

You should document this as a separate feature because it required frontend + backend changes.

* Added admin notification API:

  * `GET /api/admin/notifications`
* Added `AdminNotifications.js`.
* Added router entry.
* Added notifications navigation item to `AdminLayout`.
* Admin can therefore see background-job outcomes inside the application.
* Notifications correctly work with JWT authentication and can be marked/read. 

### 6. Success + failure reporting

The notification system was improved further so it doesn't only report failures.

**Successful job:**

* Example: `Interview reminders: ran successfully — all 3 email(s) delivered.`

**Partial/failure:**

* Example: `Interview reminders: 0/1 emails delivered. 1 skipped or failed...`

**No-op:**

* If there are genuinely no interviews/reports to process, no unnecessary notification is generated.

This distinction is worth documenting because it demonstrates **meaningful background-job observability**, not just error handling. 

### 7. Testing / verification

Document that you didn't just make the changes—you verified them.

Mention:

* Python syntax/compilation checks.
* Database seeding successfully completed after adding `min_cgpa`.
* Eligibility rejection tested.
* Deadline rejection tested.
* Admin API authentication tested.
* Email failure path tested.
* Email success path tested using a mock.
* Admin notifications verified end-to-end.
* Database reset afterward to a clean seed state.  

### 8. Files/modules changed

Keep a small change log:

| File                    | Important change                           |
| ----------------------- | ------------------------------------------ |
| `models.py`             | Added `PlacementDrive.min_cgpa`            |
| `init_db.py`            | Seeded CGPA eligibility values             |
| `routes/student.py`     | Deadline + CGPA validation; resume cleanup |
| `routes/company.py`     | Create/edit drive with `min_cgpa`          |
| `routes/api.py`         | Admin authentication on CRUD APIs          |
| `tasks.py`              | Email status tracking + admin summaries    |
| `routes/admin.py`       | Admin notifications endpoint               |
| `AdminNotifications.js` | Admin notification UI                      |
| `router.js`             | Notification route                         |
| `AdminLayout.js`        | Notification navigation                    |

### 9. What **not** to claim as implemented

Important for your documentation/viva: don't accidentally say these were implemented.

These were **left as future improvements**:

* JWT expiry
* JWT cookie storage
* Rate limiting
* Pagination
* Soft deletion
* Flask-Limiter

The source explicitly says these were not implemented because they would add complexity/dependencies. 

### If you're making a project report, I'd structure this as:

**Enhancements / Improvements**

1. Structured placement eligibility
2. Deadline enforcement
3. API authentication and RBAC
4. Resume lifecycle management
5. Background-job email monitoring
6. Admin notification system
7. Success/failure observability
8. Testing and validation

**This is the core story:**

> The changes moved several features from being **display-only or silently failing** to being **actually enforced, authenticated, observable, and test-verified**.
===
Yes — **add this Axios → Fetch migration to the documentation/change list**. It is relevant because it changes the frontend dependency stack and improves compliance with the “no extra libraries” constraint.

### 10. Axios → Browser Fetch API migration

Document these points:

* **Removed Axios** from the frontend.
* Replaced Axios HTTP requests with the **native browser `fetch()` API**.
* Converted all existing:

  * `axios.get()` → `fetch(..., { method: 'GET' })` / simple `fetch()`
  * `axios.post()` → `fetch(..., { method: 'POST', ... })`
  * `axios.put()` → `fetch(..., { method: 'PUT', ... })`
  * `axios.delete()` → `fetch(..., { method: 'DELETE', ... })`
* Added appropriate `Content-Type: application/json` headers for JSON requests.
* Used `JSON.stringify()` for JSON request bodies.
* Updated response handling from Axios's `response.data` style to Fetch's `response.json()`.
* Preserved existing:

  * API endpoints
  * request payloads
  * authentication/JWT handling
  * error handling
  * UI behavior
* Removed Axios from frontend dependencies/imports.
* Verified there are **no remaining Axios imports or calls** anywhere in the frontend.
* This reduces unnecessary dependencies and keeps the stack aligned with the assignment requirements.

### Your final technology stack should now be documented as

**Frontend**

* Vue.js
* Vue Router
* Bootstrap
* **Browser Fetch API**

**Backend**

* Flask
* Flask-RESTful
* SQLite
* Redis
* Celery

### Important viva point

If asked **“Why did you use Fetch instead of Axios?”**, your answer should be:

> “The assignment restricts the use of additional libraries, so I removed Axios and used the browser's native Fetch API for HTTP communication. This keeps the frontend dependency footprint minimal while still supporting GET, POST, PUT and DELETE requests.”

And if they ask **“Why is Vue Router allowed but Axios wasn't?”**:

> “Vue Router is required for SPA routing and is part of the official Vue ecosystem, whereas Axios is an independent HTTP client library. Since the browser already provides Fetch, Axios wasn't necessary.”

### So your complete documentation checklist now becomes

1. **CGPA eligibility enforcement**
2. **Application deadline enforcement**
3. **Structured `min_cgpa` database field**
4. **Company drive create/edit changes**
5. **API authentication / admin RBAC**
6. **Resume replacement + old-file cleanup**
7. **Background email success/failure tracking**
8. **Admin notification backend**
9. **Admin notification frontend**
10. **Successful job summaries**
11. **Failed/partial job summaries**
12. **No-op job behavior**
13. **Axios → Fetch migration**
14. **Removal of Axios dependency/imports**
15. **Testing of all modified functionality**
16. **Future improvements explicitly not implemented** — JWT expiry, rate limiting, pagination, soft delete, etc.

The **Axios → Fetch change is worth mentioning in the “Technology/Compliance Improvements” section**, but it shouldn't be presented as a major functional feature like CGPA validation or RBAC.
