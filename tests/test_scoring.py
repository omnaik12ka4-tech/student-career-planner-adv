"""
Unit tests for the weighted, level-aware scoring engine in app/scoring.py.
These don't touch Flask or the database at all - just plain function calls,
so they double as a spec for how the matching algorithm is supposed to behave.
"""
from app.scoring import score_one_career, next_skills, category_coverage, readiness


def _req(skill_id, name, level):
    return {"skill_id": skill_id, "name": name, "required_level": level}


CAREER = {"id": 1, "name": "Data Analyst", "slug": "data-analyst", "icon": "📊",
          "hue": 215, "description": "d", "project": "p"}
REQS = [_req(1, "Excel", 2), _req(2, "SQL", 2), _req(3, "Python", 2),
        _req(4, "Statistics", 3), _req(5, "Pandas", 2), _req(6, "Power BI", 2)]


def test_full_match_scores_100():
    levels = {1: 2, 2: 2, 3: 2, 4: 3, 5: 2, 6: 2}
    result = score_one_career(CAREER, REQS, levels)
    assert result["score"] == 100
    assert len(result["matched"]) == 6
    assert not result["missing"] and not result["partial"]


def test_no_skills_scores_zero():
    result = score_one_career(CAREER, REQS, {})
    assert result["score"] == 0
    assert len(result["missing"]) == 6


def test_partial_credit_for_under_levelled_skill():
    # Beginner (1) in a skill that needs Advanced (3) -> 1/3 credit, not 0
    levels = {4: 1}
    result = score_one_career(CAREER, REQS, levels)
    entry = next(e for e in result["partial"] if e["name"] == "Statistics")
    assert abs(entry["contribution"] - (1 / 3)) < 1e-9
    assert result["score"] == round((1 / 3) / 6 * 100)


def test_exceeding_required_level_gives_no_bonus():
    # Advanced (3) where only Intermediate (2) is needed -> capped at full credit (1), not more
    levels = {1: 3}
    result = score_one_career(CAREER, REQS, levels)
    entry = next(e for e in result["matched"] if e["name"] == "Excel")
    assert entry["contribution"] == 1.0


def test_matched_vs_partial_vs_missing_buckets():
    levels = {1: 2, 4: 1}   # Excel fully met, Statistics partially, everything else missing
    result = score_one_career(CAREER, REQS, levels)
    names = lambda bucket: {e["name"] for e in bucket}
    assert names(result["matched"]) == {"Excel"}
    assert names(result["partial"]) == {"Statistics"}
    assert names(result["missing"]) == {"SQL", "Python", "Pandas", "Power BI"}


def test_readiness_labels_match_score_bands():
    assert readiness(0)[1] == "Just starting"
    assert readiness(30)[1] == "Building basics"
    assert readiness(60)[1] == "Getting there"
    assert readiness(80)[1] == "Almost there"
    assert readiness(100)[1] == "Ready to apply"


def test_next_skills_prefers_highest_scoring_career():
    close_career = dict(CAREER, id=2, name="Close One")
    far_career = dict(CAREER, id=3, name="Far One")
    close_result = score_one_career(close_career, REQS, {1: 2, 2: 2, 3: 2, 5: 2})   # 4/6 -> high score
    far_result = score_one_career(far_career, REQS, {})                             # 0/6
    ranked = next_skills([close_result, far_result], limit=5)
    # "Statistics" and "Power BI" are missing from the close career - they should
    # rank ahead of skills only missing from the far, low-scoring career.
    top_names = {r["skill"] for r in ranked[:2]}
    assert top_names == {"Statistics", "Power BI"}


def test_category_coverage_counts_any_started_skill():
    categories = [{"name": "Data & AI", "icon": "📊",
                  "skills": [{"id": 1}, {"id": 2}, {"id": 3}]}]
    levels = {1: 1, 2: 0}  # skill 1 started (even at Beginner), skill 2 not, skill 3 absent
    result = category_coverage(categories, levels)
    assert result[0]["have"] == 1
    assert result[0]["total"] == 3
    assert result[0]["pct"] == 33
