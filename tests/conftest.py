"""Shared pytest fixtures. Each test gets a brand-new, empty SQLite file, so
tests never see another test's data and can run in any order."""
import os
import re
import tempfile

import pytest

from app import create_app


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app = create_app({"TESTING": True, "DATABASE": db_path, "SECRET_KEY": "test-secret"})
    yield app
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


def csrf(html):
    return re.search(r'name="_csrf" value="([^"]+)"', html).group(1)


@pytest.fixture
def register(client):
    """Factory: register(email, name='Student') -> logs the client in, returns the CSRF token."""
    def _register(email, name="Test Student", password="secret1"):
        html = client.get("/register").get_data(as_text=True)
        t = csrf(html)
        client.post("/register", data={"_csrf": t, "name": name, "email": email,
                                        "password": password, "confirm": password})
        return t
    return _register
