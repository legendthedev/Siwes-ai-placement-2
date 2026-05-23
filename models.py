"""
models.py — Full ORM for SIWES Placement Portal
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
import json, pickle
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    Text, DateTime, ForeignKey, LargeBinary
)
from sqlalchemy.orm import relationship
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from database import Base


class User(UserMixin, Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True)
    email         = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    role          = Column(String(20), nullable=False)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    student = relationship("Student", back_populates="user", uselist=False)
    company = relationship("Company",  back_populates="user",  uselist=False)
    school  = relationship("TechSchool", back_populates="user", uselist=False)
    def set_password(self, pw): self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)


class Student(Base):
    __tablename__ = "students"
    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    name        = Column(String(100), nullable=False)
    email       = Column(String(120), unique=True, nullable=False)
    phone       = Column(String(20))
    university  = Column(String(150), nullable=False)
    department  = Column(String(100), nullable=False)
    level       = Column(Integer, nullable=False)
    state       = Column(String(50), nullable=False)
    location    = Column(String(100), nullable=False)
    matric_no   = Column(String(30), unique=True)
    bio         = Column(Text)
    linkedin    = Column(String(200))
    github      = Column(String(200))
    track       = Column(String(20), default="placement")
    created_at  = Column(DateTime, default=datetime.utcnow)
    user          = relationship("User", back_populates="student")
    cv            = relationship("CV", back_populates="student", uselist=False)
    placements    = relationship("Placement", back_populates="student")
    test_attempts = relationship("TestAttempt", back_populates="student")
    school_enrollments = relationship("SchoolEnrollment", back_populates="student")


class CV(Base):
    __tablename__ = "cvs"
    id                   = Column(Integer, primary_key=True)
    student_id           = Column(Integer, ForeignKey("students.id"), unique=True, nullable=False)
    filename             = Column(String(200))
    raw_text             = Column(Text)
    extracted_skills     = Column(Text)
    extracted_location   = Column(String(100))
    extracted_department = Column(String(100))
    skill_vector         = Column(LargeBinary)
    uploaded_at          = Column(DateTime, default=datetime.utcnow)
    student = relationship("Student", back_populates="cv")
    def get_skills(self): return json.loads(self.extracted_skills) if self.extracted_skills else []
    def get_vector(self): return pickle.loads(self.skill_vector) if self.skill_vector else None
    def set_skills(self, s): self.extracted_skills = json.dumps(s)
    def set_vector(self, v): self.skill_vector = pickle.dumps(v)


class Company(Base):
    __tablename__ = "companies"
    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True)
    name        = Column(String(150), unique=True, nullable=False)
    email       = Column(String(120), unique=True, nullable=False)
    industry    = Column(String(100))
    state       = Column(String(50))
    location    = Column(String(100), nullable=False)
    website     = Column(String(200))
    description = Column(Text)
    verified    = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)
    user             = relationship("User", back_populates="company")
    job_descriptions = relationship("JobDescription", back_populates="company", cascade="all, delete-orphan")


class JobDescription(Base):
    __tablename__ = "job_descriptions"
    id                      = Column(Integer, primary_key=True)
    company_id              = Column(Integer, ForeignKey("companies.id"), nullable=False)
    title                   = Column(String(150), nullable=False)
    raw_text                = Column(Text, nullable=False)
    required_skills         = Column(Text)
    target_department       = Column(String(100))
    location                = Column(String(100))
    quota                   = Column(Integer, default=1)
    remaining_quota         = Column(Integer, nullable=True)  # decrements as students are placed
    additional_requirements = Column(Text)
    requirement_vector      = Column(LargeBinary)
    created_at              = Column(DateTime, default=datetime.utcnow)
    company           = relationship("Company", back_populates="job_descriptions")
    similarity_scores = relationship("SimilarityScore", back_populates="job_description")
    placements        = relationship("Placement", back_populates="job_description")
    def get_required_skills(self): return json.loads(self.required_skills) if self.required_skills else []
    def get_vector(self): return pickle.loads(self.requirement_vector) if self.requirement_vector else None
    def set_required_skills(self, s): self.required_skills = json.dumps(s)
    def set_vector(self, v): self.requirement_vector = pickle.dumps(v)


class PlacementBatch(Base):
    __tablename__ = "placement_batches"
    id              = Column(Integer, primary_key=True)
    label           = Column(String(100), nullable=False)
    status          = Column(String(20), default="pending")
    total_students  = Column(Integer, default=0)
    placed_students = Column(Integer, default=0)
    run_at          = Column(DateTime, default=datetime.utcnow)
    scores     = relationship("SimilarityScore", back_populates="batch")
    placements = relationship("Placement", back_populates="batch")


class SimilarityScore(Base):
    __tablename__ = "similarity_scores"
    id                 = Column(Integer, primary_key=True)
    batch_id           = Column(Integer, ForeignKey("placement_batches.id"), nullable=False)
    student_id         = Column(Integer, ForeignKey("students.id"), nullable=False)
    job_description_id = Column(Integer, ForeignKey("job_descriptions.id"), nullable=False)
    score              = Column(Float, nullable=False)
    location_match     = Column(Boolean, default=True)
    dept_match         = Column(Boolean, default=True)
    computed_at        = Column(DateTime, default=datetime.utcnow)
    batch           = relationship("PlacementBatch", back_populates="scores")
    student         = relationship("Student")
    job_description = relationship("JobDescription", back_populates="similarity_scores")


class Placement(Base):
    __tablename__ = "placements"
    id                 = Column(Integer, primary_key=True)
    batch_id           = Column(Integer, ForeignKey("placement_batches.id"), nullable=False)
    student_id         = Column(Integer, ForeignKey("students.id"), nullable=False)
    company_id         = Column(Integer, ForeignKey("companies.id"), nullable=False)
    job_description_id = Column(Integer, ForeignKey("job_descriptions.id"), nullable=False)
    match_score        = Column(Float, nullable=False)
    status             = Column(String(20), default="assigned")
    created_at         = Column(DateTime, default=datetime.utcnow)
    batch           = relationship("PlacementBatch", back_populates="placements")
    student         = relationship("Student", back_populates="placements")
    company         = relationship("Company")
    job_description = relationship("JobDescription", back_populates="placements")
    shap_values     = relationship("ShapExplanation", back_populates="placement", cascade="all, delete-orphan")


class ShapExplanation(Base):
    __tablename__ = "shap_explanations"
    id            = Column(Integer, primary_key=True)
    placement_id  = Column(Integer, ForeignKey("placements.id"), nullable=False)
    feature_name  = Column(String(100), nullable=False)
    shap_value    = Column(Float, nullable=False)
    in_student_cv = Column(Boolean, default=False)
    in_job_req    = Column(Boolean, default=False)
    created_at    = Column(DateTime, default=datetime.utcnow)
    placement = relationship("Placement", back_populates="shap_values")


class TechSchool(Base):
    __tablename__ = "tech_schools"
    id                  = Column(Integer, primary_key=True)
    user_id             = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True)
    name                = Column(String(150), unique=True, nullable=False)
    state               = Column(String(50), nullable=False)
    location            = Column(String(150), nullable=False)
    website             = Column(String(200))
    description         = Column(Text)
    siwes_discount_pct  = Column(Integer, default=0)
    siwes_discount_note = Column(Text)
    contact_email       = Column(String(120))
    created_at          = Column(DateTime, default=datetime.utcnow)
    user    = relationship("User", back_populates="school")
    courses = relationship("SchoolCourse", back_populates="school", cascade="all, delete-orphan")
    enrollments = relationship("SchoolEnrollment", back_populates="school")


class SchoolCourse(Base):
    __tablename__ = "school_courses"
    id              = Column(Integer, primary_key=True)
    school_id       = Column(Integer, ForeignKey("tech_schools.id"), nullable=False)
    name            = Column(String(150), nullable=False)
    duration_months = Column(Integer, nullable=False)
    price_ngn       = Column(Integer, nullable=False)
    siwes_price_ngn = Column(Integer)
    skills          = Column(Text)
    description     = Column(Text)
    created_at      = Column(DateTime, default=datetime.utcnow)
    school    = relationship("TechSchool", back_populates="courses")
    questions = relationship("PreliminaryQuestion", back_populates="course", cascade="all, delete-orphan")
    attempts  = relationship("TestAttempt", back_populates="course")
    enrollments = relationship("SchoolEnrollment", back_populates="course")
    def get_skills(self): return json.loads(self.skills) if self.skills else []
    def set_skills(self, s): self.skills = json.dumps(s)
    @property
    def discount_pct(self):
        if self.siwes_price_ngn and self.price_ngn:
            return round((1 - self.siwes_price_ngn / self.price_ngn) * 100)
        return self.school.siwes_discount_pct if self.school else 0


class PreliminaryQuestion(Base):
    __tablename__ = "preliminary_questions"
    id             = Column(Integer, primary_key=True)
    course_id      = Column(Integer, ForeignKey("school_courses.id"), nullable=False)
    question       = Column(Text, nullable=False)
    options        = Column(Text, nullable=False)
    correct_answer = Column(String(200), nullable=False)
    points         = Column(Integer, default=2)
    skill_domain   = Column(String(50))
    created_at     = Column(DateTime, default=datetime.utcnow)
    course = relationship("SchoolCourse", back_populates="questions")
    def get_options(self): return json.loads(self.options) if self.options else []


class TestAttempt(Base):
    __tablename__ = "test_attempts"
    id         = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    course_id  = Column(Integer, ForeignKey("school_courses.id"), nullable=False)
    answers    = Column(Text)
    score      = Column(Float)
    passed     = Column(Boolean, default=False)
    pass_mark  = Column(Float, default=60.0)
    taken_at   = Column(DateTime, default=datetime.utcnow)
    student = relationship("Student", back_populates="test_attempts")
    course  = relationship("SchoolCourse", back_populates="attempts")
    enrollments = relationship("SchoolEnrollment", back_populates="test_attempt")
    def get_answers(self): return json.loads(self.answers) if self.answers else {}

class SchoolEnrollment(Base):
    __tablename__ = "school_enrollments"
    
    id           = Column(Integer, primary_key=True)
    student_id   = Column(Integer, ForeignKey("students.id"), nullable=False)
    school_id    = Column(Integer, ForeignKey("tech_schools.id"), nullable=False)
    course_id    = Column(Integer, ForeignKey("school_courses.id"), nullable=False)
    attempt_id   = Column(Integer, ForeignKey("test_attempts.id"), nullable=False)
    
    test_score   = Column(Float)
    amount_ngn   = Column(Integer)
    status       = Column(String(20), default="pending_payment")
    enrolled_at  = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime)

    # Relationships
    student = relationship("Student", back_populates="school_enrollments")
    school  = relationship("TechSchool", back_populates="enrollments")
    course  = relationship("SchoolCourse", back_populates="enrollments")
    test_attempt = relationship("TestAttempt", back_populates="enrollments")