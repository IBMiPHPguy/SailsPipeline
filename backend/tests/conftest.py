import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-tests")
os.environ.setdefault("ALLOW_PUBLIC_REGISTRATION", "true")
os.environ.setdefault("CORS_ORIGINS", "http://testserver")
os.environ.setdefault("EXPOSE_OPENAPI", "true")
os.environ.setdefault("SEED_ADMIN_USERNAME", "")
os.environ.setdefault("SEED_ADMIN_PASSWORD", "")
os.environ.setdefault("ATTACHMENTS_DIR", "/tmp/sailspipeline-test-uploads")
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "sqlite://"

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services.agency_service import ensure_default_agency  # noqa: E402
from app.tenant_constants import DEFAULT_AGENCY_ID, DEFAULT_AGENCY_ORGANIZATION_HANDLE  # noqa: E402
from app.tenant_roles import USER_ROLE_TENANT_SUPER_USER
from app.tenant_context import clear_current_agency_id, set_current_agency_id  # noqa: E402


class _NoCloseSession:
    """Wrap a test session so middleware close() does not tear down the fixture."""

    def __init__(self, session):
        self._session = session

    def __getattr__(self, name):
        return getattr(self._session, name)

    def close(self) -> None:
        return None


def _create_test_engine():
    database_url = os.environ["DATABASE_URL"]
    if database_url.startswith("sqlite"):
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(database_url, pool_pre_ping=True)


def _ensure_agency_groups_schema(engine) -> None:
    database_url = os.environ["DATABASE_URL"]
    if database_url.startswith("sqlite"):
        return

    from app.models import AgencyGroup, AgencyGroupInventory  # noqa: WPS433

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "agency_groups" not in table_names:
        Base.metadata.create_all(
            bind=engine,
            tables=[AgencyGroup.__table__, AgencyGroupInventory.__table__],
        )
        inspector = inspect(engine)

    if "travel_requests" in inspector.get_table_names():
        request_columns = {column["name"] for column in inspector.get_columns("travel_requests")}
        alters: list[str] = []
        added_group_columns = False
        if "ship_name" not in request_columns:
            alters.append("ADD COLUMN ship_name VARCHAR(100) NULL AFTER destination_details")
        if "group_id" not in request_columns:
            alters.append("ADD COLUMN group_id CHAR(36) NULL AFTER marketing_campaign_id")
            added_group_columns = True
        if "group_inventory_id" not in request_columns:
            alters.append("ADD COLUMN group_inventory_id CHAR(36) NULL AFTER group_id")
            added_group_columns = True
        if alters:
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE travel_requests {', '.join(alters)}"))
        if added_group_columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE travel_requests "
                        "ADD CONSTRAINT fk_travel_requests_group "
                        "FOREIGN KEY (group_id) REFERENCES agency_groups(id) ON DELETE SET NULL"
                    )
                )
                connection.execute(
                    text(
                        "ALTER TABLE travel_requests "
                        "ADD CONSTRAINT fk_travel_requests_group_inventory "
                        "FOREIGN KEY (group_inventory_id) REFERENCES agency_group_inventory(id) ON DELETE SET NULL"
                    )
                )
                connection.execute(text("CREATE INDEX idx_travel_requests_group ON travel_requests(group_id)"))


def _ensure_workflow_engine_schema(engine) -> None:
    database_url = os.environ["DATABASE_URL"]
    if database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "agency_workflow_templates" in inspector.get_table_names():
        workflow_columns = {column["name"] for column in inspector.get_columns("agency_workflow_templates")}
        if "archived_at" not in workflow_columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE agency_workflow_templates "
                        "ADD COLUMN archived_at TIMESTAMP NULL DEFAULT NULL AFTER created_at"
                    )
                )
        if "agency_custom_task_definitions" not in inspector.get_table_names():
            from app.models import AgencyCustomTaskDefinition  # noqa: WPS433

            Base.metadata.create_all(
                bind=engine,
                tables=[AgencyCustomTaskDefinition.__table__],
            )
        return

    from app.models import (  # noqa: WPS433
        AgencyCustomTaskDefinition,
        AgencyTaskTemplate,
        AgencyWorkflowTemplate,
        RequestTaskLive,
        RequestWorkflowLive,
    )

    Base.metadata.create_all(
        bind=engine,
        tables=[
            AgencyWorkflowTemplate.__table__,
            AgencyTaskTemplate.__table__,
            AgencyCustomTaskDefinition.__table__,
            RequestWorkflowLive.__table__,
            RequestTaskLive.__table__,
        ],
    )

    communication_columns = {column["name"] for column in inspector.get_columns("request_communications")}
    if "request_workflow_live_id" not in communication_columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE request_communications "
                    "ADD COLUMN request_workflow_live_id CHAR(36) NULL AFTER request_workflow_id"
                )
            )
            connection.execute(
                text(
                    "ALTER TABLE request_communications "
                    "ADD CONSTRAINT fk_request_communications_workflow_live "
                    "FOREIGN KEY (request_workflow_live_id) "
                    "REFERENCES request_workflows_live(id) ON DELETE SET NULL"
                )
            )


@pytest.fixture(scope="session")
def engine():
    test_engine = _create_test_engine()
    database_url = os.environ["DATABASE_URL"]
    if database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=test_engine)
    else:
        _ensure_workflow_engine_schema(test_engine)
        _ensure_agency_groups_schema(test_engine)
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

    ensure_default_agency(session)
    from app.services.workflow_template_seed import seed_agency_workflow_templates
    from app.tenant_constants import DEFAULT_AGENCY_ID

    seed_agency_workflow_templates(session, DEFAULT_AGENCY_ID)
    from app.services.agency_group_seed import seed_agency_groups

    seed_agency_groups(session, DEFAULT_AGENCY_ID)
    session.commit()
    set_current_agency_id(DEFAULT_AGENCY_ID)

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.expire_all()
            sess.begin_nested()

    yield session
    clear_current_agency_id()
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    from app import subscription_gatekeeper as subscription_gatekeeper_module

    original_session_local = subscription_gatekeeper_module.SessionLocal
    subscription_gatekeeper_module.SessionLocal = lambda: _NoCloseSession(db)

    with TestClient(app) as test_client:
        yield test_client

    subscription_gatekeeper_module.SessionLocal = original_session_local
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    user = User(
        agency_id=DEFAULT_AGENCY_ID,
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("TestPassword1!"),
        role=USER_ROLE_TENANT_SUPER_USER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(client, test_user):
    response = client.post(
        "/api/auth/login",
        json={
            "organization_handle": DEFAULT_AGENCY_ORGANIZATION_HANDLE,
            "username": test_user.username,
            "password": "TestPassword1!",
        },
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
