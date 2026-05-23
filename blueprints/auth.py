"""blueprints/auth.py — login · unified register page · logout"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from database import SessionLocal
from models import User, Student, Company

auth_bp = Blueprint("auth", __name__)

STATES_LOCATIONS = {'Lagos': ['Victoria Island', 'Lekki', 'Yaba', 'Ikeja', 'Ikoyi', 'Surulere', 'Ajah', 'Lagos Island', 'Apapa', 'Oshodi', 'Mushin', 'Ikorodu', 'Gbagada', 'Festac', 'Badagry', 'Epe'], 'Abuja': ['Wuse 2', 'Maitama', 'Garki', 'Central Business District', 'Asokoro', 'Gwarinpa', 'Jabi', 'Utako', 'Area 1', 'Area 3', 'Kubwa', 'Nyanya', 'Lugbe'], 'Ibadan': ['Ring Road', 'Bodija', 'UI Campus', 'Challenge', 'Dugbe', 'New Bodija', 'Agodi', 'Iwo Road', 'Molete', 'Ojoo', 'Oluyole', 'Sango'], 'Calabar': ['State Housing', 'MCC Road', 'Efio-Ette', 'Marian', 'Atimbo', '8 Miles', 'Satellite Town', 'Ikot Ansa', 'Lemna Road'], 'Kwara': ['GRA Ilorin', 'University Road Ilorin', 'Tanke', 'Fate Road', 'Offa Garage', 'Basin', 'Ganmo', 'Asa Dam Road', 'Ahmadu Bello Way']}

@auth_bp.route("/", methods=["GET","POST"])
@auth_bp.route("/login", methods=["GET","POST"])
def login():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user.role, current_user.id)
    if request.method == "POST":
        email    = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        db = SessionLocal()
        try:
            user = db.query(User).filter_by(email=email).first()
            if user and user.check_password(password):
                login_user(user, remember=True)
                flash("Welcome back!", "success")
                return _redirect_by_role(user.role, user.id)
            flash("Invalid email or password.", "danger")
        finally:
            db.close()
    return render_template("auth/login.html",
                           states=list(STATES_LOCATIONS.keys()),
                           states_locations=STATES_LOCATIONS)


@auth_bp.route("/register/student", methods=["GET","POST"])
def register_student():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user.role, current_user.id)
    if request.method == "POST":
        f     = request.form
        email = f.get("email","").strip().lower()
        db    = SessionLocal()
        try:
            if db.query(User).filter_by(email=email).first():
                flash("An account with this email already exists.", "danger")
                return render_template("auth/register_student.html", form=f,
                                       states=list(STATES_LOCATIONS.keys()),
                                       states_locations=STATES_LOCATIONS)
            pw  = f.get("password","")
            pw2 = f.get("confirm","")
            if pw != pw2:
                flash("Passwords do not match.", "danger")
                return render_template("auth/register_student.html", form=f,
                                       states=list(STATES_LOCATIONS.keys()),
                                       states_locations=STATES_LOCATIONS)
            user = User(email=email, role="student")
            user.set_password(pw)
            db.add(user); db.flush()
            student = Student(
                user_id=user.id, name=f.get("name","").strip(),
                email=email, phone=f.get("phone","").strip(),
                university=f.get("university","").strip(),
                department=f.get("department","").strip(),
                level=int(f.get("level",300)),
                state=f.get("state","Lagos").strip(),
                location=f.get("location","").strip(),
                matric_no=f.get("matric_no","").strip() or None,
                bio=f.get("bio","").strip(),
                linkedin=f.get("linkedin","").strip() or None,
                github=f.get("github","").strip() or None,
                track=f.get("track","placement"),
            )
            db.add(student); db.commit()
            login_user(user, remember=True)
            flash("Account created! Please upload your CV.", "success")
            return redirect(url_for("student.upload_cv"))
        except Exception as e:
            db.rollback()
            flash(f"Registration failed: {e}", "danger")
        finally:
            db.close()
    return render_template("auth/register_student.html", form={},
                           states=list(STATES_LOCATIONS.keys()),
                           states_locations=STATES_LOCATIONS)


@auth_bp.route("/register/admin", methods=["GET","POST"])
def register_admin():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user.role, current_user.id)
    if request.method == "POST":
        f     = request.form
        email = f.get("email","").strip().lower()
        db    = SessionLocal()
        try:
            if db.query(User).filter_by(email=email).first():
                flash("An account with this email already exists.", "danger")
                return render_template("auth/register_admin.html", form=f,
                                       states=list(STATES_LOCATIONS.keys()),
                                       states_locations=STATES_LOCATIONS)
            pw  = f.get("password","")
            pw2 = f.get("confirm","")
            if pw != pw2:
                flash("Passwords do not match.", "danger")
                return render_template("auth/register_admin.html", form=f,
                                       states=list(STATES_LOCATIONS.keys()),
                                       states_locations=STATES_LOCATIONS)
            user = User(email=email, role="admin")
            user.set_password(pw)
            db.add(user); db.flush()
            company = Company(
                user_id=user.id,
                name=f.get("company_name","").strip(),
                email=email,
                industry=f.get("industry","").strip(),
                state=f.get("state","Lagos").strip(),
                location=f.get("location","").strip(),
                website=f.get("website","").strip() or None,
                description=f.get("description","").strip(),
                verified=False,
            )
            db.add(company); db.commit()
            login_user(user, remember=True)
            flash("Company registered! Add your job descriptions below. Your account is pending verification.", "success")
            return redirect(url_for("admin.dashboard"))
        except Exception as e:
            db.rollback()
            flash(f"Registration failed: {e}", "danger")
        finally:
            db.close()
    return render_template("auth/register_admin.html", form={},
                           states=list(STATES_LOCATIONS.keys()),
                           states_locations=STATES_LOCATIONS)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


# HTMX: return location <option> tags for a given state
@auth_bp.route("/api/locations/<state>")
def locations_for_state(state):
    locs = STATES_LOCATIONS.get(state, [])
    return "".join(f'<option value="{l}">{l}, {state}</option>' for l in locs)


def _redirect_by_role(role, user_id=None):
    if role == "student":
        return redirect(url_for("student.dashboard"))
    # For admins: detect whether they manage a company or a tech school
    from database import SessionLocal as _SL
    from models import User as _U, Company as _C, TechSchool as _TS
    db = _SL()
    try:
        user = db.query(_U).filter_by(email=current_user.email).first()
        if user:
            if db.query(_TS).filter_by(user_id=user.id).first():
                return redirect(url_for("schools.school_dashboard"))
    finally:
        db.close()
    return redirect(url_for("admin.dashboard"))
