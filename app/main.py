"""Student-facing pages: landing, dashboard, skills, careers, career detail, profile."""
from datetime import datetime

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from . import models, scoring
from .auth import login_required

bp = Blueprint("main", __name__)


def _requirements_by_career(careers):
    return {c["id"]: models.get_career_requirements(c["id"]) for c in careers}


def _build_recommendations(user_id):
    careers = models.get_all_careers()
    reqs = _requirements_by_career(careers)
    levels = models.get_user_levels(user_id)
    return scoring.recommendations(careers, reqs, levels), levels


def greeting():
    hour = datetime.now().hour
    return "Good morning" if hour < 12 else ("Good afternoon" if hour < 17 else "Good evening")


@bp.route("/")
def index():
    if g.user:
        return redirect(url_for("main.dashboard"))
    career_count = models.get_db().execute("SELECT COUNT(*) c FROM careers").fetchone()["c"]
    skill_count = models.get_db().execute("SELECT COUNT(*) c FROM skills").fetchone()["c"]
    return render_template("index.html", career_count=career_count, skill_count=skill_count)


@bp.route("/dashboard")
@login_required
def dashboard():
    recs, levels = _build_recommendations(g.user["id"])
    next_up = scoring.next_skills(recs)
    categories = models.get_categories_with_skills()
    has_skills = any(levels.values())
    my_skills = []
    for cat in categories:
        for s in cat["skills"]:
            lvl = levels.get(s["id"], 0)
            if lvl > 0:
                my_skills.append({"name": s["name"], "level": lvl})
    my_skills.sort(key=lambda s: s["name"])
    return render_template(
        "dashboard.html",
        recommendations=recs, top=recs[0],
        strong_count=sum(1 for r in recs if r["score"] >= 50),
        next_up=next_up,
        summary=scoring.plain_summary(recs[0], next_up, has_skills),
        coverage=scoring.category_coverage(categories, levels),
        radar=[{"label": r["name"][:14], "score": r["score"]} for r in sorted(recs, key=lambda r: r["name"])],
        has_skills=has_skills, skill_count=sum(1 for v in levels.values() if v > 0),
        my_skills=my_skills,
        greeting=greeting(),
    )


@bp.route("/skills", methods=["GET", "POST"])
@login_required
def skills():
    if request.method == "POST":
        levels = {}
        for key, value in request.form.items():
            if key.startswith("level_") and value:
                try:
                    skill_id, level = int(key[6:]), int(value)
                except ValueError:
                    continue
                if 0 <= level <= 3:
                    levels[skill_id] = level
        models.set_user_levels(g.user["id"], levels)
        flash(f"Skills updated - {sum(1 for v in levels.values() if v > 0)} saved.", "success")
        return redirect(url_for("main.dashboard"))

    categories = models.get_categories_with_skills()
    user_levels = models.get_user_levels(g.user["id"])
    careers = models.get_all_careers()
    careers_json = [
        {"name": c["name"], "icon": c["icon"],
         "skills": [{"id": r["skill_id"], "level": r["required_level"]} for r in models.get_career_requirements(c["id"])]}
        for c in careers
    ]
    return render_template("skills.html", categories=categories, user_levels=user_levels, careers_json=careers_json)


@bp.route("/careers")
@login_required
def careers():
    recs, _ = _build_recommendations(g.user["id"])
    return render_template("careers.html", recommendations=recs)


@bp.route("/career/<slug>")
@login_required
def career_detail(slug):
    career = models.get_career_by_slug(slug)
    if career is None:
        abort(404)
    recs, levels = _build_recommendations(g.user["id"])
    scored = next(r for r in recs if r["slug"] == slug)

    steps = []
    for e in sorted(scored["matched"], key=lambda x: x["name"]):
        steps.append({"skill": e["name"], "state": "done", "have": e["have_level"], "need": e["required_level"]})
    remaining = sorted(scored["partial"] + scored["missing"], key=lambda x: (-x["contribution"], x["name"]))
    for i, e in enumerate(remaining):
        steps.append({"skill": e["name"], "state": "current" if i == 0 else "todo",
                      "have": e["have_level"], "need": e["required_level"]})

    return render_template("career_detail.html", career=scored, steps=steps,
                           related=scoring.related_careers(recs, career["name"]))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        course = request.form.get("course", "").strip()[:60]
        year = request.form.get("year", "").strip()
        if not name:
            flash("Name cannot be empty.", "error")
            return redirect(url_for("main.profile"))
        if year not in ("FY", "SY", "TY"):
            year = "TY"
        db = models.get_db()
        db.execute("UPDATE users SET name=?, course=?, year=? WHERE id=?", (name[:60], course, year, g.user["id"]))
        db.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("main.profile"))

    recs, levels = _build_recommendations(g.user["id"])
    return render_template("profile.html", skill_count=sum(1 for v in levels.values() if v > 0), top=recs[0])
