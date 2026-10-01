"""
Admin panel: manage careers and skills without touching code, plus a look
at the student list. Only an account with is_admin=1 can reach any of
these routes (see admin_required in auth.py). The first account ever
registered becomes admin automatically (or set ADMIN_EMAIL in .env).
"""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from . import models, scoring
from .auth import admin_required
from .models import slugify

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("")
@admin_required
def dashboard():
    db = models.get_db()
    careers = models.get_all_careers()
    skills = models.get_all_skills()
    users = db.execute("SELECT * FROM users WHERE is_admin=0 ORDER BY id DESC").fetchall()

    reqs = {c["id"]: models.get_career_requirements(c["id"]) for c in careers}
    career_skill_counts = {cid: len(rows) for cid, rows in reqs.items()}
    student_rows = []
    for u in users:
        levels = models.get_user_levels(u["id"])
        recs = scoring.recommendations(careers, reqs, levels) if careers else []
        top = recs[0] if recs else None
        student_rows.append({
            "id": u["id"], "name": u["name"], "email": u["email"], "year": u["year"],
            "joined": (u["created_at"] or "")[:10], "last_login": (u["last_login"] or "")[:16] or "Never",
            "skill_count": sum(1 for v in levels.values() if v > 0),
            "top_name": top["name"] if top else "—", "top_score": top["score"] if top else 0,
        })

    stats = {
        "students": len(users), "careers": len(careers), "skills": len(skills),
        "avg_top": round(sum(s["top_score"] for s in student_rows) / len(student_rows)) if student_rows else 0,
    }
    return render_template("admin/dashboard.html", careers=careers, skills=skills,
                           students=student_rows, stats=stats, career_skill_counts=career_skill_counts)


# ---------------------------------------------------------------- careers --

@bp.route("/careers/new", methods=["GET", "POST"])
@admin_required
def career_new():
    return _career_form(career=None)


@bp.route("/careers/<int:career_id>/edit", methods=["GET", "POST"])
@admin_required
def career_edit(career_id):
    career = models.get_db().execute("SELECT * FROM careers WHERE id=?", (career_id,)).fetchone()
    if career is None:
        abort(404)
    return _career_form(career=career)


def _career_form(career):
    db = models.get_db()
    all_skills = models.get_all_skills()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        icon = request.form.get("icon", "💼").strip() or "💼"
        hue = request.form.get("hue", "220").strip()
        description = request.form.get("description", "").strip()
        project = request.form.get("project", "").strip()

        try:
            hue = max(0, min(360, int(hue)))
        except ValueError:
            hue = 220

        if not name or not description:
            flash("Name and description are required.", "error")
            return render_template("admin/career_form.html", career=career, all_skills=all_skills,
                                   selected={}, form=request.form)

        # required_N inputs: level (0-3) for every skill row in the form
        selected_levels = {}
        for s in all_skills:
            raw = request.form.get(f"required_{s['id']}", "0")
            try:
                lvl = int(raw)
            except ValueError:
                lvl = 0
            if 1 <= lvl <= 3:
                selected_levels[s["id"]] = lvl

        if not selected_levels:
            flash("Pick at least one required skill.", "error")
            return render_template("admin/career_form.html", career=career, all_skills=all_skills,
                                   selected=selected_levels, form=request.form)

        if career is None:
            slug = models.slugify(name)
            try:
                cur = db.execute("INSERT INTO careers (name, slug, icon, hue, description, project) VALUES (?,?,?,?,?,?)",
                                 (name, slug, icon, hue, description, project))
            except Exception:
                flash("A career with that name already exists.", "error")
                return render_template("admin/career_form.html", career=career, all_skills=all_skills,
                                       selected=selected_levels, form=request.form)
            career_id = cur.lastrowid
            flash(f"Career “{name}” created.", "success")
        else:
            career_id = career["id"]
            db.execute("UPDATE careers SET name=?, icon=?, hue=?, description=?, project=? WHERE id=?",
                       (name, icon, hue, description, project, career_id))
            flash(f"Career “{name}” updated.", "success")

        db.execute("DELETE FROM career_skills WHERE career_id=?", (career_id,))
        db.executemany("INSERT INTO career_skills (career_id, skill_id, required_level) VALUES (?,?,?)",
                       [(career_id, sid, lvl) for sid, lvl in selected_levels.items()])
        db.commit()
        return redirect(url_for("admin.dashboard"))

    selected = {}
    if career is not None:
        for r in models.get_career_requirements(career["id"]):
            selected[r["skill_id"]] = r["required_level"]
    return render_template("admin/career_form.html", career=career, all_skills=all_skills,
                           selected=selected, form={})


@bp.route("/careers/<int:career_id>/delete", methods=["POST"])
@admin_required
def career_delete(career_id):
    db = models.get_db()
    row = db.execute("SELECT name FROM careers WHERE id=?", (career_id,)).fetchone()
    if row is None:
        abort(404)
    db.execute("DELETE FROM careers WHERE id=?", (career_id,))
    db.commit()
    flash(f"Career “{row['name']}” deleted.", "info")
    return redirect(url_for("admin.dashboard"))


# ----------------------------------------------------------------- skills --

@bp.route("/skills/new", methods=["GET", "POST"])
@admin_required
def skill_new():
    return _skill_form(skill=None)


@bp.route("/skills/<int:skill_id>/edit", methods=["GET", "POST"])
@admin_required
def skill_edit(skill_id):
    skill = models.get_db().execute("SELECT * FROM skills WHERE id=?", (skill_id,)).fetchone()
    if skill is None:
        abort(404)
    return _skill_form(skill=skill)


def _skill_form(skill):
    db = models.get_db()
    categories = db.execute("SELECT * FROM skill_categories ORDER BY sort_order").fetchall()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category_id = request.form.get("category_id", "")
        description = request.form.get("description", "").strip()
        weeks_low = request.form.get("weeks_low", "2")
        weeks_high = request.form.get("weeks_high", "4")
        try:
            category_id = int(category_id)
            weeks_low, weeks_high = int(weeks_low), int(weeks_high)
        except ValueError:
            flash("Please fill every field correctly.", "error")
            return render_template("admin/skill_form.html", skill=skill, categories=categories, form=request.form)

        if not name:
            flash("Name is required.", "error")
            return render_template("admin/skill_form.html", skill=skill, categories=categories, form=request.form)

        if skill is None:
            try:
                db.execute("INSERT INTO skills (name, category_id, description, weeks_low, weeks_high) VALUES (?,?,?,?,?)",
                           (name, category_id, description, weeks_low, weeks_high))
            except Exception:
                flash("A skill with that name already exists.", "error")
                return render_template("admin/skill_form.html", skill=skill, categories=categories, form=request.form)
            flash(f"Skill “{name}” created.", "success")
        else:
            db.execute("UPDATE skills SET name=?, category_id=?, description=?, weeks_low=?, weeks_high=? WHERE id=?",
                       (name, category_id, description, weeks_low, weeks_high, skill["id"]))
            flash(f"Skill “{name}” updated.", "success")
        db.commit()
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/skill_form.html", skill=skill, categories=categories, form={})


@bp.route("/skills/<int:skill_id>/delete", methods=["POST"])
@admin_required
def skill_delete(skill_id):
    db = models.get_db()
    row = db.execute("SELECT name FROM skills WHERE id=?", (skill_id,)).fetchone()
    if row is None:
        abort(404)
    db.execute("DELETE FROM skills WHERE id=?", (skill_id,))
    db.commit()
    flash(f"Skill “{row['name']}” deleted.", "info")
    return redirect(url_for("admin.dashboard"))
