"""
pipeline/scorer.py  —  Cosine similarity scoring with hard-constraint filters
Computes a score matrix: students × job_descriptions
Filters out invalid pairs before scoring (location mismatch, dept mismatch).
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from dataclasses import dataclass


@dataclass
class ScoreEntry:
    student_id:         int
    job_description_id: int
    score:              float
    location_match:     bool
    dept_match:         bool


class SimilarityScorer:
    """
    Computes cosine similarity between student skill vectors
    and job requirement vectors, with optional hard-constraint filtering.
    """

    def __init__(self, location_strict: bool = True, dept_strict: bool = False):
        """
        location_strict: if True, pairs with location mismatch score 0.0
        dept_strict:     if True, pairs with department mismatch score 0.0
        """
        self.location_strict = location_strict
        self.dept_strict     = dept_strict

    def compute_scores(
        self,
        students:    list[dict],   # [{id, vector, location, department}, ...]
        jd_list:     list[dict],   # [{id, vector, location, department}, ...]
    ) -> list[ScoreEntry]:
        """
        Compute all student–JD cosine similarity scores.
        Returns a list of ScoreEntry, one per valid (student, JD) pair.
        """
        if not students or not jd_list:
            return []

        # Stack vectors for batch cosine similarity
        student_vecs = np.vstack([s["vector"] for s in students])   # (N_s, D)
        jd_vecs      = np.vstack([j["vector"] for j in jd_list])    # (N_j, D)

        # Cosine similarity matrix: shape (N_s, N_j)
        sim_matrix = cosine_similarity(student_vecs, jd_vecs)

        results = []
        for i, student in enumerate(students):
            for j, jd in enumerate(jd_list):
                loc_match  = self._location_match(student["location"], jd["location"])
                dept_match = self._dept_match(student["department"], jd["department"])

                raw_score = float(sim_matrix[i, j])

                # Apply hard constraint penalties
                if self.location_strict and not loc_match:
                    adjusted_score = 0.0
                elif self.dept_strict and not dept_match:
                    adjusted_score = 0.0
                else:
                    adjusted_score = raw_score

                results.append(ScoreEntry(
                    student_id=student["id"],
                    job_description_id=jd["id"],
                    score=adjusted_score,
                    location_match=loc_match,
                    dept_match=dept_match,
                ))

        return results

    def build_preference_lists(
        self,
        scores:  list[ScoreEntry],
        top_k:   int = 10,
    ) -> tuple[dict, dict]:
        """
        Build ranked preference lists for Gale-Shapley from score entries.

        Returns:
          student_prefs  — {student_id: [jd_id1, jd_id2, ...]} (highest score first)
          company_prefs  — {jd_id: [student_id1, student_id2, ...]} (highest score first)
        """
        # Group by student → sort JDs by descending score
        from collections import defaultdict
        student_scores: dict[int, list[tuple[float, int]]] = defaultdict(list)
        jd_scores:      dict[int, list[tuple[float, int]]] = defaultdict(list)

        for entry in scores:
            if entry.score > 0:   # skip hard-constraint-filtered pairs
                student_scores[entry.student_id].append((entry.score, entry.job_description_id))
                jd_scores[entry.job_description_id].append((entry.score, entry.student_id))

        student_prefs = {
            sid: [jd_id for _, jd_id in sorted(pairs, reverse=True)[:top_k]]
            for sid, pairs in student_scores.items()
        }
        company_prefs = {
            jid: [sid for _, sid in sorted(pairs, reverse=True)]
            for jid, pairs in jd_scores.items()
        }

        return student_prefs, company_prefs

    # ── Hard constraints ──────────────────────

    @staticmethod
    def _location_match(student_loc: str, jd_loc: str) -> bool:
        """
        Soft location matching: if either is in the same SW-Nigeria cluster
        the match is accepted. Simple substring check.
        """
        s = (student_loc or "").lower()
        j = (jd_loc or "").lower()

        # Same city/state → always fine
        if s == j or s in j or j in s:
            return True

        # Both within Lagos → fine
        LAGOS_AREAS = {"ikeja", "victoria island", "lekki", "yaba", "surulere",
                       "ikorodu", "apapa", "oshodi", "mushin", "lagos"}
        if any(a in s for a in LAGOS_AREAS) and any(a in j for a in LAGOS_AREAS):
            return True

        return False

    @staticmethod
    def _dept_match(student_dept: str, jd_dept: str) -> bool:
        """Accept if JD targets any CS-family department or is unspecified."""
        if not jd_dept:
            return True
        s = (student_dept or "").lower()
        j = (jd_dept or "").lower()
        return (s == j or s in j or j in s or not j)
