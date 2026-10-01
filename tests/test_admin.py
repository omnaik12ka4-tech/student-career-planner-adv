"""Admin-only permission checks and the career/skill CRUD flows."""
import re

from tests.conftest import csrf


def _skill_select_ids(html):
    """Career form markup: <span>Python</span>\n<select name="required_7">"""
    return dict(re.findall(r'<span>([A-Za-z0-9 /+#.\-]+)</span>\s*<select name="required_(\d+)"', html))


def test_non_admin_gets_403_on_every_admin_route(client, register):
    register("someone-else@example.com")   # first user -> becomes admin
    client.get("/logout")
    register("plain@example.com")          # second user -> NOT admin
    for url in ("/admin", "/admin/careers/new", "/admin/skills/new"):
        assert client.get(url).status_code == 403


def test_admin_can_create_a_skill(client, register):
    register("admin@example.com")   # first user = admin
    html = client.get("/admin/skills/new").get_data(as_text=True)
    t = csrf(html)
    r = client.post("/admin/skills/new", data={
        "_csrf": t, "name": "Rust", "category_id": "1",
        "description": "A fast, memory-safe systems language", "weeks_low": "6", "weeks_high": "10"})
    assert r.status_code == 302
    html = client.get("/admin").get_data(as_text=True)
    assert "Rust" in html


def test_admin_can_create_a_career_with_required_skills(client, register):
    register("admin2@example.com")
    html = client.get("/admin/careers/new").get_data(as_text=True)
    t = csrf(html)
    skills = _skill_select_ids(html)
    form = {"_csrf": t, "name": "Mobile Developer", "icon": "📱", "hue": "260",
            "description": "Builds mobile apps.", "project": "Build a to-do app."}
    form[f"required_{skills['Python']}"] = "2"
    form[f"required_{skills['Git']}"] = "1"
    r = client.post("/admin/careers/new", data=form)
    assert r.status_code == 302
    html = client.get("/careers").get_data(as_text=True)
    assert "Mobile Developer" in html


def test_creating_career_without_any_required_skill_is_rejected(client, register):
    register("admin3@example.com")
    html = client.get("/admin/careers/new").get_data(as_text=True)
    t = csrf(html)
    r = client.post("/admin/careers/new", data={"_csrf": t, "name": "Empty Career", "icon": "💼",
                                                 "hue": "100", "description": "d", "project": "p"})
    assert "Pick at least one required skill" in r.get_data(as_text=True)
    html = client.get("/careers").get_data(as_text=True)
    assert "Empty Career" not in html


def test_admin_can_edit_a_career(client, register):
    register("admin4@example.com")
    html = client.get("/admin/careers/1/edit").get_data(as_text=True)
    t = csrf(html)
    skills = _skill_select_ids(html)
    form = {"_csrf": t, "name": "Data Analyst Pro", "icon": "📈", "hue": "215",
            "description": "Updated.", "project": "Updated project."}
    form[f"required_{skills['Excel']}"] = "2"
    r = client.post("/admin/careers/1/edit", data=form)
    assert r.status_code == 302
    html = client.get("/admin").get_data(as_text=True)
    assert "Data Analyst Pro" in html


def test_admin_can_delete_a_career(client, register):
    register("admin5@example.com")
    html = client.get("/admin/careers/1/edit").get_data(as_text=True)
    t = csrf(html)
    r = client.post("/admin/careers/1/delete", data={"_csrf": t})
    assert r.status_code == 302
    html = client.get("/careers").get_data(as_text=True)
    assert html.count("career-card") == 7


def test_admin_sees_registered_students(client, register):
    register("admin6@example.com")
    client.get("/logout")
    register("student@example.com", name="A Student")
    client.get("/logout")
    html = client.get("/register").get_data(as_text=True)
    # log back in as admin
    from tests.conftest import csrf as _csrf
    t = _csrf(client.get("/login").get_data(as_text=True))
    client.post("/login", data={"_csrf": t, "email": "admin6@example.com", "password": "secret1"})
    html = client.get("/admin").get_data(as_text=True)
    assert "A Student" in html
