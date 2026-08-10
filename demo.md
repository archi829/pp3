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

# point the app at a local dev SMTP server (Mailhog)
export MAIL_SERVER=localhost    # Windows: set MAIL_SERVER=localhost
export MAIL_PORT=1025           # Windows: set MAIL_PORT=1025
export MAIL_USERNAME=demo       # Windows: set MAIL_USERNAME=demo
export MAIL_PASSWORD=demo       # Windows: set MAIL_PASSWORD=demo

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

## 4. Caching demo (45s) — matches your original plan
**Do:**
1. Hit the `/cacheremove` debug route (or whatever cache-clearing route you wired up) to guarantee a cold cache.
2. Navigate to a cached page (e.g. Browse Drives) — visibly wait ~5s (your artificial `time.sleep(5)` on cache miss).
3. Reload the same page — instant load.

**Say:** First load is a cache miss — hits the DB, then Flask-Caching writes the result into Redis. Second load is a cache hit — served straight from Redis, no DB query at all.

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
3. (Optional, stronger) trigger `send_monthly_report` instead/also, to show the PDF attachment landing in Mailhog.

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
