from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.frontend import mount_frontend


def make_client(tmp_path):
    (tmp_path / "index.html").write_text("<h1>dashboard</h1>")
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    assert mount_frontend(app, str(tmp_path)) is True
    return TestClient(app)


def test_root_serves_the_frontend(tmp_path):
    response = make_client(tmp_path).get("/")
    assert response.status_code == 200
    assert "dashboard" in response.text


def test_api_routes_win_over_the_frontend(tmp_path):
    response = make_client(tmp_path).get("/health")
    assert response.json() == {"status": "ok"}


def test_unknown_path_is_404(tmp_path):
    assert make_client(tmp_path).get("/nope").status_code == 404


def test_missing_directory_is_ignored(tmp_path):
    assert mount_frontend(FastAPI(), str(tmp_path / "missing")) is False
