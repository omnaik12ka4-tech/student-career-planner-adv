"""Registration, login, logout, and the CSRF / session plumbing shared by every page."""
import secrets
from functools import wraps

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from . import models

bp = Blueprint("auth", __name__)


def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


@bp.record_once
def _register_globals(state):
    state.app.jinja_env.globals["csrf_token"] = csrf_token


@bp.before_app_request
def load_user():
    g.user = None
    if request.endpoint == "static":
        return
    user_id = session.get("user_id")
    if not user_id:
        return
    g.user = models.get_db().execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if g.user is None:
        session.pop("user_id", None)


@bp.before_app_request
def csrf_protect():
    if request.method == "POST":
        sent = request.form.get("_csrf", "")
        if not sent or not secrets.compare_digest(sent, session.get("_csrf", "")):
            abort(400)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please log in to continue.", "info")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please log in to continue.", "info")
            return redirect(url_for("auth.login"))
        if not g.user["is_admin"]:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def _should_be_admin(email):
    """First account ever created becomes admin, unless ADMIN_EMAIL is set - then only that email does."""
    wanted = current_app.config.get("ADMIN_EMAIL", "")
    if wanted:
        return email == wanted
    return models.get_db().execute("SELECT 1 FROM users LIMIT 1").fetchone() is None


@bp.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        error = None

        if not name or not email or not password:
            error = "Please fill all required fields."
        elif len(name) > 60:
            error = "Name is too long (max 60 characters)."
        elif "@" not in email or "." not in email.split("@")[-1]:
            error = "Please enter a valid email address."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != confirm:
            error = "Passwords do not match."

        if error:
            flash(error, "error")
            return render_template("register.html", form=request.form)

        db = models.get_db()
        make_admin = _should_be_admin(email)
        try:
            cur = db.execute(
                "INSERT INTO users (name,email,password,created_at,last_login,is_admin) VALUES (?,?,?,?,?,?)",
                (name, email, generate_password_hash(password), models.now_str(), models.now_str(), int(make_admin)))
            db.commit()
        except Exception:
            flash("An account with this email already exists.", "error")
            return render_template("register.html", form=request.form)

        session["user_id"] = cur.lastrowid
        if make_admin:
            flash("Welcome! You're the admin - open “Admin” in the menu to manage careers and skills.", "success")
        else:
            flash(f"Welcome, {name.split()[0]}! Pick the skills you already have to get started.", "success")
        return redirect(url_for("main.skills"))

    return render_template("register.html", form={})


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        db = models.get_db()
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

        if user and check_password_hash(user["password"], password):
            wanted = current_app.config.get("ADMIN_EMAIL", "")
            is_admin = user["is_admin"] or (wanted and email == wanted)
            db.execute("UPDATE users SET last_login=?, is_admin=? WHERE id=?",
                       (models.now_str(), int(bool(is_admin)), user["id"]))
            db.commit()
            csrf = session.get("_csrf")
            session.clear()
            session["_csrf"] = csrf or secrets.token_hex(16)
            session["user_id"] = user["id"]
            return redirect(url_for("main.dashboard"))

        flash("Invalid email or password.", "error")
        return render_template("login.html", form=request.form)

    return render_template("login.html", form={})


@bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
