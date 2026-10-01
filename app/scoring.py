"""
Weighted, level-aware career matching.

The old version treated a skill as either "have it" or "don't" - a
checkbox. This version tracks a LEVEL for every skill the student has
(1=Beginner, 2=Intermediate, 3=Advanced) and every skill a career
requires, and gives PARTIAL credit when a student is under-levelled:

    contribution of one required skill
        = min(student_level, required_level) / required_level

so a Beginner (1) in a skill that needs Advanced (3) contributes 1/3,
not 0 - closer than nothing, but clearly not there yet. A student who
exceeds the requirement still only contributes 1 (no bonus for
over-qualification, since the career doesn't need more than it asks for).

    score % = sum(contribution for every required skill) / number of required skills * 100

This is a small but real improvement over boolean matching: two students
with the same three "missing" skills are told apart by how close they
actually are on each one.
"""
from urllib.parse import quote_plus

LEVEL_NAMES = {0: "Not started", 1: "Beginner", 2: "Intermediate", 3: "Advanced"}

LEVELS = [
    (0, "Just starting", "You have less than 25% of the depth this career needs."),
    (1, "Building basics", "You have 25-49% of the depth this career needs."),
    (2, "Getting there", "You have 50-74% of the depth this career needs."),
    (3, "Almost there", "You have 75-99% of the depth this career needs."),
    (4, "Ready to apply", "You meet every skill at the level this career needs."),
]


def readiness(score):
    if score >= 100:
        return LEVELS[4]
    if score >= 75:
        return LEVELS[3]
    if score >= 50:
        return LEVELS[2]
    if score >= 25:
        return LEVELS[1]
    return LEVELS[0]


def score_one_career(career_row, requirements, user_levels):
    """
    requirements: rows from get_career_requirements() - skill_id, required_level, name, ...
    user_levels: {skill_id: level} for the student
    Returns a dict with the score plus matched / partial / missing skill breakdowns.
    """
    total = len(requirements)
    earned = 0.0
    matched, partial, missing = [], [], []

    for req in requirements:
        have = user_levels.get(req["skill_id"], 0)
        need = req["required_level"]
        contribution = min(have, need) / need if need else 1
        earned += contribution
        entry = {"skill_id": req["skill_id"], "name": req["name"], "required_level": need,
                 "have_level": have, "contribution": contribution}
        if have >= need:
            matched.append(entry)
        elif have > 0:
            partial.append(entry)
        else:
            missing.append(entry)

    score = round(earned / total * 100) if total else 0
    level_index, level, level_tip = readiness(score)
    return {
        "id": career_row["id"], "name": career_row["name"], "slug": career_row["slug"],
        "icon": career_row["icon"], "hue": career_row["hue"], "description": career_row["description"],
        "project": career_row["project"], "total": total,
        "matched": matched, "partial": partial, "missing": missing,
        "score": score, "level": level, "level_index": level_index, "level_tip": level_tip,
    }


def recommendations(careers, requirements_by_career, user_levels):
    """careers: rows from get_all_careers(). requirements_by_career: {career_id: requirements}."""
    results = [score_one_career(c, requirements_by_career.get(c["id"], []), user_levels) for c in careers]
    return sorted(results, key=lambda r: (-r["score"], r["name"]))


def next_skills(recs, limit=3):
    """
    'Learn next' - look at the careers the student is closest to, and rank
    their still-incomplete skills by how much reaching the required level
    would help. A skill already started (partial) ranks ahead of one not
    started at all, since less work is needed to close that particular gap.
    """
    board = {}
    for r in recs:
        for entry in r["partial"] + r["missing"]:
            key = entry["skill_id"]
            item = board.setdefault(key, {
                "skill_id": key, "skill": entry["name"], "best_career_score": r["score"],
                "have_level": entry["have_level"], "target_level": entry["required_level"],
                "careers": [],
            })
            item["best_career_score"] = max(item["best_career_score"], r["score"])
            item["have_level"] = max(item["have_level"], entry["have_level"])
            item["target_level"] = max(item["target_level"], entry["required_level"])
            item["careers"].append(r["name"])
    ranked = sorted(board.values(),
                    key=lambda i: (-i["best_career_score"], -i["have_level"], -len(i["careers"]), i["skill"]))
    return ranked[:limit]


def plain_summary(top, next_up, has_skills):
    if not has_skills:
        return "Add a few skills and I'll tell you which career fits you best."
    if top["score"] >= 100:
        return f"🎉 You meet every requirement for {top['name']}. Build the starter project and start applying!"
    if next_up:
        pick = next_up[0]
        target = LEVEL_NAMES[pick["target_level"]]
        lead = f"You're close to {top['name']}" if top["score"] >= 50 else f"{top['name']} is your best match so far"
        return f"{lead}. Reach {target} in {pick['skill']} next."
    return f"{top['name']} is your best match so far."


def category_coverage(categories, user_levels):
    """How many skills the student has STARTED (level >= 1) in each category."""
    out = []
    for cat in categories:
        members = cat["skills"]
        have = [s for s in members if user_levels.get(s["id"], 0) > 0]
        total = len(members) or 1
        out.append({"name": cat["name"], "icon": cat["icon"], "have": len(have), "total": len(members),
                    "pct": round(len(have) / total * 100)})
    return out


def related_careers(all_scored, name, limit=3):
    mine = next(r for r in all_scored if r["name"] == name)
    mine_skills = {e["skill_id"] for e in mine["matched"] + mine["partial"] + mine["missing"]}
    out = []
    for other in all_scored:
        if other["name"] == name:
            continue
        other_skills = {e["skill_id"] for e in other["matched"] + other["partial"] + other["missing"]}
        shared_ids = mine_skills & other_skills
        if shared_ids:
            names = sorted(e["name"] for e in (other["matched"] + other["partial"] + other["missing"])
                          if e["skill_id"] in shared_ids)
            out.append({"name": other["name"], "slug": other["slug"], "icon": other["icon"],
                        "hue": other["hue"], "shared": names})
    out.sort(key=lambda o: (-len(o["shared"]), o["name"]))
    return out[:limit]


def learn_url(skill):
    return "https://www.youtube.com/results?search_query=" + quote_plus(f"{skill} tutorial for beginners")
