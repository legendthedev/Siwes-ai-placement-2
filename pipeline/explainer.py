"""
pipeline/explainer.py  —  SHAP-based explainability for match scores
Explains why a student was matched to a specific company by computing
the marginal contribution of each skill to the cosine similarity score.
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from dataclasses import dataclass


@dataclass
class SkillContribution:
    skill:          str
    shap_value:     float    # contribution to match score
    in_student_cv:  bool
    in_job_req:     bool


class PlacementExplainer:
    """
    Approximates SHAP values for the cosine similarity scoring model.

    Method: leave-one-out (LOO) approximation.
    For each skill dimension, compute how much the score drops when
    that skill is zeroed out in the student's vector.
    This is a practical surrogate to full SHAP for embedding-space scores.
    """

    def explain(
        self,
        student_skills: list[str],
        jd_skills:      list[str],
        student_vector: np.ndarray,
        jd_vector:      np.ndarray,
        encoder,                    # SBERTEncoder instance
        top_k: int = 10,
    ) -> list[SkillContribution]:
        """
        Compute per-skill SHAP contributions.

        Returns top_k skills ranked by absolute contribution.
        """
        all_skills = sorted(set(student_skills) | set(jd_skills))
        if not all_skills:
            return []

        baseline_score = self._cosine(student_vector, jd_vector)
        contributions  = []

        for skill in all_skills:
            # Build modified skill list with this skill removed from student
            modified_skills = [s for s in student_skills if s != skill]
            modified_vec    = encoder.encode_skills(modified_skills)

            modified_score  = self._cosine(modified_vec, jd_vector)
            shap_val        = baseline_score - modified_score   # marginal drop

            contributions.append(SkillContribution(
                skill=skill,
                shap_value=round(float(shap_val), 5),
                in_student_cv=(skill in student_skills),
                in_job_req=(skill in jd_skills),
            ))

        # Sort by absolute contribution descending, return top_k
        contributions.sort(key=lambda c: abs(c.shap_value), reverse=True)
        return contributions[:top_k]

    @staticmethod
    def _cosine(a: np.ndarray, b: np.ndarray) -> float:
        if a is None or b is None:
            return 0.0
        return float(cosine_similarity(a.reshape(1, -1), b.reshape(1, -1))[0, 0])

    def generate_feedback(self, contributions: list[SkillContribution], match_score: float) -> dict:
        """
        Generate human-readable feedback for a student.
        Returns dict with strengths, gaps, and match_summary.
        """
        strengths = [c for c in contributions if c.in_student_cv and c.in_job_req and c.shap_value > 0]
        gaps      = [c for c in contributions if c.in_job_req and not c.in_student_cv]
        extras    = [c for c in contributions if c.in_student_cv and not c.in_job_req]

        level = "Strong" if match_score >= 0.75 else "Moderate" if match_score >= 0.50 else "Weak"

        return {
            "match_score":    round(match_score, 3),
            "match_level":    level,
            "strengths":      [c.skill for c in strengths[:5]],
            "skill_gaps":     [c.skill for c in gaps[:5]],
            "extra_skills":   [c.skill for c in extras[:3]],
            "summary": (
                f"Your profile is a {level.lower()} match ({match_score:.0%}). "
                f"Your top matching skills are: {', '.join(c.skill for c in strengths[:3]) or 'none identified'}. "
                f"To improve your score, consider developing: {', '.join(c.skill for c in gaps[:3]) or 'no critical gaps found'}."
            ),
        }
