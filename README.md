# Smart Student Career Planner — Advanced Edition

A TY BSc CS mini-project built with **Flask**, **SQLite**, and a small vanilla-JS frontend.
Set a skill level for everything you know → get weighted career matches, a skill-gap
analysis, and a step-by-step roadmap. Careers and skills are managed by an **admin panel**,
not hard-coded — and the whole thing ships with a real test suite and Docker deployment.

## What's new in this edition

| Before | Now |
|---|---|
| Skills were a checkbox (have it / don't) | Every skill has a **level**: Beginner, Intermediate, Advanced |
| Match % = matched ÷ total | Match % = **weighted**: partial credit for under-levelled skills, capped at full credit for over-qualification |
| Careers/skills were Python constants in `app.py` | Careers/skills live in **SQLite**, editable from an **admin panel** |
| One 500-line `app.py` | Proper **app factory** + **blueprints** (`auth`, `main`, `admin`) |
| No automated tests | **34 pytest tests** covering scoring, auth, routes, and admin CRUD |
| `app.run(debug=True)` only | **Docker**, **docker-compose**, **Gunicorn**, and a `Procfile` for Render/Railway |

## How the scoring actually works (good for the viva)

Every career lists required skills at a level (1=Beginner, 2=Intermediate, 3=Advanced).
Every student sets their own level per skill. For each required skill:

```
contribution = min(your_level, required_level) / required_level
```

So being Beginner (1) in a skill that needs Advanced (3) contributes 1/3 — closer than
nothing, but clearly not there yet. Being over-qualified never gives more than full credit
(a career that needs Intermediate doesn't score you extra for being Advanced).

```
match % = sum(contribution for every required skill) / number of required skills × 100
```

This is implemented in `app/scoring.py` as a small set of pure functions with **zero**
dependency on Flask or the database — which is what makes them unit-testable in isolation
(see `tests/test_scoring.py`).

## Project structure

```
app/
  __init__.py     app factory (create_app) - wires blueprints, config, DB
  config.py       all settings read from environment variables
  models.py       SQLite schema, seed data, query helpers
  scoring.py       the weighted matching engine (pure functions, no Flask)
  auth.py          register / login / logout / CSRF / login_required / admin_required
  main.py          dashboard, skills, careers, career detail, profile
  admin.py         admin dashboard + full CRUD for careers and skills
  errors.py        404 / 403 / 400 error pages
templates/         HTML (Jinja2) - unchanged look, updated for the new data model
  admin/           admin dashboard, career form, skill form
static/            style.css (design system) + app.js (level pills, radar chart, etc.)
tests/
  conftest.py      pytest fixtures: app, client, register
  test_scoring.py  unit tests for the matching algorithm (no Flask needed)
  test_auth.py     registration, login, CSRF, admin-assignment rules
  test_routes.py   dashboard, skills, careers, career detail, profile
  test_admin.py    permission checks + full CRUD flows
app.py             local dev entry point:  python app.py
wsgi.py            production entry point for gunicorn:  gunicorn wsgi:app
Dockerfile, docker-compose.yml, .env.example, Procfile     deployment
```

## Run it locally

```bash
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000. The database (`career_planner.db`) and its 8 careers /
25 skills are created automatically on first run.

**The first account you register becomes the admin** and gets an "🛠️ Admin" link in the
nav bar, where careers and skills can be created, edited, and deleted. To fix who the
admin is regardless of registration order, set `ADMIN_EMAIL` in a `.env` file (see
`.env.example`) before that person registers.

## Run the tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

34 tests, split by concern:
- `test_scoring.py` — the algorithm itself: full match, zero match, partial credit,
  over-qualification, readiness labels, "learn next" ranking, category coverage.
- `test_auth.py` — registration validation, duplicate emails, CSRF enforcement, login/logout,
  the "first user = admin" rule.
- `test_routes.py` — dashboard states, saving skills actually changes the score, 404s,
  profile editing.
- `test_admin.py` — non-admins get 403 everywhere under `/admin`, and the full
  create/edit/delete flow for both careers and skills.

## Deployment

**Docker (recommended — works anywhere Docker runs):**
```bash
cp .env.example .env   # fill in a real SECRET_KEY
docker compose up --build
```
The SQLite file is kept in a named volume (`career_data`), so it survives container
restarts and rebuilds.

**Render / Railway / any Heroku-style host:**
The included `Procfile` (`web: gunicorn wsgi:app --bind 0.0.0.0:$PORT`) is picked up
automatically by most of these platforms — just connect the repo, set `SECRET_KEY` and
optionally `ADMIN_EMAIL` as environment variables, and deploy.

**Plain Gunicorn, no Docker:**
```bash
pip install -r requirements.txt
gunicorn wsgi:app --bind 0.0.0.0:8000
```

## Add your own career or skill

You no longer need to touch code — log in as the admin and use "+ New career" /
"+ New skill" in the admin panel. The very first time the app runs against an empty
database, it seeds the original 8 careers and 25 skills automatically
(`app/models.py::seed_if_empty`) — after that, the admin panel is the only thing that
changes them.

## Ideas for the future

- Resume upload with automatic skill extraction (NLP)
- Email verification and password reset
- Rate limiting on `/login` (e.g. Flask-Limiter)
- Move from raw `sqlite3` to SQLAlchemy + Alembic migrations if the schema keeps growing
- A "who's online now" panel for admins (last-activity tracking)

## Note

The match percentage is a project heuristic, not a professional career assessment.
