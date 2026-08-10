# Placement Portal — Demo Video Script

Total suggested length: ~8–10 minutes. Have these running *before* you hit record:

**One-time setup (skip if already done):**
```bash
cd placement-portal-mad2-main

# create + activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# install dependencies
pip install -r requirements.txt

# seed the database with demo admin/company/student accounts
python init_db.py
```

**Every time, right before recording (each in its own terminal tab):**
```bash
# 1. Redis — Celery's broker/result-backend + the cache store
redis-server

# 2. Mailhog — fake SMTP server + web inbox at localhost:8025
docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog

# 3. Celery worker — executes queued tasks
source venv/bin/activate
celery -A celery_worker.celery worker --loglevel=info

# 4. Celery beat — schedules the cron-style tasks (interview reminders, monthly report)
source venv/bin/activate
celery -A celery_worker.celery beat --loglevel=info

# 5. Flask app
source venv/bin/activate
python app.py
```
Then open `http://localhost:5000` (or whatever port `app.py` prints) in the browser.

Arrange windows beforehand: browser (main), a second browser/incognito window (for a second role), and a terminal panel showing the Celery worker log — you'll cut to it twice.

---

## 1. Intro (30s)
**Say:** One line on what the project is — a placement portal with three roles (admin/company/student), Flask API backend, Vue SPA frontend, Redis + Celery for background jobs, Flask-Caching for performance.

**Show:** Nothing yet — just talk over the login page loaded in the browser, or a quick flash of the file tree (`app.py`, `routes/`, `static/js/`, `tasks.py`).

---

## 2. Architecture in 60 seconds
**Say:** Flask serves the SPA shell once, then it's a pure JSON API. Vue Router handles all navigation client-side. Auth is JWT in `localStorage`, not server sessions. Redis backs two independent things: Celery's job queue, and API response caching.

**Show (optional):** the repo structure diagram or just narrate over the code tree — don't linger, this is context-setting, not the demo itself.

---

## 3. Login flow — the fetch-based auth loop (60s)
**Do:**
1. Open the app fresh (no token) → show it auto-redirect to `/login`.
2. Open DevTools → Network tab, filtered to Fetch/XHR.
3. Log in as a student.
4. Point out the `POST /api/auth/login` request — no `Authorization` header (no token yet).
5. Point out the *next* request, `GET /student/dashboard` — now it **does** have `Authorization: Bearer …`.

**Say:** This is the whole session model — login returns a JWT, we stash it in `localStorage`, and every request after that attaches it via a `fetch()` wrapper that mimics axios's `{data}` shape.

---

## 4. Caching demo (60–75s)

**Step 1 — Clear the cache (guarantee a cold start)**
Navigate to `http://localhost:5000/cacheremove`. You should see:
```json
{ "msg": "Cache cleared successfully." }
```
This flushes Redis and guarantees the next request is a genuine cache miss.

> 🎙️ **Say:** "Before we start, I'm hitting a debug route that flushes Redis — this guarantees what you're about to see is a real cache miss, not a leftover cached result from earlier."

**Step 2 — First load: cache miss**
Log in as a student (`student1@test.com` / `password123`) and click **Browse Drives**. Watch the loading spinner run for a couple of seconds.

*(Optional, stronger on camera)* Open DevTools → Network tab → click the `drives` request → point out the response time (a couple thousand ms) — proof this hit the database.

> 🎙️ **Say:** "This first load is a cache miss. The request goes all the way to the database, and while it's there, Flask-Caching writes the result into Redis before sending it back — that's why it takes a moment."

**Step 3 — Navigate away and back: cache hit**
Click **Dashboard** in the nav, then click **Browse Drives** again (rather than just hitting refresh — this proves it's the *route* that's cached, not just a browser-level reload).

*(Optional)* Check the Network tab again — response time should now be single-digit milliseconds.

> 🎙️ **Say:** "Now watch what happens when I navigate away to the dashboard and come back to the same page. No spinner, no delay — this time the response is served straight out of Redis in a couple of milliseconds, with zero database queries. Same route, same data, completely different cost, because the second request never touches the database at all."

---

## 5. Core role walkthrough (2–3 min)
Keep this tight — one meaningful action per role, not a full feature tour.

- **Student:** browse drives → open one → apply.
- **Company:** log in (or switch tab) → view applicants for a drive → shortlist one.
- **Admin:** log in → approve a pending company, or view the applications table.

**Say (once, generally):** every one of these clicks follows the same pattern — Vue method → `fetch()` call → Flask route behind a role-checking decorator → DB or cache → JSON back → Vue re-renders reactively. You don't need to repeat this per click, just demonstrate it's consistent.

---

## 6. Redis + Celery — the async pipeline (2 min)
This is the most "impressive" section — make sure it's clearly staged.

**Do:**
1. Switch to the Celery worker terminal — show it idle, connected to Redis.
2. Go to **Admin → Broadcast** (your new page).
3. Type a message, pick "Student" as audience, hit Send.
4. **Immediately** point out the UI response: `202 Accepted` / "Broadcast queued" banner appears instantly — the task is *not* done yet.
5. Cut to the Celery worker terminal — show the task being received and picked up.
6. Wait ~5 seconds on camera (your task's deliberate `time.sleep(5)`).
7. Switch to the student browser tab, refresh notifications → the message appears.

**Say:** The admin's request returned immediately because it only pushed a job onto the Redis queue — it didn't wait for the work to finish. The actual work (writing notifications for every student, sending emails) happened separately in the worker process. This is the same mechanism used for the scheduled jobs — Celery Beat pushes `send_interview_reminders` and `send_monthly_report` onto this same queue on a cron schedule; I'm just triggering one manually here so we don't have to wait for 8 AM.

---

## 7. Mailhog — proving the email pipeline (60s)
**Do:**
1. Switch to `localhost:8025` (Mailhog inbox) — the email from the broadcast you just sent should already be sitting there.
2. Open it — show subject + body rendered.
3. *(Optional, stronger)* Trigger `send_monthly_report` as well, to show the PDF attachment landing in Mailhog. Two ways to do this:

**Option A — Via a debug admin route (if you built one):**
Call it the same way you trigger the broadcast — through the UI or a quick `curl`/Postman request to whatever route wires up `send_monthly_report.delay()`.

**Option B — Via Browser Console (when logged in as Admin):**
1. Log into the portal as Admin (`admin@placementportal.com` / `admin123`).
2. Open F12 Developer Tools → Console tab.
3. Paste and run:
   ```javascript
   window.api.post('/admin/trigger-monthly-report').then(res => console.log(res.data));
   ```
4. Check your Admin notifications, or inspect the generated PDF files under `static/reports/`.

> 🎙️ **Say:** "Instead of waiting for the actual monthly cron, I'm triggering the report task directly through the browser console — same underlying Celery task, same queue, just fired manually so we don't have to wait for the 1st of the month."

**Say:** In production this would point at a real SMTP provider — for local dev and this demo, Mailhog catches everything so we can verify the email pipeline works end-to-end without sending real mail or needing real credentials.

---

## 8. Wrap-up (20s)
**Say:** One sentence tying it together — three roles, JWT auth over a JSON API, Redis-backed caching for read performance, Celery for anything that shouldn't block a request (notifications, scheduled reports, emails).

**Show:** Back to the dashboard or file tree, end recording.

---

## Quick checklist before you hit record
- [ ] Mailhog container running, inbox empty (restart container if you want a clean start)
- [ ] Celery worker + beat both running, worker terminal visible/ready to cut to
- [ ] `MAIL_SERVER=localhost` / `MAIL_PORT=1025` set in the environment Flask/Celery are running in
- [ ] `tasks.py` patched (STARTTLS/login skip for localhost) — test the broadcast once *before* recording so you're not debugging live
- [ ] DB seeded (`init_db.py`) with known credentials for admin/company/student
- [ ] Second browser/incognito window logged in as student or company, ready to switch to
- [ ] Cache cleared right before section 4 so the miss-then-hit timing is real
