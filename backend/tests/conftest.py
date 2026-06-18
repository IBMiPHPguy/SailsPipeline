import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-tests")
os.environ.setdefault("SEED_ADMIN_USERNAME", "")
os.environ.setdefault("SEED_ADMIN_PASSWORD", "")
os.environ.setdefault("ATTACHMENTS_DIR", "/tmp/cruisetravelnow-test-uploads")
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "sqlite://"

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.security import hash_password  # noqa: E402


def _create_test_engine():
    database_url = os.environ["DATABASE_URL"]
    if database_url.startswith("sqlite"):
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(database_url, pool_pre_ping=True)


@pytest.fixture(scope="session")
def engine():
    test_engine = _create_test_engine()
    database_url = os.environ["DATABASE_URL"]
    if database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=test_engine)
    yield test_engine
    if database_url.startswith("sqlite"):
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="session")
def session_factory(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db(session_factory, engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = session_factory(bind=connection)
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.expire_all()
            sess.begin_nested()

    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("TestPassword1!"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(client, test_user):
    response = client.post(
        "/api/auth/login",
        data={"username": test_user.username, "password": "TestPassword1!"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_request_payload():
    return {
        "first_name": "Jane",
        "last_name": "Cruiser",
        "email": "jane@example.com",
        "phone": "5551234567",
        "cruise_lines": ["Royal Caribbean International"],
        "destination": "Caribbean",
        "destination_details": {"caribbean_regions": ["Eastern"]},
        "departure_date": "2026-06-01",
        "return_date": "2026-06-08",
        "cabin_types": ["Balcony"],
        "passengers": 2,
        "cabins_needed": 1,
    }
