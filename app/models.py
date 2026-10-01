"""
Data layer. Careers and skills used to be hard-coded Python dictionaries -
they now live in the database, in these tables:

    skill_categories(id, name, icon, sort_order)
    skills(id, name, category_id, description, weeks_low, weeks_high)
    careers(id, name, slug, icon, hue, description, project)
    career_skills(career_id, skill_id, required_level)   <- required_level: 1/2/3
    user_skills(user_id, skill_id, level)                <- level: 1/2/3
    users(id, name, email, password, course, year, created_at, last_login, is_admin)

Levels are 1=Beginner, 2=Intermediate, 3=Advanced. Storing a *level* instead
of a plain checkbox is what lets the scoring in scoring.py give partial
credit ("you're Beginner in SQL but this career wants Advanced").

Careers/skills are seeded once, the first time the app runs against an
empty database (see seed_if_empty). After that, the admin panel is the
only thing that changes them - editing app.py is no longer needed.
"""
import sqlite3
from datetime import datetime, timezone

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    course TEXT DEFAULT 'BSc Computer Science',
    year TEXT DEFAULT 'TY',
    created_at TEXT,
    last_login TEXT,
    is_admin INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS skill_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    icon TEXT DEFAULT '🔧',
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    category_id INTEGER NOT NULL,
    description TEXT DEFAULT '',
    weeks_low INTEGER DEFAULT 2,
    weeks_high INTEGER DEFAULT 4,
    FOREIGN KEY(category_id) REFERENCES skill_categories(id)
);

CREATE TABLE IF NOT EXISTS careers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    icon TEXT DEFAULT '💼',
    hue INTEGER DEFAULT 220,
    description TEXT DEFAULT '',
    project TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS career_skills (
    career_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    required_level INTEGER NOT NULL DEFAULT 2,
    PRIMARY KEY (career_id, skill_id),
    FOREIGN KEY(career_id) REFERENCES careers(id) ON DELETE CASCADE,
    FOREIGN KEY(skill_id) REFERENCES skills(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_skills (
    user_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    level INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, skill_id),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(skill_id) REFERENCES skills(id) ON DELETE CASCADE
);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db(app.config["DATABASE"])


def init_db(path):
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    seed_if_empty(path)


# --------------------------------------------------------------------------
# SEED DATA - the original 8 careers / 25 skills, now loaded into the
# database instead of living as Python constants. Advanced-skill flavour:
# a hand-picked set of "harder" skills require Advanced level, the rest
# require Intermediate - this only affects the seed, admins can change any
# of it afterwards.
# --------------------------------------------------------------------------

CATEGORY_SEED = [
    ("Programming & Tools", "💻"), ("Web", "🌐"), ("Data & AI", "📊"),
    ("Systems & Security", "🛡️"), ("Cloud & DevOps", "☁️"),
]

SKILL_SEED = {
    "Python": ("Programming & Tools", "Popular, beginner-friendly programming language", 4, 6),
    "OOP": ("Programming & Tools", "Organising code into reusable classes and objects", 2, 3),
    "Git": ("Programming & Tools", "Tracking code changes and working in teams", 1, 2),
    "Testing": ("Programming & Tools", "Checking that software works as expected", 2, 3),
    "HTML": ("Web", "The structure of every web page", 1, 2),
    "CSS": ("Web", "Styling and layout for web pages", 2, 3),
    "JavaScript": ("Web", "Makes web pages interactive", 4, 6),
    "Flask": ("Web", "A lightweight Python framework for websites", 2, 4),
    "APIs": ("Web", "How programs talk to each other over the web", 2, 3),
    "Excel": ("Data & AI", "Spreadsheets, formulas and pivot tables", 2, 3),
    "SQL": ("Data & AI", "Asking questions of databases", 2, 4),
    "Statistics": ("Data & AI", "Averages, probability and conclusions from data", 3, 5),
    "Pandas": ("Data & AI", "Python library for working with tables of data", 2, 3),
    "Power BI": ("Data & AI", "Turning data into interactive dashboards", 2, 3),
    "Machine Learning": ("Data & AI", "Teaching computers to learn patterns from data", 6, 10),
    "Data Visualization": ("Data & AI", "Charts that make data easy to understand", 2, 3),
    "Networking": ("Systems & Security", "How computers connect: IP, DNS, routers", 4, 6),
    "Windows": ("Systems & Security", "Using and fixing Windows systems", 2, 3),
    "Linux": ("Systems & Security", "Command line and servers, the backbone of the cloud", 3, 5),
    "Troubleshooting": ("Systems & Security", "Finding and fixing problems step by step", 2, 4),
    "Cybersecurity": ("Systems & Security", "Protecting systems and spotting attacks", 6, 8),
    "Cryptography": ("Systems & Security", "Encryption, hashing and keeping data secret", 3, 5),
    "Docker": ("Cloud & DevOps", "Packaging apps so they run anywhere", 2, 3),
    "AWS": ("Cloud & DevOps", "Amazon's cloud: servers, storage and databases", 4, 6),
    "CI/CD": ("Cloud & DevOps", "Automatically testing and deploying code", 2, 3),
}

# Skills that require ADVANCED level in any career that lists them (everything
# else defaults to Intermediate). Roughly: the skills with the longest
# study estimate above, i.e. the ones that take real depth to be useful.
ADVANCED_SKILLS = {"Machine Learning", "Cybersecurity", "Cryptography", "AWS", "CI/CD", "Networking", "Statistics"}

CAREER_SEED = [
    ("Data Analyst", "📊", 215,
     "Works with data to find patterns, create reports and support business decisions.",
     ["Excel", "SQL", "Python", "Statistics", "Pandas", "Power BI"],
     "Analyse a public sales dataset and build a Power BI dashboard with 3 business insights."),
    ("Python Developer", "🐍", 145,
     "Builds applications, automation tools and backend systems using Python.",
     ["Python", "SQL", "Flask", "Git", "OOP", "APIs"],
     "Build a REST API for an expense tracker and publish the code on GitHub."),
    ("Web Developer", "🌐", 265,
     "Builds and maintains websites and web applications.",
     ["HTML", "CSS", "JavaScript", "SQL", "Git", "Flask"],
     "Create a responsive portfolio website with a contact form that saves messages to a database."),
    ("IT Support Engineer", "🖥️", 30,
     "Helps users solve computer, software, network and system-related problems.",
     ["Networking", "Windows", "Linux", "Troubleshooting", "SQL", "Python"],
     "Set up a small home lab (a Linux and a Windows VM) and write a Python script that checks if both are reachable."),
    ("Cybersecurity Analyst", "🛡️", 350,
     "Monitors systems and helps identify and respond to security issues.",
     ["Networking", "Linux", "Cybersecurity", "Python", "SQL", "Cryptography"],
     "Write a Python script that scans a log file for failed logins and flags suspicious IP addresses."),
    ("Data Scientist", "🤖", 290,
     "Uses statistics and machine learning to build models that predict and explain things.",
     ["Python", "Statistics", "Pandas", "Machine Learning", "SQL", "Data Visualization"],
     "Predict student marks or house prices with a simple regression model and explain the results with charts."),
    ("Software Tester (QA)", "🧪", 175,
     "Finds bugs before users do by writing test cases and automating checks.",
     ["Testing", "SQL", "Git", "Python", "APIs", "Troubleshooting"],
     "Write test cases and automated tests for a small web app, then report the bugs in a clear format."),
    ("Cloud & DevOps Engineer", "☁️", 200,
     "Deploys and runs applications on the cloud and automates how software is shipped.",
     ["Linux", "Docker", "Git", "AWS", "CI/CD", "Networking"],
     "Containerise a small Flask app with Docker and build it automatically on every Git push."),
]


def slugify(text):
    import re
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def seed_if_empty(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if conn.execute("SELECT 1 FROM careers LIMIT 1").fetchone():
        conn.close()
        return  # already seeded (or the admin has real data) - never overwrite

    cat_ids = {}
    for i, (name, icon) in enumerate(CATEGORY_SEED):
        cur = conn.execute("INSERT INTO skill_categories (name, icon, sort_order) VALUES (?,?,?)", (name, icon, i))
        cat_ids[name] = cur.lastrowid

    skill_ids = {}
    for name, (cat, desc, low, high) in SKILL_SEED.items():
        cur = conn.execute(
            "INSERT INTO skills (name, category_id, description, weeks_low, weeks_high) VALUES (?,?,?,?,?)",
            (name, cat_ids[cat], desc, low, high))
        skill_ids[name] = cur.lastrowid

    for name, icon, hue, desc, skills, project in CAREER_SEED:
        cur = conn.execute(
            "INSERT INTO careers (name, slug, icon, hue, description, project) VALUES (?,?,?,?,?,?)",
            (name, slugify(name), icon, hue, desc, project))
        career_id = cur.lastrowid
        for skill_name in skills:
            level = 3 if skill_name in ADVANCED_SKILLS else 2
            conn.execute("INSERT INTO career_skills (career_id, skill_id, required_level) VALUES (?,?,?)",
                        (career_id, skill_ids[skill_name], level))
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------
# Query helpers used by the routes
# --------------------------------------------------------------------------

def now_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def get_categories_with_skills():
    db = get_db()
    cats = db.execute("SELECT * FROM skill_categories ORDER BY sort_order").fetchall()
    out = []
    for c in cats:
        skills = db.execute("SELECT * FROM skills WHERE category_id=? ORDER BY name", (c["id"],)).fetchall()
        out.append({"id": c["id"], "name": c["name"], "icon": c["icon"], "skills": skills})
    return out


def get_all_skills():
    return get_db().execute("SELECT s.*, c.name AS category_name FROM skills s "
                            "JOIN skill_categories c ON c.id = s.category_id ORDER BY c.sort_order, s.name").fetchall()


def get_all_careers():
    return get_db().execute("SELECT * FROM careers ORDER BY name").fetchall()


def get_career_by_slug(slug):
    return get_db().execute("SELECT * FROM careers WHERE slug=?", (slug,)).fetchone()


def get_career_requirements(career_id):
    """[{skill_id, name, required_level, category_name}, ...] for one career."""
    return get_db().execute(
        """SELECT cs.skill_id, cs.required_level, s.name, s.description, s.weeks_low, s.weeks_high
           FROM career_skills cs JOIN skills s ON s.id = cs.skill_id
           WHERE cs.career_id=? ORDER BY cs.required_level DESC, s.name""", (career_id,)).fetchall()


def get_user_levels(user_id):
    """{skill_id: level} for one student."""
    rows = get_db().execute("SELECT skill_id, level FROM user_skills WHERE user_id=?", (user_id,)).fetchall()
    return {r["skill_id"]: r["level"] for r in rows}


def set_user_levels(user_id, levels):
    """levels: {skill_id: level}. level 0 removes the row (means 'not started')."""
    db = get_db()
    db.execute("DELETE FROM user_skills WHERE user_id=?", (user_id,))
    rows = [(user_id, sid, lvl) for sid, lvl in levels.items() if lvl and lvl > 0]
    if rows:
        db.executemany("INSERT INTO user_skills (user_id, skill_id, level) VALUES (?,?,?)", rows)
    db.commit()
