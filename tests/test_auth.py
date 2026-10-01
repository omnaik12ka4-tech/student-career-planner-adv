"""Registration, login, logout, CSRF, and the "first user becomes admin" rule."""
import re

from tests.conftest import csrf


def test_public_pages_load(client):
    for url in ("/", "/login", "/register"):
        assert client.get(url).status_code == 200


def test_protected_pages_redirect_when_logged_out(client):
    for url in ("/dashboard", "/skills", "/careers", "/profile", "/admin"):
        assert client.get(url).status_code in (302, 401, 403)


def test_register_logs_in_and_redirects_to_skills(client, register):
    register("ana@example.com")
    r = client.get("/skills")
    assert r.status_code == 200
    assert "Choose your current skills" in r.get_data(as_text=True)


def test_first_registered_user_becomes_admin(client, register):
    register("first@example.com")
    r = client.get("/admin")
    assert r.status_code == 200


def test_second_user_is_not_admin(client, register):
    register("first@example.com")
    client.get("/logout")
    register("second@example.com")
    r = client.get("/admin")
    assert r.status_code == 403


def test_duplicate_email_rejected(client, register):
    register("dupe@example.com")
    client.get("/logout")
    html = client.get("/register").get_data(as_text=True)
    r = client.post("/register", data={"_csrf": csrf(html), "name": "Someone Else",
                                        "email": "dupe@example.com", "password": "secret1", "confirm": "secret1"})
    assert "already exists" in r.get_data(as_text=True)


def test_password_too_short_rejected(client):
    html = client.get("/register").get_data(as_text=True)
    r = client.post("/register", data={"_csrf": csrf(html), "name": "X", "email": "x@example.com",
                                        "password": "abc", "confirm": "abc"})
    assert "at least 6" in r.get_data(as_text=True)


def test_mismatched_passwords_rejected(client):
    html = client.get("/register").get_data(as_text=True)
    r = client.post("/register", data={"_csrf": csrf(html), "name": "X", "email": "x2@example.com",
                                        "password": "secret1", "confirm": "secret2"})
    assert "do not match" in r.get_data(as_text=True)


def test_post_without_csrf_token_is_rejected(client):
    r = client.post("/register", data={"name": "X", "email": "nocsrf@example.com",
                                        "password": "secret1", "confirm": "secret1"})
    assert r.status_code == 400


def test_login_with_wrong_password_fails(client, register):
    register("bob@example.com")
    client.get("/logout")
    html = client.get("/login").get_data(as_text=True)
    r = client.post("/login", data={"_csrf": csrf(html), "email": "bob@example.com", "password": "wrongpass"})
    assert "Invalid email or password" in r.get_data(as_text=True)


def test_login_with_correct_password_succeeds(client, register):
    register("carol@example.com")
    client.get("/logout")
    html = client.get("/login").get_data(as_text=True)
    r = client.post("/login", data={"_csrf": csrf(html), "email": "carol@example.com", "password": "secret1"})
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/dashboard")


def test_logout_then_dashboard_redirects(client, register):
    register("dana@example.com")
    client.get("/logout")
    r = client.get("/dashboard")
    assert r.status_code == 302
