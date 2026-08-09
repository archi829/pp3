from app import create_app
from models import (db, Admin, Company, Student, PlacementDrive,
                    Application, Notification, ApplicationStatusLog,
                    Interview, Placement)
from constants import ApplicationStatus, InterviewStatus, OfferStatus
from werkzeug.security import generate_password_hash
from datetime import date, datetime, timedelta, timezone
import os
import random

app = create_app()

with app.app_context():
    # ── Setup ──────────────────────────────────────────────────────────────
    os.makedirs('static/uploads/resumes', exist_ok=True)
    db.drop_all()
    db.create_all()
    print("Database tables created.")

    default_password = generate_password_hash('password123')

    # ── Admin ───────────────────────────────────────────────────────────────
    admin = Admin(
        username='admin',
        email='admin@placementportal.com',
        password_hash=generate_password_hash('admin123')
    )
    db.session.add(admin)

    # ── Companies ───────────────────────────────────────────────────────────
    companies_data = [
        ("TechNova Solutions",  "hr@technova.com",             "Software", "Approved", False),
        ("Global Finance Inc",  "careers@globalfinance.com",   "Finance",  "Approved", False),
        ("Pending Startup1",    "contact1@startup.com",        "Software", "Pending",  False),
        ("Pending Startup2",    "contact2@startup.com",        "Software", "Pending",  False),
        ("Sketchy Corp",        "admin@sketchy.com",           "Unknown",  "Rejected", False),
    ]

    companies = []
    for name, email, industry, status, blacklisted in companies_data:
        company = Company(
            company_name=name,
            email=email,
            password_hash=default_password,
            industry=industry,
            approval_status=status,
            is_blacklisted=blacklisted
        )
        db.session.add(company)
        companies.append(company)

    db.session.commit()

    # ── Students ────────────────────────────────────────────────────────────
    skills_pool  = ["Python", "Java", "C++", "React", "SQL"]
    demo_resumes = ["resume1.pdf", "resume2.pdf", "resume3.pdf", "resume4.pdf", "resume5.pdf"]
    students     = []

    for i in range(1, 11):
        if i == 1:
            # Intentional empty-profile student — tests "no resume / no CGPA" UI edge cases
            student = Student(
                full_name=f"Student {i}",
                email=f"student{i}@test.com",
                password_hash=default_password,
                cgpa=None,
                skills=None,
                resume_path=None,
            )
        else:
            student = Student(
                full_name=f"Student {i}",
                email=f"student{i}@test.com",
                password_hash=default_password,
                cgpa=round(random.uniform(6.5, 9.5), 2),
                skills=", ".join(random.sample(skills_pool, 3)),
                resume_path=f"uploads/resumes/{random.choice(demo_resumes)}"
            )
        db.session.add(student)
        students.append(student)

    db.session.commit()
    print(f"{len(students)} students created.")

    # ── Placement Drives (Approved) ─────────────────────────────────────────
    today              = date.today()
    approved_companies = [c for c in companies if c.approval_status == 'Approved']
    drives             = []

    drive_specs = [
        ("Software Engineer",    "Python, Django, SQL",    "8-12 LPA",  "Bangalore"),
        ("Frontend Developer",   "React, JavaScript, CSS", "6-10 LPA",  "Remote"),
        ("Data Analyst",         "Python, SQL, Excel",     "7-11 LPA",  "Mumbai"),
        ("DevOps Engineer",      "Linux, Docker, AWS",     "9-14 LPA",  "Hyderabad"),
        ("Full Stack Developer", "React, Node.js, SQL",    "10-15 LPA", "Pune"),
    ]

    for i, (title, skills, salary, location) in enumerate(drive_specs):
        drive = PlacementDrive(
            company_id=random.choice(approved_companies).id,
            job_title=title,
            job_description=f"We are looking for a skilled {title} to join our team.",
            required_skills=skills,
            eligibility_criteria="CGPA >= 7.0",
            min_cgpa=7.0,
            salary_range=salary,
            location=location,
            application_deadline=today + timedelta(days=10 + i),
            status="Approved"
        )
        db.session.add(drive)
        drives.append(drive)

    # ── Extra drives: Pending / Rejected / Closed ──────────────────────────
    # Gives admin approval queue something to show on first load
    extra_drives = [
        PlacementDrive(
            company_id=approved_companies[0].id,
            job_title="ML Intern",
            job_description="Work on ML pipelines and model deployment.",
            required_skills="Python, TensorFlow, sklearn",
            eligibility_criteria="CGPA >= 8.0",
            min_cgpa=8.0,
            salary_range="5-8 LPA",
            location="Bangalore",
            application_deadline=today + timedelta(days=15),
            status="Pending",
        ),
        PlacementDrive(
            company_id=approved_companies[0].id,
            job_title="QA Engineer",
            job_description="Test and validate software products.",
            required_skills="Selenium, JIRA, Python",
            eligibility_criteria="CGPA >= 6.0",
            min_cgpa=6.0,
            salary_range="4-7 LPA",
            location="Remote",
            application_deadline=today + timedelta(days=20),
            status="Rejected",
        ),
        PlacementDrive(
            company_id=approved_companies[1].id,
            job_title="Backend Intern",
            job_description="Build backend APIs for internal tools.",
            required_skills="Python, Flask, SQL",
            eligibility_criteria="CGPA >= 7.0",
            min_cgpa=7.0,
            salary_range="3-6 LPA",
            location="Pune",
            application_deadline=today + timedelta(days=5),
            status="Closed",
        ),
    ]
    db.session.add_all(extra_drives)

    db.session.commit()
    print(f"{len(drives)} approved drives + {len(extra_drives)} extra drives (Pending/Rejected/Closed) created.")

    # ── Applications + Status Log ───────────────────────────────────────────
    # Only seed simple statuses here; richer states are forced explicitly below.
    # Student 10 (students[-1]) intentionally gets ZERO applications → tests empty-state UI.
    students_with_apps = students[:-1]
    apps_to_add        = []

    for student in students_with_apps:
        num_drives    = min(len(drives), random.randint(2, 4))
        chosen_drives = random.sample(drives, num_drives)
        for drive in chosen_drives:
            app_entry = Application(
                student_id=student.id,
                drive_id=drive.id,
                status=random.choice(['Applied', 'Shortlisted', 'Rejected']),
            )
            db.session.add(app_entry)
            apps_to_add.append(app_entry)

    # Flush to get IDs before writing FK-dependent log rows
    db.session.flush()

    log_rows = 0
    for app_entry in apps_to_add:
        # Every application starts with an "Applied" log entry
        db.session.add(ApplicationStatusLog(
            application_id=app_entry.id,
            from_status=None,
            to_status='Applied',
            changed_by_role='student',
            changed_by_id=app_entry.student_id,
        ))
        log_rows += 1

        # Shortlisted apps get a second log row + student notification
        if app_entry.status == 'Shortlisted':
            db.session.add(ApplicationStatusLog(
                application_id=app_entry.id,
                from_status='Applied',
                to_status='Shortlisted',
                changed_by_role='company',
                changed_by_id=app_entry.drive.company_id,
            ))
            log_rows += 1
            db.session.add(Notification(
                user_type='student',
                user_id=app_entry.student_id,
                message=(f"Update: Your application for "
                         f"{app_entry.drive.job_title} is now 'Shortlisted'."),
            ))

    db.session.commit()
    print(f"{len(apps_to_add)} applications created.")
    print(f"{log_rows} status log rows seeded.")

    # ── Force 3 applications into fully demo-able states ───────────────────
    # Pick from students who have a resume so the demo profile looks complete.
    eligible_apps = [a for a in apps_to_add if a.student.resume_path]
    sample_apps   = random.sample(eligible_apps, min(3, len(eligible_apps)))

    for i, app_entry in enumerate(sample_apps):

        if i == 0:
            # ── Interview Scheduled (with real Interview row) ────────────────
            # Full log chain: Applied → Shortlisted → Interview Scheduled
            app_entry.status = ApplicationStatus.INTERVIEW_SCHEDULED
            for from_s, to_s in [
                (None,          'Applied'),
                ('Applied',     'Shortlisted'),
                ('Shortlisted', 'Interview Scheduled'),
            ]:
                db.session.add(ApplicationStatusLog(
                    application_id=app_entry.id,
                    from_status=from_s,
                    to_status=to_s,
                    changed_by_role='company',
                    changed_by_id=app_entry.drive.company_id,
                ))
            db.session.add(Interview(
                application_id=app_entry.id,
                scheduled_at=datetime.now(timezone.utc) + timedelta(days=2),
                mode="Online",
                location_or_link="https://meet.google.com/demo-link",
                status=InterviewStatus.SCHEDULED,
            ))
            # Notifications for both sides
            db.session.add(Notification(
                user_type='student',
                user_id=app_entry.student_id,
                message=(f"Interview scheduled for {app_entry.drive.job_title} "
                         f"in 2 days. Check the Interviews tab."),
            ))
            db.session.add(Notification(
                user_type='company',
                user_id=app_entry.drive.company_id,
                message=(f"Interview scheduled with {app_entry.student.full_name} "
                         f"for {app_entry.drive.job_title}."),
            ))

        elif i == 1:
            # ── Selected + Offer Accepted (with real Placement row) ──────────
            # Full log chain: Applied → Shortlisted → Interview Scheduled → Selected
            app_entry.status       = ApplicationStatus.SELECTED
            app_entry.offer_status = OfferStatus.ACCEPTED
            for from_s, to_s in [
                (None,                 'Applied'),
                ('Applied',            'Shortlisted'),
                ('Shortlisted',        'Interview Scheduled'),
                ('Interview Scheduled','Selected'),
            ]:
                db.session.add(ApplicationStatusLog(
                    application_id=app_entry.id,
                    from_status=from_s,
                    to_status=to_s,
                    changed_by_role='company',
                    changed_by_id=app_entry.drive.company_id,
                ))
            db.session.add(Placement(
                student_id=app_entry.student_id,
                company_id=app_entry.drive.company_id,
                drive_id=app_entry.drive_id,
                position=app_entry.drive.job_title,
                salary=app_entry.drive.salary_range,
                joining_date=date.today() + timedelta(days=30),
            ))
            db.session.add(Notification(
                user_type='student',
                user_id=app_entry.student_id,
                message=(f"Congratulations! You have been selected for "
                         f"{app_entry.drive.job_title}. Check your Placements tab."),
            ))
            db.session.add(Notification(
                user_type='company',
                user_id=app_entry.drive.company_id,
                message=(f"{app_entry.student.full_name} has been placed as "
                         f"{app_entry.drive.job_title}."),
            ))

        else:
            # ── Selected + Offer Pending (student hasn't responded yet) ──────
            # Shorter chain: Applied → Shortlisted → Selected
            app_entry.status       = ApplicationStatus.SELECTED
            app_entry.offer_status = OfferStatus.PENDING
            for from_s, to_s in [
                (None,      'Applied'),
                ('Applied', 'Shortlisted'),
                ('Shortlisted', 'Selected'),
            ]:
                db.session.add(ApplicationStatusLog(
                    application_id=app_entry.id,
                    from_status=from_s,
                    to_status=to_s,
                    changed_by_role='company',
                    changed_by_id=app_entry.drive.company_id,
                ))
            db.session.add(Placement(
                student_id=app_entry.student_id,
                company_id=app_entry.drive.company_id,
                drive_id=app_entry.drive_id,
                position=app_entry.drive.job_title,
                salary=app_entry.drive.salary_range,
                joining_date=date.today() + timedelta(days=45),
            ))
            db.session.add(Notification(
                user_type='student',
                user_id=app_entry.student_id,
                message=(f"You've been selected for {app_entry.drive.job_title}. "
                         f"Please respond to the offer in your Applications tab."),
            ))

    db.session.commit()
    print("3 demo-state applications seeded "
          "(Interview Scheduled, Selected+Accepted, Selected+Pending).")

    # ── Blacklist one student and one company for demo ─────────────────────
    # students[2] = Student 3 (has profile + some applications — good demo target)
    # companies[0] = TechNova Solutions (Approved, so blacklist behaviour is visible)
    students[2].is_blacklisted = True
    companies[0].is_blacklisted = True

    db.session.commit()
    print(f"Blacklisted: '{students[2].full_name}' (student) "
          f"and '{companies[0].company_name}' (company).")
    print("Seeding completed successfully!")