"""blueprints/admin.py — company dashboard, JD CRUD, verification, placement trigger"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from database import SessionLocal
from models import Company, JobDescription, Placement, Student, PlacementBatch, User

admin_bp = Blueprint("admin", __name__)

STATES_LOCATIONS = {'Lagos': ['Victoria Island', 'Lekki', 'Yaba', 'Ikeja', 'Ikoyi', 'Surulere', 'Ajah', 'Lagos Island', 'Apapa', 'Oshodi', 'Mushin', 'Ikorodu', 'Gbagada', 'Ojota', 'Anthony', 'Maryland', 'Agege', 'Badagry', 'Epe', 'Festac', 'Amuwo-Odofin'], 'Abuja': ['Wuse 2', 'Maitama', 'Garki', 'Central Business District', 'Asokoro', 'Gwarinpa', 'Jabi', 'Utako', 'Area 1', 'Area 3', 'Kubwa', 'Nyanya', 'Lugbe'], 'Ibadan': ['Ring Road', 'Bodija', 'UI Campus', 'Challenge', 'Dugbe', 'New Bodija', 'Agodi', 'Iwo Road', 'Molete', 'Ojoo', 'Oluyole', 'Sango'], 'Calabar': ['State Housing', 'MCC Road', 'Efio-Ette', 'Marian', 'Atimbo', '8 Miles', 'Satellite Town', 'Ikot Ansa', 'Lemna Road'], 'Kwara': ['GRA Ilorin', 'University Road Ilorin', 'Tanke', 'Fate Road', 'Offa Garage', 'Basin', 'Ganmo', 'Asa Dam Road', 'Ahmadu Bello Way']}

def _get_company(db):
    return db.query(Company).filter_by(user_id=current_user.id).first()

def _require_admin():
    if current_user.role != "admin":
        return redirect(url_for("student.dashboard"))
    return None


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    redir = _require_admin()
    if redir: return redir
    db = SessionLocal()
    try:
        company = _get_company(db)
        jds     = db.query(JobDescription).filter_by(company_id=company.id).all() if company else []
        total_quota    = sum(j.quota for j in jds)
        remaining_total= sum(
            j.remaining_quota if j.remaining_quota is not None else j.quota
            for j in jds
        )
        placements = []
        if company:
            placements = (db.query(Placement).filter_by(company_id=company.id)
                          .order_by(Placement.created_at.desc()).all())

        # Count placements per JD so template can show "X placed" per row
        from collections import Counter
        jd_placed_counts = Counter(p.job_description_id for p in placements)

        recent_batch = (db.query(PlacementBatch)
                        .order_by(PlacementBatch.run_at.desc()).first())
        return render_template("admin/dashboard.html",
                               company=company, jds=jds,
                               total_quota=total_quota,
                               remaining_total=remaining_total,
                               jd_placed_counts=jd_placed_counts,
                               placements=placements,
                               recent_batch=recent_batch)
    finally:
        db.close()


@admin_bp.route("/company/edit", methods=["GET","POST"])
@login_required
def edit_company():
    redir = _require_admin()
    if redir: return redir
    db = SessionLocal()
    try:
        company = _get_company(db)
        if not company:
            flash("Company profile not found.", "danger")
            return redirect(url_for("admin.dashboard"))
        if request.method == "POST":
            f = request.form
            company.name        = f.get("company_name", company.name).strip()
            company.industry    = f.get("industry", company.industry).strip()
            company.state       = f.get("state", company.state).strip()
            company.location    = f.get("location", company.location).strip()
            company.website     = f.get("website","").strip() or None
            company.description = f.get("description","").strip()
            db.commit()
            flash("Company profile updated.", "success")
            return redirect(url_for("admin.dashboard"))
        return render_template("admin/edit_company.html", company=company,
                               states=list(STATES_LOCATIONS.keys()),
                               states_locations=STATES_LOCATIONS)
    finally:
        db.close()


@admin_bp.route("/jd/add", methods=["GET","POST"])
@login_required
def add_jd():
    redir = _require_admin()
    if redir: return redir
    db = SessionLocal()
    try:
        company = _get_company(db)
        if not company:
            flash("Complete your company profile first.", "warning")
            return redirect(url_for("admin.edit_company"))
        if request.method == "POST":
            f      = request.form
            skills = [s.strip().lower() for s in f.get("required_skills","").split(",") if s.strip()]
            jd = JobDescription(
                company_id=company.id,
                title=f.get("title","").strip(),
                raw_text=f.get("raw_text","").strip(),
                target_department=f.get("target_department","").strip(),
                location=f.get("location", company.location).strip(),
                quota=max(1, int(f.get("quota", 1))),
                additional_requirements=f.get("additional_requirements","").strip(),
            )
            jd.set_required_skills(skills)
            db.add(jd); db.commit()
            flash(f'Job description "{jd.title}" added.', "success")
            return redirect(url_for("admin.dashboard"))
        return render_template("admin/jd_form.html", company=company, jd=None,
                               states=list(STATES_LOCATIONS.keys()),
                               states_locations=STATES_LOCATIONS)
    finally:
        db.close()


@admin_bp.route("/jd/<int:jd_id>/edit", methods=["GET","POST"])
@login_required
def edit_jd(jd_id):
    redir = _require_admin()
    if redir: return redir
    db = SessionLocal()
    try:
        company = _get_company(db)
        jd = db.query(JobDescription).filter_by(id=jd_id, company_id=company.id).first()
        if not jd:
            flash("Job description not found.", "danger")
            return redirect(url_for("admin.dashboard"))
        if request.method == "POST":
            f      = request.form
            skills = [s.strip().lower() for s in f.get("required_skills","").split(",") if s.strip()]
            jd.title                   = f.get("title", jd.title).strip()
            jd.raw_text                = f.get("raw_text", jd.raw_text).strip()
            jd.target_department       = f.get("target_department","").strip()
            jd.location                = f.get("location", jd.location).strip()
            jd.quota                   = max(1, int(f.get("quota", jd.quota)))
            jd.additional_requirements = f.get("additional_requirements","").strip()
            jd.requirement_vector      = None   # invalidate so it re-encodes
            jd.set_required_skills(skills)
            db.commit()
            flash("Job description updated.", "success")
            return redirect(url_for("admin.dashboard"))
        return render_template("admin/jd_form.html", company=company, jd=jd,
                               skills_csv=", ".join(jd.get_required_skills()),
                               states=list(STATES_LOCATIONS.keys()),
                               states_locations=STATES_LOCATIONS)
    finally:
        db.close()


@admin_bp.route("/jd/<int:jd_id>/delete", methods=["POST"])
@login_required
def delete_jd(jd_id):
    redir = _require_admin()
    if redir: return redir
    db = SessionLocal()
    try:
        company = _get_company(db)
        jd = db.query(JobDescription).filter_by(id=jd_id, company_id=company.id).first()
        if jd:
            db.delete(jd); db.commit()
            flash("Job description deleted.", "info")
    finally:
        db.close()
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/jd/<int:jd_id>/applicants")
@login_required
def jd_applicants(jd_id):
    redir = _require_admin()
    if redir: return redir
    db = SessionLocal()
    try:
        company = _get_company(db)
        jd = db.query(JobDescription).filter_by(id=jd_id, company_id=company.id).first()
        if not jd:
            flash("Not found.", "danger")
            return redirect(url_for("admin.dashboard"))
        rows = (db.query(Placement, Student)
                .join(Student, Student.id == Placement.student_id)
                .filter(Placement.job_description_id == jd_id)
                .order_by(Placement.match_score.desc()).all())
        return render_template("admin/applicants.html", company=company, jd=jd, placements=rows)
    finally:
        db.close()


@admin_bp.route("/run-placement", methods=["POST"])
@login_required
def run_placement():
    redir = _require_admin()
    if redir: return redir
    label = request.form.get("label","Placement Run 2024/2025").strip()
    try:
        from placement_engine import PlacementEngine
        engine = PlacementEngine()
        batch_id, report = engine.run_placement(batch_label=label)
        flash(f"✅ Placement complete! Batch {batch_id} — "
              f"{report.placed_students}/{report.total_students} students placed "
              f"({report.match_rate:.0%} match rate).", "success")
    except Exception as e:
        flash(f"Placement failed: {e}", "danger")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/students")
@login_required
def all_students():
    redir = _require_admin()
    if redir: return redir
    db = SessionLocal()
    try:
        students = db.query(Student).order_by(Student.created_at.desc()).all()
        return render_template("admin/students.html", students=students)
    finally:
        db.close()


# HTMX endpoint — return location options for a given state
@admin_bp.route("/locations/<state>")
def locations_for_state(state):
    locs = STATES_LOCATIONS.get(state, [])
    opts = "".join(f'<option value="{l}">{l}</option>' for l in locs)
    return opts
