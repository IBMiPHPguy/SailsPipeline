"""Regression tests for ID-guessing attacks on child records without direct agency_id."""

from datetime import date

import pytest
from fastapi import HTTPException

from app.models import (
    Agency,
    AgencyGroup,
    AgencyGroupInventory,
    AgencyTaskTemplate,
    AgencyWorkflowTemplate,
    Passenger,
    RequestPassenger,
    TravelRequest,
    User,
)
from app.passenger_helpers import attach_passenger_to_request
from app.security import hash_password
from app.services.agency_group_service import get_agency_group_inventory_for_agency
from app.services.passenger_service import get_request_passenger_for_agency
from app.services.workflow_template_service import load_workflow_template
from app.tenant_constants import DEFAULT_AGENCY_ID
from app.tenant_context import clear_current_agency_id, set_current_agency_id
from app.tenant_roles import SUBSCRIPTION_STATE_ACTIVE, USER_ROLE_TENANT_SUPER_USER

AGENCY_ONE_ID = DEFAULT_AGENCY_ID
AGENCY_TWO_ID = "00000000-0000-4000-8000-000000000002"

AGENCY_ONE_GROUP_ID = "11111111-1111-4111-8111-111111111101"
AGENCY_ONE_INVENTORY_ID = "22222222-2222-4222-8222-222222222201"
AGENCY_ONE_WORKFLOW_ID = "33333333-3333-4333-8333-333333333301"
AGENCY_ONE_TASK_ID = "44444444-4444-4444-8444-444444444401"


def _expect_not_found(callable) -> None:
    try:
        callable()
    except HTTPException as exc:
        assert exc.status_code == 404
        return
    pytest.fail("Expected HTTP 404 Not Found.")


@pytest.fixture(autouse=True)
def restore_default_agency_context():
    set_current_agency_id(AGENCY_ONE_ID)
    yield
    set_current_agency_id(AGENCY_ONE_ID)


@pytest.fixture
def agency_one_user(db) -> User:
    user = User(
        agency_id=AGENCY_ONE_ID,
        username="agency-one-agent",
        email="agent@agency-one.example",
        password_hash=hash_password("ValidPass1!"),
        role=USER_ROLE_TENANT_SUPER_USER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def agency_two(db) -> Agency:
    clear_current_agency_id()
    agency = Agency(
        id=AGENCY_TWO_ID,
        name="Agency Two",
        slug="agency-two",
        organization_handle="agency-two",
        subscription_state=SUBSCRIPTION_STATE_ACTIVE,
        is_active=True,
    )
    db.add(agency)
    db.commit()
    db.refresh(agency)
    return agency


@pytest.fixture
def agency_one_group_inventory(db) -> AgencyGroupInventory:
    clear_current_agency_id()
    group = AgencyGroup(
        id=AGENCY_ONE_GROUP_ID,
        agency_id=AGENCY_ONE_ID,
        group_name="Agency One Block",
        cruise_line="Royal Caribbean International",
        ship_name="Oasis of the Seas",
        sailing_date=date(2027, 4, 1),
        disembarkation_date=date(2027, 4, 8),
        group_id_code="A1-BLOCK",
        tc_ratio="1:16",
        is_active=True,
    )
    inventory = AgencyGroupInventory(
        id=AGENCY_ONE_INVENTORY_ID,
        group_id=group.id,
        cabin_category="8C",
        cabin_type="Balcony",
        price_per_cabin=1200,
        cabins_allocated=10,
        cabins_reserved=0,
    )
    db.add_all([group, inventory])
    db.commit()
    db.refresh(inventory)
    return inventory


@pytest.fixture
def agency_one_task_template(db) -> AgencyTaskTemplate:
    clear_current_agency_id()
    template = AgencyWorkflowTemplate(
        id=AGENCY_ONE_WORKFLOW_ID,
        agency_id=AGENCY_ONE_ID,
        workflow_name="Agency One Workflow",
        description="Tenant isolation fixture",
    )
    task = AgencyTaskTemplate(
        id=AGENCY_ONE_TASK_ID,
        workflow_template_id=template.id,
        task_title="Research",
        sequence_order=1,
        action_type="manual_check",
    )
    db.add_all([template, task])
    db.commit()
    db.refresh(task)
    return task


@pytest.fixture
def agency_one_request_passenger(db, agency_one_user) -> tuple[TravelRequest, RequestPassenger]:
    clear_current_agency_id()
    set_current_agency_id(AGENCY_ONE_ID)
    request = TravelRequest(
        agency_id=AGENCY_ONE_ID,
        first_name="Jane",
        last_name="Cruiser",
        email="jane@agency-one.example",
        phone="5551234567",
        cruise_lines=["Royal Caribbean International"],
        destination="Caribbean",
        departure_date=date(2026, 6, 1),
        return_date=date(2026, 6, 8),
        cabin_types=["Balcony"],
        passengers=2,
        cabins_needed=1,
        status="Open",
        created_by_id=agency_one_user.id,
        updated_by_id=agency_one_user.id,
    )
    passenger = Passenger(
        agency_id=AGENCY_ONE_ID,
        first_name="Mary",
        last_name="Guest",
        email="mary@agency-one.example",
        phone="5559876543",
        is_active=True,
    )
    db.add_all([request, passenger])
    db.flush()
    link = attach_passenger_to_request(db, request.id, passenger.id)
    db.commit()
    db.refresh(request)
    db.refresh(link)
    return request, link


@pytest.fixture
def agency_two_travel_request(db, agency_two, agency_two_super_user) -> TravelRequest:
    clear_current_agency_id()
    request = TravelRequest(
        agency_id=AGENCY_TWO_ID,
        first_name="Bob",
        last_name="Tenant",
        email="bob@agency-two.example",
        phone="5550001111",
        cruise_lines=["Holland America Line"],
        destination="Alaska",
        departure_date=date(2026, 7, 1),
        return_date=date(2026, 7, 8),
        cabin_types=["Ocean View"],
        passengers=1,
        cabins_needed=1,
        status="Open",
        created_by_id=agency_two_super_user.id,
        updated_by_id=agency_two_super_user.id,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


@pytest.fixture
def agency_two_super_user(db, agency_two) -> User:
    user = User(
        agency_id=AGENCY_TWO_ID,
        username="agency-two-admin",
        email="admin@agency-two.example",
        password_hash=hash_password("ValidPass1!"),
        role=USER_ROLE_TENANT_SUPER_USER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def agency_two_auth_headers(client, agency_two_super_user):
    response = client.post(
        "/api/auth/login",
        json={
            "organization_handle": "agency-two",
            "username": agency_two_super_user.username,
            "password": "ValidPass1!",
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_agency_two_cannot_read_agency_one_group_inventory(db, agency_two, agency_one_group_inventory):
    set_current_agency_id(AGENCY_TWO_ID)

    _expect_not_found(
        lambda: get_agency_group_inventory_for_agency(db, agency_one_group_inventory.id, AGENCY_TWO_ID)
    )


def test_agency_two_cannot_load_agency_one_workflow_template(db, agency_two, agency_one_task_template):
    set_current_agency_id(AGENCY_TWO_ID)

    _expect_not_found(
        lambda: load_workflow_template(db, agency_one_task_template.workflow_template_id)
    )


def test_agency_two_cannot_read_agency_one_request_passenger_link(
    db,
    agency_two,
    agency_one_request_passenger,
):
    _, link = agency_one_request_passenger
    set_current_agency_id(AGENCY_TWO_ID)

    _expect_not_found(lambda: get_request_passenger_for_agency(db, link.id, AGENCY_TWO_ID))


def test_attach_passenger_rejects_cross_tenant_request(db, agency_two, agency_one_request_passenger):
    request, _ = agency_one_request_passenger
    set_current_agency_id(AGENCY_TWO_ID)
    other_passenger = Passenger(
        agency_id=AGENCY_TWO_ID,
        first_name="Eve",
        last_name="Outsider",
        email="eve@agency-two.example",
        phone="5552223333",
        is_active=True,
    )
    db.add(other_passenger)
    db.commit()

    _expect_not_found(lambda: attach_passenger_to_request(db, request.id, other_passenger.id))


def test_agency_one_context_can_read_own_request_passenger_link(db, agency_one_request_passenger):
    _, link = agency_one_request_passenger
    set_current_agency_id(AGENCY_ONE_ID)
    db.expire_all()

    found = get_request_passenger_for_agency(db, link.id, AGENCY_ONE_ID)

    assert found.id == link.id
    assert found.travel_request_id == link.travel_request_id


@pytest.mark.parametrize(
    ("method", "url", "json_body"),
    [
        (
            "patch",
            f"/api/agency-groups/inventory/{AGENCY_ONE_INVENTORY_ID}",
            {"cabins_allocated": 12},
        ),
        ("delete", f"/api/agency-groups/inventory/{AGENCY_ONE_INVENTORY_ID}", None),
    ],
)
def test_agency_two_api_cannot_mutate_agency_one_inventory(
    client,
    agency_two_auth_headers,
    agency_one_group_inventory,
    method,
    url,
    json_body,
):
    if json_body is None:
        response = getattr(client, method)(url, headers=agency_two_auth_headers)
    else:
        response = getattr(client, method)(url, headers=agency_two_auth_headers, json=json_body)

    assert response.status_code == 404


def test_agency_two_api_cannot_view_agency_one_group_detail(
    client,
    agency_two_auth_headers,
    agency_one_group_inventory,
):
    response = client.get(
        f"/api/agency-groups/{AGENCY_ONE_GROUP_ID}",
        headers=agency_two_auth_headers,
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("method", "url", "json_body"),
    [
        (
            "patch",
            f"/api/agency-workflow-templates/tasks/{AGENCY_ONE_TASK_ID}",
            {"task_title": "Hijacked Task"},
        ),
        ("delete", f"/api/agency-workflow-templates/tasks/{AGENCY_ONE_TASK_ID}", None),
    ],
)
def test_agency_two_api_cannot_mutate_agency_one_task_template(
    client,
    agency_two_auth_headers,
    agency_one_task_template,
    method,
    url,
    json_body,
):
    if json_body is None:
        response = getattr(client, method)(url, headers=agency_two_auth_headers)
    else:
        response = getattr(client, method)(url, headers=agency_two_auth_headers, json=json_body)

    assert response.status_code == 404


def test_agency_two_api_cannot_update_agency_one_workflow_template(
    client,
    agency_two_auth_headers,
    agency_one_task_template,
):
    response = client.patch(
        f"/api/agency-workflow-templates/{AGENCY_ONE_WORKFLOW_ID}",
        headers=agency_two_auth_headers,
        json={"workflow_name": "Hijacked Workflow"},
    )

    assert response.status_code == 404


def test_agency_two_api_cannot_update_agency_one_request_passenger_link(
    client,
    agency_two_auth_headers,
    agency_two_travel_request,
    agency_one_request_passenger,
):
    _, link = agency_one_request_passenger
    response = client.patch(
        f"/api/requests/{agency_two_travel_request.id}/passengers/{link.id}",
        headers=agency_two_auth_headers,
        json={"first_name": "Hijacked"},
    )

    assert response.status_code == 404


def test_agency_two_api_cannot_delete_agency_one_request_passenger_link(
    client,
    agency_two_auth_headers,
    agency_one_request_passenger,
):
    request, link = agency_one_request_passenger
    response = client.delete(
        f"/api/requests/{request.id}/passengers/{link.id}",
        headers=agency_two_auth_headers,
    )

    assert response.status_code == 404
