"""
pipeline/evaluator.py  —  Placement quality evaluation metrics
Covers: coverage, stability, rank satisfaction, fairness (Gini), score distribution.
"""

import numpy as np
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class EvaluationReport:
    # Coverage
    total_students:     int
    matched_students:   int
    coverage_rate:      float

    # Score quality
    mean_match_score:   float
    median_match_score: float
    std_match_score:    float
    min_match_score:    float
    max_match_score:    float

    # Rank satisfaction
    mean_student_rank:  float
    top1_rate:          float
    top3_rate:          float

    # Quota utilisation
    total_quota:        int
    filled_quota:       int
    quota_fill_rate:    float

    # Stability
    blocking_pairs:     int
    is_stable:          bool

    # Fairness
    gini_coefficient:   float

    # Dept breakdown
    dept_coverage:      dict = field(default_factory=dict)

    # Score bands
    strong_matches:     int = 0
    moderate_matches:   int = 0
    weak_matches:       int = 0

    # Per-JD utilisation list (for charts)
    jd_utilisation:     list = field(default_factory=list)


class PlacementEvaluator:

    def evaluate(
        self,
        matched:        list,
        unmatched:      list,
        student_prefs:  dict,
        #company_prefs:      dict,
        jd_quotas:      dict,
        student_dept:   dict,
        score_lookup:   dict,
        #student_skill_map:  dict,  # Add this
        #jd_skill_map:       dict,  # Add this
        #placement_loc_map:  dict,  # Add this
        #placement_dept_map: dict,  # Add this
    ) -> EvaluationReport:

        total     = len(matched) + len(unmatched)
        n_matched = len(matched)

        scores = [m["score"] for m in matched] if matched else [0.0]

        # ── Score stats ───────────────────────────
        mean_s   = float(np.mean(scores))
        median_s = float(np.median(scores))
        std_s    = float(np.std(scores))
        min_s    = float(np.min(scores))
        max_s    = float(np.max(scores))

        # ── Rank satisfaction ─────────────────────
        ranks = []
        for m in matched:
            pref = student_prefs.get(m["student_id"], [])
            try:
                rank = pref.index(m["jd_id"]) + 1
            except ValueError:
                rank = len(pref) + 1
            ranks.append(rank)

        mean_rank = float(np.mean(ranks)) if ranks else 0.0
        top1_rate = sum(1 for r in ranks if r == 1) / n_matched if n_matched else 0.0
        top3_rate = sum(1 for r in ranks if r <= 3) / n_matched if n_matched else 0.0

        # ── Quota utilisation ─────────────────────
        total_quota = sum(jd_quotas.values())
        filled_per_jd = defaultdict(int)
        for m in matched:
            filled_per_jd[m["jd_id"]] += 1
        filled_quota    = sum(filled_per_jd.values())
        quota_fill_rate = filled_quota / total_quota if total_quota else 0.0

        jd_util = [
            {"jd_id": jd_id, "quota": q, "filled": filled_per_jd.get(jd_id, 0),
             "rate": round(filled_per_jd.get(jd_id, 0) / q, 3) if q else 0}
            for jd_id, q in jd_quotas.items()
        ]

        # ── Stability ─────────────────────────────
        blocking = self._count_blocking_pairs(matched, student_prefs, score_lookup)

        # ── Gini ──────────────────────────────────
        gini = self._gini(scores)

        # ── Dept coverage ─────────────────────────
        dept_total   = defaultdict(int)
        dept_matched_cnt = defaultdict(int)
        for m in matched:
            dept = student_dept.get(m["student_id"], "Unknown")
            dept_total[dept]       += 1
            dept_matched_cnt[dept] += 1
        for u in unmatched:
            dept = student_dept.get(u["student_id"], "Unknown")
            dept_total[dept] += 1

        dept_coverage = {
            d: {
                "matched": dept_matched_cnt[d],
                "total":   dept_total[d],
                "rate":    round(dept_matched_cnt[d] / dept_total[d], 3),
            }
            for d in dept_total
        }

        # ── Score bands ───────────────────────────
        strong   = sum(1 for s in scores if s >= 0.75)
        moderate = sum(1 for s in scores if 0.50 <= s < 0.75)
        weak     = sum(1 for s in scores if s < 0.50)

        return EvaluationReport(
            total_students=total,
            matched_students=n_matched,
            coverage_rate=round(n_matched / total, 4) if total else 0.0,
            mean_match_score=round(mean_s, 4),
            median_match_score=round(median_s, 4),
            std_match_score=round(std_s, 4),
            min_match_score=round(min_s, 4),
            max_match_score=round(max_s, 4),
            mean_student_rank=round(mean_rank, 2),
            top1_rate=round(top1_rate, 4),
            top3_rate=round(top3_rate, 4),
            total_quota=total_quota,
            filled_quota=filled_quota,
            quota_fill_rate=round(quota_fill_rate, 4),
            blocking_pairs=blocking,
            is_stable=(blocking == 0),
            gini_coefficient=round(gini, 4),
            dept_coverage=dept_coverage,
            strong_matches=strong,
            moderate_matches=moderate,
            weak_matches=weak,
            jd_utilisation=jd_util,
        )

    def _count_blocking_pairs(self, matched, student_prefs, score_matrix):
        student_jd = {m["student_id"]: m["jd_id"] for m in matched}
        jd_students = defaultdict(list)
        for m in matched:
            jd_students[m["jd_id"]].append((m["score"], m["student_id"]))
        for jd_id in jd_students:
            jd_students[jd_id].sort()

        blocking = 0
        for m in matched:
            s_id    = m["student_id"]
            curr_jd = m["jd_id"]
            prefs   = student_prefs.get(s_id, [])
            for preferred_jd in prefs:
                if preferred_jd == curr_jd:
                    break
                new_score = score_matrix.get((s_id, preferred_jd), 0.0)
                if not new_score:
                    continue
                holders = jd_students[preferred_jd]
                if holders:
                    worst_score, _ = holders[0]
                    if new_score > worst_score:
                        blocking += 1
                        break
        return blocking

    @staticmethod
    def _gini(values):
        if not values or all(v == 0 for v in values):
            return 0.0
        arr = np.sort(np.array(values, dtype=float))
        n   = len(arr)
        idx = np.arange(1, n + 1)
        return float(
            (2 * np.sum(idx * arr) - (n + 1) * np.sum(arr)) / (n * np.sum(arr))
        )
