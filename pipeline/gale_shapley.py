"""
pipeline/gale_shapley.py  —  Gale-Shapley Deferred Acceptance Algorithm
Produces a stable matching between students (proposers) and companies (reviewers).
Supports capacity quotas (each JD slot can accept N students).
"""

from dataclasses import dataclass, field
from collections import defaultdict
from typing import Optional


@dataclass
class MatchResult:
    student_id:         int
    job_description_id: int
    company_id:         int
    match_score:        float
    round_matched:      int


@dataclass
class UnmatchedStudent:
    student_id: int
    reason:     str   # "no_eligible_jd" | "rejected_all_rounds"


@dataclass
class GaleShapleyOutput:
    matched:   list[MatchResult]
    unmatched: list[UnmatchedStudent]
    rounds:    int
    stable:    bool = True


class GaleShapleyMatcher:
    """
    Student-proposing Gale-Shapley with capacity constraints.

    Parameters
    ----------
    student_prefs  : {student_id: [jd_id, ...]}  ranked best-first
    company_prefs  : {jd_id: [student_id, ...]}  ranked best-first
    jd_quotas      : {jd_id: int}                max students per JD slot
    jd_company_map : {jd_id: company_id}         for output enrichment
    score_lookup   : {(student_id, jd_id): float} raw cosine scores
    """

    def __init__(
        self,
        student_prefs:  dict[int, list[int]],
        company_prefs:  dict[int, list[int]],
        jd_quotas:      dict[int, int],
        jd_company_map: dict[int, int],
        score_lookup:   dict[tuple[int, int], float],
    ):
        self.student_prefs  = {k: list(v) for k, v in student_prefs.items()}
        self.company_prefs  = company_prefs
        self.jd_quotas      = jd_quotas
        self.jd_company_map = jd_company_map
        self.score_lookup   = score_lookup

        # Pre-compute company ranking maps for O(1) preference lookup
        # company_rank[jd_id][student_id] = rank (lower = more preferred)
        self.company_rank: dict[int, dict[int, int]] = {}
        for jd_id, ranked_students in company_prefs.items():
            self.company_rank[jd_id] = {
                sid: rank for rank, sid in enumerate(ranked_students)
            }

    def run(self) -> GaleShapleyOutput:
        """
        Execute the student-proposing Gale-Shapley algorithm.

        Students propose to their most preferred available JD.
        JDs tentatively accept up to `quota` students, rejecting the
        worst-ranked if over capacity.
        """
        all_students = list(self.student_prefs.keys())

        # Track next proposal index per student
        next_proposal: dict[int, int] = {sid: 0 for sid in all_students}

        # Track tentative holds per JD: {jd_id: [student_id, ...]}
        jd_holds: dict[int, list[int]] = defaultdict(list)

        # Track which JD a student is currently held by (None = free)
        student_held_by: dict[int, Optional[int]] = {sid: None for sid in all_students}

        # Free students = those not currently held
        free_students = set(all_students)

        rounds = 0
        max_rounds = len(all_students) * (max(len(v) for v in self.student_prefs.values()) + 1)

        while free_students and rounds < max_rounds:
            rounds += 1
            # Pick any free student who still has proposals left
            proposers = [
                s for s in free_students
                if next_proposal[s] < len(self.student_prefs[s])
            ]
            if not proposers:
                break

            for student_id in list(proposers):
                pref_list = self.student_prefs[student_id]
                if next_proposal[student_id] >= len(pref_list):
                    continue

                # Propose to next preferred JD
                target_jd = pref_list[next_proposal[student_id]]
                next_proposal[student_id] += 1

                quota = self.jd_quotas.get(target_jd, 1)

                if target_jd not in self.company_rank:
                    # Company has no preference for this student — skip
                    continue

                if student_id not in self.company_rank[target_jd]:
                    # JD doesn't rank this student at all — skip
                    continue

                current_holds = jd_holds[target_jd]

                if len(current_holds) < quota:
                    # JD has room — tentatively accept
                    current_holds.append(student_id)
                    student_held_by[student_id] = target_jd
                    free_students.discard(student_id)

                else:
                    # JD is full; compare worst current hold vs this student
                    quota = self.jd_quotas.get(target_jd, 0) # Changed default to 0 for safety

                    # Defensive Guard: Skip JDs with no capacity to avoid max() crash
                    if quota <= 0:
                        continue
                    worst_held = self._worst_held(target_jd, current_holds)
                    rank_new   = self.company_rank[target_jd].get(student_id, 10**9)
                    rank_worst = self.company_rank[target_jd].get(worst_held, 10**9)

                    if rank_new < rank_worst:
                        # New student is better — swap
                        current_holds.remove(worst_held)
                        current_holds.append(student_id)

                        # Previously held student is now free again
                        student_held_by[worst_held] = None
                        free_students.add(worst_held)

                        student_held_by[student_id] = target_jd
                        free_students.discard(student_id)
                    # else: new student is rejected; stays free, tries next

        # ── Build output ──────────────────────
        matched:   list[MatchResult]        = []
        unmatched: list[UnmatchedStudent]   = []

        for student_id in all_students:
            jd_id = student_held_by.get(student_id)
            if jd_id:
                matched.append(MatchResult(
                    student_id=student_id,
                    job_description_id=jd_id,
                    company_id=self.jd_company_map.get(jd_id, -1),
                    match_score=self.score_lookup.get((student_id, jd_id), 0.0),
                    round_matched=rounds,
                ))
            else:
                proposals_made = next_proposal.get(student_id, 0)
                reason = "no_eligible_jd" if proposals_made == 0 else "rejected_all_rounds"
                unmatched.append(UnmatchedStudent(student_id=student_id, reason=reason))

        return GaleShapleyOutput(
            matched=matched,
            unmatched=unmatched,
            rounds=rounds,
        )

    def _worst_held(self, jd_id: int, held: list[int]) -> int:
        """Return the student ranked worst by this JD from the held list."""
        ranking = self.company_rank[jd_id]
        return max(held, key=lambda sid: ranking.get(sid, 10**9))
