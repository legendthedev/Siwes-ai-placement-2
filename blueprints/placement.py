"""blueprints/placement.py — results page + full evaluation metrics page"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from database import SessionLocal
from models import (Placement, Student, Company, JobDescription,
                    PlacementBatch, ShapExplanation, SimilarityScore, CV)

placement_bp = Blueprint("placement", __name__)


# ── Placement results list ────────────────────────────────────────────────────
@placement_bp.route("/results")
@login_required
def results():
    db = SessionLocal()
    try:
        batch_id = request.args.get("batch_id", type=int)
        batches  = db.query(PlacementBatch).order_by(PlacementBatch.run_at.desc()).all()
        if not batch_id and batches:
            batch_id = batches[0].id

        rows = []
        if batch_id:
            rows = (db.query(Placement, Student, Company, JobDescription)
                    .join(Student, Student.id == Placement.student_id)
                    .join(Company, Company.id == Placement.company_id)
                    .join(JobDescription, JobDescription.id == Placement.job_description_id)
                    .filter(Placement.batch_id == batch_id)
                    .order_by(Placement.match_score.desc())
                    .all())

        return render_template("placement/results.html",
                               rows=rows, batches=batches,
                               selected_batch=batch_id)
    finally:
        db.close()


# ── Full evaluation metrics page ──────────────────────────────────────────────
@placement_bp.route("/evaluation")
@login_required
def evaluation():
    """
    Computes the full suite of evaluation metrics for a placement batch
    and renders them as an interactive HTML page.
    """
    import numpy as np
    from collections import defaultdict, Counter

    db = SessionLocal()
    try:
        batch_id = request.args.get("batch_id", type=int)
        batches  = db.query(PlacementBatch).order_by(PlacementBatch.run_at.desc()).all()
        if not batch_id and batches:
            batch_id = batches[0].id

        if not batch_id:
            return render_template("placement/evaluation.html",
                                   batches=batches, selected_batch=None, metrics=None)

        batch      = db.query(PlacementBatch).filter_by(id=batch_id).first()
        placements = (db.query(Placement, Student, Company, JobDescription)
                      .join(Student, Student.id == Placement.student_id)
                      .join(Company, Company.id == Placement.company_id)
                      .join(JobDescription, JobDescription.id == Placement.job_description_id)
                      .filter(Placement.batch_id == batch_id)
                      .all())

        score_rows = (db.query(SimilarityScore)
                      .filter_by(batch_id=batch_id).all())
        all_jds    = db.query(JobDescription).all()

        if not placements:
            return render_template("placement/evaluation.html",
                                   batches=batches, selected_batch=batch_id,
                                   metrics=None, batch=batch)

        # ── Raw data ───────────────────────────────────────────────────────
        scores     = [p.match_score for p, *_ in placements]
        arr        = np.array(scores)
        n_matched  = len(placements)
        n_total    = batch.total_students or n_matched

        # ── 1. Coverage ────────────────────────────────────────────────────
        match_rate = n_matched / n_total if n_total else 0

        # ── 2. Score quality ───────────────────────────────────────────────
        strong   = sum(1 for s in scores if s >= 0.75)
        moderate = sum(1 for s in scores if 0.50 <= s < 0.75)
        weak     = sum(1 for s in scores if s < 0.50)
        pct_vals = [10,25,50,75,90]
        percentiles = {p: round(float(np.percentile(arr, p)), 4) for p in pct_vals}

        # score histogram (10 buckets 0→1)
        hist, edges = np.histogram(arr, bins=10, range=(0,1))
        score_hist  = [{"label": f"{edges[i]:.1f}–{edges[i+1]:.1f}",
                         "count": int(hist[i])} for i in range(len(hist))]

        # ── 3. Stability (blocking pairs) ──────────────────────────────────
        score_lkp = {(sr.student_id, sr.job_description_id): sr.score
                     for sr in score_rows}

        # Rebuild student_prefs from similarity_scores
        from collections import defaultdict
        s_scores_map = defaultdict(list)
        for sr in score_rows:
            if sr.score > 0:
                s_scores_map[sr.student_id].append((sr.score, sr.job_description_id))
        student_prefs = {sid: [jid for _,jid in sorted(v, reverse=True)]
                         for sid, v in s_scores_map.items()}

        # Blocking pair count
        placed_jd  = {p.student_id: p.job_description_id for p, *_ in placements}
        jd_holders = defaultdict(list)
        for p, *_ in placements:
            jd_holders[p.job_description_id].append((p.match_score, p.student_id))
        for jd_id in jd_holders:
            jd_holders[jd_id].sort()

        blocking = 0
        for p, *_ in placements:
            sid, curr_jd = p.student_id, p.job_description_id
            for preferred_jd in student_prefs.get(sid, []):
                if preferred_jd == curr_jd:
                    break
                new_score = score_lkp.get((sid, preferred_jd), 0.0)
                if not new_score:
                    continue
                holders = jd_holders[preferred_jd]
                if holders and new_score > holders[0][0]:
                    blocking += 1
                    break

        # Preference rank
        ranks = []
        for p, *_ in placements:
            pref = student_prefs.get(p.student_id, [])
            try:   ranks.append(pref.index(p.job_description_id) + 1)
            except ValueError: ranks.append(len(pref) + 1)
        mean_rank = float(np.mean(ranks)) if ranks else 0
        top1_rate = sum(1 for r in ranks if r == 1) / n_matched if n_matched else 0
        top3_rate = sum(1 for r in ranks if r <= 3) / n_matched if n_matched else 0

        rank_dist = Counter(ranks)
        rank_chart = [{"rank": r, "count": rank_dist.get(r, 0)} for r in range(1, 11)]

        # ── 4. Skill alignment (Precision / Recall / F1) ───────────────────
        def skill_metrics(student_skills, jd_skills):
            ss = set(student_skills)
            js = set(jd_skills)
            if not ss or not js:
                return 0.0, 0.0, 0.0
            tp = len(ss & js)
            p  = tp / len(ss)
            r  = tp / len(js)
            f1 = 2*p*r/(p+r) if (p+r) else 0.0
            return round(p,4), round(r,4), round(f1,4)

        alignment_rows = []
        for p, s, c, jd in placements:
            cv = db.query(CV).filter_by(student_id=s.id).first()
            s_skills = cv.get_skills() if cv else []
            j_skills = jd.get_required_skills()
            prec, rec, f1 = skill_metrics(s_skills, j_skills)
            alignment_rows.append({
                "student": s.name, "company": c.name, "role": jd.title,
                "precision": prec, "recall": rec, "f1": f1,
                "score": round(p.match_score, 4),
            })
        prec_arr = np.array([r["precision"] for r in alignment_rows])
        rec_arr  = np.array([r["recall"]    for r in alignment_rows])
        f1_arr   = np.array([r["f1"]        for r in alignment_rows])

        # ── 5. Fairness (Gini + dept coverage) ────────────────────────────
        def gini(vals):
            if not vals or all(v == 0 for v in vals):
                return 0.0
            a = np.sort(np.array(vals, dtype=float))
            n = len(a); idx = np.arange(1, n+1)
            return float((2*np.sum(idx*a) - (n+1)*np.sum(a)) / (n*np.sum(a)))

        gini_coeff = round(gini(scores), 4)
        cv_val     = round(float(arr.std() / arr.mean()), 4) if arr.mean() else 0

        dept_total   = defaultdict(int)
        dept_matched = defaultdict(int)
        all_students = db.query(Student).all()
        for stu in all_students:
            dept_total[stu.department] += 1
        for p, s, *_ in placements:
            dept_matched[s.department] += 1
        dept_rows = []
        for dept, total in sorted(dept_total.items()):
            m = dept_matched.get(dept, 0)
            dept_rows.append({
                "dept": dept, "matched": m, "total": total,
                "rate": round(m/total, 4) if total else 0,
            })

        state_total   = defaultdict(int)
        state_matched = defaultdict(int)
        for stu in all_students:
            state_total[stu.state] += 1
        for p, s, *_ in placements:
            state_matched[s.state] += 1
        state_rows = [{"state": st, "matched": state_matched.get(st,0),
                       "total": state_total[st],
                       "rate": round(state_matched.get(st,0)/state_total[st],4)}
                      for st in sorted(state_total)]

        # ── 6. Quota utilisation ───────────────────────────────────────────
        placed_per_jd = Counter(p.job_description_id for p, *_ in placements)
        quota_rows = []
        for jd in all_jds:
            placed = placed_per_jd.get(jd.id, 0)
            q      = jd.quota or 1
            rem    = jd.remaining_quota if jd.remaining_quota is not None else q
            quota_rows.append({
                "title":     jd.title,
                "company":   jd.company.name if jd.company else "—",
                "quota":     q,
                "placed":    placed,
                "remaining": rem,
                "fill_pct":  round(placed/q*100, 1),
            })
        quota_rows.sort(key=lambda r: -r["fill_pct"])
        total_quota  = sum(j.quota for j in all_jds if j.quota)
        filled_quota = sum(placed_per_jd.values())
        overall_util = round(filled_quota / total_quota, 4) if total_quota else 0

        # ── 7. Ranking quality (NDCG / MAP / MRR / Hit@k) ─────────────────
        rr_vals  = []
        ap_vals  = []
        ndcg_1   = []
        ndcg_3   = []
        ndcg_5   = []
        ndcg_10  = []
        hit_1 = hit_3 = hit_5 = 0
        n_eval = 0

        all_jd_ids = [jd.id for jd in all_jds]

        for p, *_ in placements:
            sid   = p.student_id
            jd_id = p.job_description_id
            # Rank the JDs by score for this student
            s_jd_scores = [(score_lkp.get((sid, jid), 0.0), jid) for jid in all_jd_ids]
            s_jd_scores.sort(reverse=True)
            ranked = [jid for _, jid in s_jd_scores]
            if not ranked:
                continue
            n_eval += 1
            try:    rank = ranked.index(jd_id) + 1
            except: rank = len(ranked) + 1

            rr_vals.append(1.0 / rank)
            ap_vals.append(1.0 / rank)
            if rank == 1: hit_1 += 1
            if rank <= 3: hit_3 += 1
            if rank <= 5: hit_5 += 1
            # NDCG
            idcg = 1.0 / np.log2(2)
            for k, lst in [(1, ndcg_1),(3, ndcg_3),(5, ndcg_5),(10, ndcg_10)]:
                top_k = ranked[:k]
                dcg   = sum((1.0/np.log2(i+2)) for i,jid in enumerate(top_k) if jid==jd_id)
                lst.append(dcg / idcg if idcg else 0.0)

        mrr  = round(float(np.mean(rr_vals)),  4) if rr_vals else 0.0
        mAP  = round(float(np.mean(ap_vals)),  4) if ap_vals else 0.0
        ndcg = {
            1:  round(float(np.mean(ndcg_1)),  4) if ndcg_1  else 0.0,
            3:  round(float(np.mean(ndcg_3)),  4) if ndcg_3  else 0.0,
            5:  round(float(np.mean(ndcg_5)),  4) if ndcg_5  else 0.0,
            10: round(float(np.mean(ndcg_10)), 4) if ndcg_10 else 0.0,
        }
        hit_rates = {
            1: round(hit_1/n_eval, 4) if n_eval else 0.0,
            3: round(hit_3/n_eval, 4) if n_eval else 0.0,
            5: round(hit_5/n_eval, 4) if n_eval else 0.0,
        }

        # ── Bundle everything ──────────────────────────────────────────────
        metrics = {
            # Coverage
            "n_matched": n_matched, "n_total": n_total,
            "match_rate": round(match_rate, 4),
            "unmatched": n_total - n_matched,
            # Quality
            "mean_score":   round(float(arr.mean()),   4),
            "median_score": round(float(np.median(arr)), 4),
            "std_score":    round(float(arr.std()),    4),
            "min_score":    round(float(arr.min()),    4),
            "max_score":    round(float(arr.max()),    4),
            "strong": strong, "moderate": moderate, "weak": weak,
            "percentiles": percentiles,
            "score_hist":  score_hist,
            # Stability
            "blocking_pairs": blocking,
            "is_stable": blocking == 0,
            "mean_rank": round(mean_rank, 2),
            "top1_rate": round(top1_rate, 4),
            "top3_rate": round(top3_rate, 4),
            "rank_chart": rank_chart,
            # Skill alignment
            "mean_precision": round(float(prec_arr.mean()), 4) if len(prec_arr) else 0,
            "mean_recall":    round(float(rec_arr.mean()),  4) if len(rec_arr)  else 0,
            "mean_f1":        round(float(f1_arr.mean()),   4) if len(f1_arr)   else 0,
            "alignment_rows": alignment_rows[:20],
            # Fairness
            "gini": gini_coeff,
            "cv":   cv_val,
            "dept_rows":  dept_rows,
            "state_rows": state_rows,
            # Quota
            "total_quota":  total_quota,
            "filled_quota": filled_quota,
            "overall_util": overall_util,
            "quota_rows":   quota_rows,
            # Ranking
            "mrr": mrr, "mAP": mAP,
            "ndcg": ndcg, "hit_rates": hit_rates,
        }

        return render_template("placement/evaluation.html",
                               batches=batches, selected_batch=batch_id,
                               batch=batch, metrics=metrics,
                               placements=placements)
    finally:
        db.close()


# ── CSV export ────────────────────────────────────────────────────────────────
@placement_bp.route("/evaluation/export/<int:batch_id>")
@login_required
def export_csv(batch_id):
    import csv, io
    from flask import Response
    db = SessionLocal()
    try:
        placements = (db.query(Placement, Student, Company, JobDescription)
                      .join(Student, Student.id == Placement.student_id)
                      .join(Company, Company.id == Placement.company_id)
                      .join(JobDescription, JobDescription.id == Placement.job_description_id)
                      .filter(Placement.batch_id == batch_id)
                      .order_by(Placement.match_score.desc()).all())

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Student","University","Department","State",
                         "Company","State","Role","Match Score","Status","Date"])
        for p, s, c, jd in placements:
            writer.writerow([s.name, s.university, s.department, s.state,
                             c.name, c.state, jd.title,
                             round(p.match_score, 4), p.status,
                             p.created_at.strftime("%Y-%m-%d")])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition":
                     f"attachment; filename=siwes_batch_{batch_id}.csv"}
        )
    finally:
        db.close()
