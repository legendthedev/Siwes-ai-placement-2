"""blueprints/student.py — student dashboard, CV upload, results, SHAP"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from database import SessionLocal
from models import Student, CV, Placement, Company, JobDescription, ShapExplanation

student_bp = Blueprint("student", __name__)

ALLOWED_EXT = {"pdf"}


def _allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def _get_student(db):
    return db.query(Student).filter_by(user_id=current_user.id).first()


# ── Dashboard ────────────────────────────────────────────────────────────────
@student_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role != "student":
        return redirect(url_for("admin.dashboard"))
    db = SessionLocal()
    try:
        student = _get_student(db)
        placement = (db.query(Placement)
                     .filter_by(student_id=student.id)
                     .order_by(Placement.created_at.desc())
                     .first()) if student else None
        company = db.query(Company).filter_by(id=placement.company_id).first() if placement else None
        jd      = db.query(JobDescription).filter_by(id=placement.job_description_id).first() if placement else None
        return render_template("student/dashboard.html",
                               student=student, placement=placement,
                               company=company, jd=jd)
    finally:
        db.close()


# ── Upload / re-upload CV ─────────────────────────────────────────────────────
@student_bp.route("/cv", methods=["GET", "POST"])
@login_required
def upload_cv():
    if current_user.role != "student":
        return redirect(url_for("admin.dashboard"))
    db = SessionLocal()
    try:
        student = _get_student(db)
        if not student:
            flash("Student profile not found.", "danger")
            return redirect(url_for("auth.login"))

        if request.method == "POST":
            file = request.files.get("cv_file")
            if not file or not _allowed(file.filename):
                flash("Please upload a valid PDF file.", "danger")
                return redirect(request.url)

            filename  = secure_filename(f"student_{student.id}_{file.filename}")
            save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)

            # Extract text with pdfplumber
            raw_text = ""
            try:
                import pdfplumber
                with pdfplumber.open(save_path) as pdf:
                    raw_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
            except Exception:
                pass

            # Run spaCy NER
            try:
                from pipeline.extractor import get_extractor
                extractor = get_extractor()
                extracted = extractor.extract_from_cv(raw_text)
            except Exception:
                extracted = {"skills": [], "location": student.location, "department": student.department}

            cv_record = db.query(CV).filter_by(student_id=student.id).first()
            if not cv_record:
                cv_record = CV(student_id=student.id)
                db.add(cv_record)

            cv_record.filename             = filename
            cv_record.raw_text             = raw_text
            cv_record.extracted_location   = extracted.get("location") or student.location
            cv_record.extracted_department = extracted.get("department") or student.department
            cv_record.skill_vector         = None   # will re-encode on next placement run
            cv_record.set_skills(extracted.get("skills", []))

            # Also accept manually entered skills to supplement NER
            manual_skills = request.form.get("manual_skills", "")
            if manual_skills:
                extra = [s.strip().lower() for s in manual_skills.split(",") if s.strip()]
                merged = list(set(cv_record.get_skills() + extra))
                cv_record.set_skills(merged)

            db.commit()
            flash("CV uploaded and skills extracted successfully!", "success")
            return redirect(url_for("student.profile"))

        cv_record = db.query(CV).filter_by(student_id=student.id).first()
        return render_template("student/upload_cv.html", student=student, cv=cv_record)
    finally:
        db.close()


# ── Profile ───────────────────────────────────────────────────────────────────
@student_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if current_user.role != "student":
        return redirect(url_for("admin.dashboard"))
    db = SessionLocal()
    try:
        student = _get_student(db)
        cv      = db.query(CV).filter_by(student_id=student.id).first() if student else None

        if request.method == "POST":
            f = request.form
            student.name       = f.get("name", student.name).strip()
            student.phone      = f.get("phone", student.phone).strip()
            student.university = f.get("university", student.university).strip()
            student.department = f.get("department", student.department).strip()
            student.level      = int(f.get("level", student.level))
            student.location   = f.get("location", student.location).strip()
            student.bio        = f.get("bio", "").strip()
            student.linkedin   = f.get("linkedin", "").strip() or None
            student.github     = f.get("github", "").strip() or None
            db.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("student.profile"))

        return render_template("student/profile.html", student=student, cv=cv)
    finally:
        db.close()


# ── Placement result ──────────────────────────────────────────────────────────
@student_bp.route("/result")
@login_required
def result():
    if current_user.role != "student":
        return redirect(url_for("admin.dashboard"))
    db = SessionLocal()
    try:
        student   = _get_student(db)
        placement = (db.query(Placement)
                     .filter_by(student_id=student.id)
                     .order_by(Placement.created_at.desc())
                     .first()) if student else None
        company   = db.query(Company).filter_by(id=placement.company_id).first()  if placement else None
        jd        = db.query(JobDescription).filter_by(id=placement.job_description_id).first() if placement else None
        shap_rows = (db.query(ShapExplanation)
                     .filter_by(placement_id=placement.id)
                     .order_by(ShapExplanation.shap_value.desc())
                     .all()) if placement else []

        strengths  = [r for r in shap_rows if r.in_student_cv and r.in_job_req and r.shap_value > 0][:5]
        skill_gaps = [r for r in shap_rows if r.in_job_req and not r.in_student_cv][:5]

        return render_template("student/result.html",
                               student=student, placement=placement,
                               company=company, jd=jd,
                               shap_rows=shap_rows,
                               strengths=strengths, skill_gaps=skill_gaps)
    finally:
        db.close()
