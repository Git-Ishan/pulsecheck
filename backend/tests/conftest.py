import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.database import Base


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session


from fastapi.testclient import TestClient  # noqa: E402

from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app, headers={"X-API-Key": "test-key"})
    app.dependency_overrides.clear()


from app import urlsafety  # noqa: E402


@pytest.fixture(autouse=True)
def fake_dns(monkeypatch):
    # No test should ever make a real DNS lookup.
    monkeypatch.setattr(urlsafety, "resolve_host", lambda host: ["93.184.216.34"])


from app import heartbeat  # noqa: E402


@pytest.fixture(autouse=True)
def reset_heartbeat():
    heartbeat.reset()
    yield
    heartbeat.reset()


from app import config, ratelimit  # noqa: E402


@pytest.fixture(autouse=True)
def api_key_and_limiter(monkeypatch):
    monkeypatch.setattr(config, "API_KEY", "test-key")
    ratelimit.manual_check_limiter.reset()
    yield
    ratelimit.manual_check_limiter.reset()


@pytest.fixture
def anon_client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)  # no API key header
    app.dependency_overrides.clear()
