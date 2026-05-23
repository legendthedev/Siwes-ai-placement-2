"""
blueprints/schools.py — tech schools, test gate, enrollment, school admin dashboard
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import (Blueprint, render_template, redirect,
                   url_for, flash, request, abort)
from flask_login import login_required, current_user
from database import SessionLocal
from models import (TechSchool, SchoolCourse, PreliminaryQuestion,
                    TestAttempt, Student, SchoolEnrollment, User)

schools_bp = Blueprint("schools", __name__)
STATES    = ["Lagos", "Abuja", "Ibadan", "Calabar", "Kwara"]
PASS_MARK = 60.0


def _get_student(db):
    return db.query(Student).filter_by(user_id=current_user.id).first()

def _get_school_admin(db):
    return db.query(TechSchool).filter_by(user_id=current_user.id).first()

def _is_tech_school_student(student):
    return student and student.track == "tech_school"


# ── Listing ───────────────────────────────────────────────────────────────────
@schools_bp.route("/")
def listing():
    db = SessionLocal()
    try:
        state_filter = request.args.get("state", "")
        q = db.query(TechSchool)
        if state_filter:
            q = q.filter_by(state=state_filter)
        schools = q.order_by(TechSchool.state, TechSchool.name).all()
        return render_template("schools/listing.html",
                               schools=schools, states=STATES,
                               selected_state=state_filter)
    finally:
        db.close()


# ── Detail ────────────────────────────────────────────────────────────────────
@schools_bp.route("/<int:school_id>")
def detail(school_id):
    db = SessionLocal()
    try:
        school = db.query(TechSchool).filter_by(id=school_id).first()
        if not school:
            flash("School not found.", "danger")
            return redirect(url_for("schools.listing"))
        enrolled_course_ids = set()
        if current_user.is_authenticated and current_user.role == "student":
            student = _get_student(db)
            if student:
                enrolled_course_ids = {
                    e.course_id for e in
                    db.query(SchoolEnrollment).filter_by(
                        student_id=student.id, school_id=school_id).all()
                }
        return render_template("schools/detail.html", school=school,
                               enrolled_course_ids=enrolled_course_ids)
    finally:
        db.close()


# ── Preliminary test ──────────────────────────────────────────────────────────
@schools_bp.route("/course/<int:course_id>/test", methods=["GET", "POST"])
@login_required
def take_test(course_id):
    if current_user.role != "student":
        flash("Only students can take the preliminary test.", "warning")
        return redirect(url_for("schools.listing"))
    db = SessionLocal()
    try:
        course  = db.query(SchoolCourse).filter_by(id=course_id).first()
        if not course:
            flash("Course not found.", "danger")
            return redirect(url_for("schools.listing"))
        student = _get_student(db)

        # ── TRACK GATE ────────────────────────────────────────────────────
        if not _is_tech_school_student(student):
            flash(
                "⚠️ Preliminary tests are only available to students who selected "
                "<strong>Paid Tech School Internship</strong> as their track during "
                "registration. Visit your Profile to update your track.",
                "warning"
            )
            return redirect(url_for("schools.detail", school_id=course.school_id))

        questions = db.query(PreliminaryQuestion).filter_by(course_id=course_id).all()
        if not questions:
            flash("No test questions available for this course yet.", "warning")
            return redirect(url_for("schools.detail", school_id=course.school_id))

        # Block if already enrolled
        already = db.query(SchoolEnrollment).filter_by(
            student_id=student.id, course_id=course_id).first()
        if already:
            flash("You are already enrolled in this course.", "info")
            return redirect(url_for("schools.enrollment_status", enrollment_id=already.id))

        # Best previous attempt
        existing = (db.query(TestAttempt)
                    .filter_by(student_id=student.id, course_id=course_id)
                    .order_by(TestAttempt.score.desc()).first())

        if request.method == "POST":
            total_pts = sum(q.points for q in questions)
            earned, log = 0, {}
            for q in questions:
                chosen = request.form.get(f"q_{q.id}", "")
                log[str(q.id)] = chosen
                if chosen.strip().lower() == q.correct_answer.strip().lower():
                    earned += q.points
            pct    = round((earned / total_pts * 100) if total_pts else 0, 2)
            passed = pct >= PASS_MARK
            attempt = TestAttempt(
                student_id=student.id, course_id=course_id,
                answers=json.dumps(log), score=pct,
                passed=passed, pass_mark=PASS_MARK)
            db.add(attempt); db.commit()
            if passed:
                flash(f"🎉 You scored <strong>{pct}%</strong> — PASSED! "
                      f"You may now register for <strong>{course.name}</strong>.", "success")
            else:
                flash(f"❌ You scored <strong>{pct}%</strong>. "
                      f"Minimum pass mark is {PASS_MARK:.0f}%. Please review and retake.", "danger")
            return redirect(url_for("schools.test_result",
                                    course_id=course_id, attempt_id=attempt.id))

        return render_template("schools/test.html",
                               course=course, questions=questions,
                               existing=existing, pass_mark=PASS_MARK)
    finally:
        db.close()


# ── Test result + enrollment gate ─────────────────────────────────────────────
@schools_bp.route("/course/<int:course_id>/result/<int:attempt_id>")
@login_required
def test_result(course_id, attempt_id):
    db = SessionLocal()
    try:
        attempt   = db.query(TestAttempt).filter_by(id=attempt_id).first()
        course    = db.query(SchoolCourse).filter_by(id=course_id).first()
        questions = db.query(PreliminaryQuestion).filter_by(course_id=course_id).all()
        answers   = attempt.get_answers() if attempt else {}
        already_enrolled = None
        if current_user.is_authenticated and current_user.role == "student":
            student = _get_student(db)
            if student:
                already_enrolled = db.query(SchoolEnrollment).filter_by(
                    student_id=student.id, course_id=course_id).first()
        return render_template("schools/test_result.html",
                               attempt=attempt, course=course,
                               questions=questions, answers=answers,
                               pass_mark=PASS_MARK,
                               already_enrolled=already_enrolled)
    finally:
        db.close()


# ── Enrollment confirmation ───────────────────────────────────────────────────
@schools_bp.route("/course/<int:course_id>/enroll/<int:attempt_id>", methods=["GET","POST"])
@login_required
def enroll(course_id, attempt_id):
    if current_user.role != "student":
        abort(403)
    db = SessionLocal()
    try:
        student = _get_student(db)
        course  = db.query(SchoolCourse).filter_by(id=course_id).first()
        attempt = db.query(TestAttempt).filter_by(
            id=attempt_id, student_id=student.id, course_id=course_id).first()

        if not _is_tech_school_student(student):
            flash("Enrollment is only for students on the Tech School track.", "danger")
            return redirect(url_for("schools.listing"))
        if not attempt or not attempt.passed:
            flash("❌ You must pass the preliminary test before enrolling.", "danger")
            return redirect(url_for("schools.take_test", course_id=course_id))

        existing = db.query(SchoolEnrollment).filter_by(
            student_id=student.id, course_id=course_id).first()
        if existing:
            flash("You are already enrolled in this course.", "info")
            return redirect(url_for("schools.enrollment_status", enrollment_id=existing.id))

        if request.method == "POST":
            amount = course.siwes_price_ngn or course.price_ngn
            e = SchoolEnrollment(
                student_id=student.id, school_id=course.school_id,
                course_id=course_id, attempt_id=attempt_id,
                test_score=attempt.score, amount_ngn=amount,
                status="pending_payment")
            db.add(e); db.commit()
            flash(
                f"✅ Enrollment submitted for <strong>{course.name}</strong>! "
                f"SIWES fee: <strong>₦{amount:,}</strong>. "
                "The school will confirm after payment.", "success")
            return redirect(url_for("schools.enrollment_status", enrollment_id=e.id))

        return render_template("schools/enroll_confirm.html",
                               course=course, attempt=attempt, student=student)
    finally:
        db.close()


# ── Enrollment status (student) ───────────────────────────────────────────────
@schools_bp.route("/enrollment/<int:enrollment_id>")
@login_required
def enrollment_status(enrollment_id):
    db = SessionLocal()
    try:
        enrollment = db.query(SchoolEnrollment).filter_by(id=enrollment_id).first()
        if not enrollment:
            flash("Enrollment not found.", "danger")
            return redirect(url_for("schools.listing"))
        if current_user.role == "student":
            student = _get_student(db)
            if not student or enrollment.student_id != student.id:
                abort(403)
        return render_template("schools/enrollment_status.html", enrollment=enrollment)
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
# SCHOOL ADMIN DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
@schools_bp.route("/dashboard")
@login_required
def school_dashboard():
    if current_user.role != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("auth.login"))
    db = SessionLocal()
    try:
        school = _get_school_admin(db)
        if not school:
            return redirect(url_for("admin.dashboard"))

        enrollments = (db.query(SchoolEnrollment)
                       .filter_by(school_id=school.id)
                       .order_by(SchoolEnrollment.enrolled_at.desc()).all())

        from collections import defaultdict
        course_stats = defaultdict(lambda: {"name":"","pending":0,"paid":0,"enrolled":0,"total":0})
        for c in school.courses:
            course_stats[c.id]["name"] = c.name
        for e in enrollments:
            s = "pending" if e.status == "pending_payment" else e.status
            if s in ("paid","enrolled","pending"):
                course_stats[e.course_id][s] += 1
                course_stats[e.course_id]["total"] += 1

        return render_template("schools/school_dashboard.html",
                               school=school,
                               enrollments=enrollments,
                               pending   =[e for e in enrollments if e.status=="pending_payment"],
                               paid      =[e for e in enrollments if e.status=="paid"],
                               enrolled  =[e for e in enrollments if e.status=="enrolled"],
                               course_stats=dict(course_stats))
    finally:
        db.close()


@schools_bp.route("/enrollment/<int:enrollment_id>/confirm", methods=["POST"])
@login_required
def confirm_enrollment(enrollment_id):
    if current_user.role != "admin":
        abort(403)
    db = SessionLocal()
    try:
        school     = _get_school_admin(db)
        enrollment = db.query(SchoolEnrollment).filter_by(
            id=enrollment_id, school_id=school.id).first()
        if not enrollment:
            flash("Enrollment not found.", "danger")
            return redirect(url_for("schools.school_dashboard"))
        new_status = request.form.get("new_status", "enrolled")
        enrollment.status = new_status
        from datetime import datetime
        if new_status == "enrolled":
            enrollment.confirmed_at = datetime.utcnow()
        db.commit()
        flash(f"Enrollment #{enrollment_id} updated to <strong>{new_status}</strong>.", "success")
        return redirect(url_for("schools.school_dashboard"))
    finally:
        db.close()
