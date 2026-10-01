"""End-to-end tests through real HTTP requests: skills, careers, roadmap, profile."""
import re

from tests.conftest import csrf


def _skill_id_map(html):
    """Skills page markup: <div class="skill-level-row" data-skill="python" data-skill-id="3">"""
    return dict(re.findall(r'data-skill="([a-z0-9 /+#.\-]+)" data-skill-id="(\d+)"', html))


def test_dashboard_empty_state_when_no_skills(client, register):
    register("empty@example.com")
    html = client.get("/dashboard").get_data(as_text=True)
    assert "Let's find your best career match" in html


def test_saving_skills_updates_dashboard_score(client, register):
    register("scorer@example.com")
    html = client.get("/skills").get_data(as_text=True)
    ids = _skill_id_map(html)
    t = csrf(html)
    form = {"_csrf": t,
            f"level_{ids['python']}": "2", f"level_{ids['sql']}": "2",
            f"level_{ids['excel']}": "2", f"level_{ids['pandas']}": "2",
            f"level_{ids['power bi']}": "2", f"level_{ids['statistics']}": "3"}
    r = client.post("/skills", data=form)
    assert r.status_code == 302
    html = client.get("/dashboard").get_data(as_text=True)
    assert "Data Analyst" in html
    assert "100%" in html   # every Data Analyst requirement fully met


def test_career_detail_404_for_unknown_slug(client, register):
    register("roamer@example.com")
    r = client.get("/career/not-a-real-career")
    assert r.status_code == 404


def test_career_detail_200_for_real_slug(client, register):
    register("roamer2@example.com")
    r = client.get("/career/data-analyst")
    assert r.status_code == 200
    assert "Your roadmap" in r.get_data(as_text=True)


def test_careers_page_lists_all_seeded_careers(client, register):
    register("browser@example.com")
    html = client.get("/careers").get_data(as_text=True)
    assert html.count("career-card") == 8


def test_profile_update_changes_name(client, register):
    register("profiler@example.com")
    html = client.get("/profile").get_data(as_text=True)
    t = csrf(html)
    r = client.post("/profile", data={"_csrf": t, "name": "New Name", "course": "BSc CS", "year": "SY"})
    assert r.status_code == 302
    html = client.get("/profile").get_data(as_text=True)
    assert "New Name" in html


def test_profile_rejects_empty_name(client, register):
    register("profiler2@example.com")
    html = client.get("/profile").get_data(as_text=True)
    t = csrf(html)
    r = client.post("/profile", data={"_csrf": t, "name": "", "course": "x", "year": "TY"})
    assert r.status_code == 302
    html = client.get(r.headers["Location"]).get_data(as_text=True) if False else client.get("/profile").get_data(as_text=True)
    # name unchanged (still the original registration name, not blank)
    assert "Test Student" in html
