"""
placement_engine.py — SIWES AI Placement Pipeline (v2 — fixes stale-student bug)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, pickle
from datetime import datetime
from database import SessionLocal
from models import (Student, CV, JobDescription, Company,
                    PlacementBatch, SimilarityScore, Placement, ShapExplanation)
from pipeline.encoder      import get_encoder
from pipeline.scorer       import SimilarityScorer
from pipeline.gale_shapley import GaleShapleyMatcher
from pipeline.explainer    import PlacementExplainer
from pipeline.evaluator    import PlacementEvaluator


class PlacementEngine:

    def __init__(self):
        self.encoder   = get_encoder()
        self.scorer    = SimilarityScorer(location_strict=False, dept_strict=False)
        self.explainer = PlacementExplainer()
        self.evaluator = PlacementEvaluator()

    def encode_all(self, progress_cb=None):
        """Encode every CV and JD that has no vector. Auto-called by run_placement."""
        db = SessionLocal()
        try:
            cvs = db.query(CV).filter(CV.skill_vector.is_(None)).all()
            for i, cv in enumerate(cvs):
                if cv.get_skills():
                    cv.set_vector(self.encoder.encode_skills(cv.get_skills()))
                if progress_cb: progress_cb(f"Encoding CV {i+1}/{len(cvs)}")
            db.commit()
            jds = db.query(JobDescription).filter(JobDescription.requirement_vector.is_(None)).all()
            for i, jd in enumerate(jds):
                if jd.get_required_skills():
                    jd.set_vector(self.encoder.encode_skills(jd.get_required_skills()))
                if progress_cb: progress_cb(f"Encoding JD {i+1}/{len(jds)}")
            db.commit()
            return len(cvs), len(jds)
        finally:
            db.close()

    def run_placement(self, batch_label: str, progress_cb=None):
        """Full pipeline. Always encodes first so new registrations are included."""
        # Always encode first — picks up every newly uploaded CV or added JD
        if progress_cb: progress_cb("Encoding new CVs and JDs …")
        self.encode_all(progress_cb)

        db = SessionLocal()
        try:
            batch = PlacementBatch(label=batch_label, status="running", run_at=datetime.utcnow())
            db.add(batch); db.flush()
            batch_id = batch.id

            # ALL students who have an encoded CV (including newly registered ones)
            if progress_cb: progress_cb("Loading student profiles …")
            students_raw = (db.query(Student, CV)
                            .join(CV, CV.student_id == Student.id)
                            .filter(CV.skill_vector.isnot(None)).all())
            students = [{"id": s.id, "vector": cv.get_vector(),
                         "location": (cv.extracted_location or s.location or "").lower(),
                         "state":    (s.state or "").lower(),
                         "department": (cv.extracted_department or s.department or "").lower(),
                         "skills": cv.get_skills()}
                        for s, cv in students_raw]

            # Only verified companies
            if progress_cb: progress_cb("Loading job descriptions …")
            jds_raw = (db.query(JobDescription, Company)
                       .join(Company, Company.id == JobDescription.company_id)
                       .filter(Company.verified == True,
                               JobDescription.requirement_vector.isnot(None)).all())
            jd_list = [{"id": jd.id, "vector": jd.get_vector(),
                        "location": (jd.location or "").lower(),
                        "state":    (c.state or "").lower(),
                        "department": (jd.target_department or "").lower(),
                        "quota": jd.quota, "company_id": jd.company_id,
                        "skills": jd.get_required_skills()}
                       for jd, c in jds_raw]

            if not students:
                batch.status = "failed"; db.commit()
                raise ValueError("No students with encoded CVs found. Students must upload a CV with skills.")
            if not jd_list:
                batch.status = "failed"; db.commit()
                raise ValueError("No verified company JDs found. Verify at least one company first.")

            # Cosine similarity
            if progress_cb: progress_cb(f"Scoring {len(students)} students × {len(jd_list)} JDs …")
            score_entries = self.scorer.compute_scores(students, jd_list)
            score_lookup  = {}
            for e in score_entries:
                if e.score > 0:
                    db.add(SimilarityScore(batch_id=batch_id, student_id=e.student_id,
                                           job_description_id=e.job_description_id,
                                           score=e.score, location_match=e.location_match,
                                           dept_match=e.dept_match))
                    score_lookup[(e.student_id, e.job_description_id)] = e.score
            db.flush()

            # Gale-Shapley
            if progress_cb: progress_cb("Running Gale-Shapley stable matching …")
            student_prefs, company_prefs = self.scorer.build_preference_lists(score_entries)
            gs_output = GaleShapleyMatcher(
                student_prefs=student_prefs, company_prefs=company_prefs,
                jd_quotas={j["id"]: j["quota"] for j in jd_list},
                jd_company_map={j["id"]: j["company_id"] for j in jd_list},
                score_lookup=score_lookup).run()

            # SHAP + persist
            if progress_cb: progress_cb("Computing SHAP explanations …")
            s_skill = {s["id"]: s["skills"] for s in students}
            s_vec   = {s["id"]: s["vector"] for s in students}
            s_dept  = {s["id"]: s["department"] for s in students}
            j_skill = {j["id"]: j["skills"] for j in jd_list}
            j_vec   = {j["id"]: j["vector"] for j in jd_list}
            jd_quotas = {j["id"]: j["quota"] for j in jd_list}

            for match in gs_output.matched:
                p = Placement(batch_id=batch_id, student_id=match.student_id,
                              company_id=match.company_id,
                              job_description_id=match.job_description_id,
                              match_score=match.match_score)
                db.add(p); db.flush()
                for c in self.explainer.explain(
                    s_skill.get(match.student_id, []), j_skill.get(match.job_description_id, []),
                    s_vec.get(match.student_id), j_vec.get(match.job_description_id), self.encoder):
                    db.add(ShapExplanation(placement_id=p.id, feature_name=c.skill,
                                           shap_value=c.shap_value, in_student_cv=c.in_student_cv,
                                           in_job_req=c.in_job_req))

            report = self.evaluator.evaluate(
                matched=[{"student_id": m.student_id, "jd_id": m.job_description_id,
                          "score": m.match_score} for m in gs_output.matched],
                unmatched=[{"student_id": u.student_id} for u in gs_output.unmatched],
                student_prefs=student_prefs, jd_quotas=jd_quotas,
                student_dept=s_dept, score_lookup=score_lookup)

            batch.placed_students = len(gs_output.matched)
            batch.total_students  = len(students)
            batch.status = "completed"
            db.commit()

            # Decrement remaining_quota on each JD that received students
            if progress_cb: progress_cb("Updating remaining quotas …")
            try:
                from seed_companies_extended import reduce_quotas_after_placement
                reduce_quotas_after_placement(batch_id)
            except Exception as qe:
                print(f"[QUOTA WARNING] Could not reduce quotas: {qe}")

            if progress_cb: progress_cb(f"Done — {batch.placed_students}/{batch.total_students} placed.")
            return batch_id, report

        except Exception:
            db.rollback(); raise
        finally:
            db.close()


if __name__ == "__main__":
    engine = PlacementEngine()
    bid, report = engine.run_placement("Manual run")
    print(f"Batch {bid}: {report.match_rate:.1%} match rate")
