from app.security import hash_password
from app.services.bridge_launch_service import (
    BridgeLaunchError,
    bootstrap_platform_operator,
    count_platform_operators,
    run_bridge_launch,
)
from app.tenant_roles import USER_ROLE_PLATFORM_SUPER_ADMIN


def test_bootstrap_platform_operator_creates_first_operator(db):
    user, created = bootstrap_platform_operator(
        db,
        username="bridge.ops",
        email="bridge@sailspipeline.com",
        password="BridgePass1!",
    )

    assert created is True
    assert user.role == USER_ROLE_PLATFORM_SUPER_ADMIN
    assert user.agency_id is None
    assert count_platform_operators(db) == 1


def test_bootstrap_platform_operator_is_idempotent_for_same_username(db):
    bootstrap_platform_operator(
        db,
        username="bridge.ops",
        email="bridge@sailspipeline.com",
        password="BridgePass1!",
    )

    user, created = bootstrap_platform_operator(
        db,
        username="bridge.ops",
        email="bridge.updated@sailspipeline.com",
        password="BridgePass1!",
    )

    assert created is False
    assert user.email == "bridge.updated@sailspipeline.com"


def test_bootstrap_platform_operator_rejects_second_distinct_operator(db):
    bootstrap_platform_operator(
        db,
        username="bridge.ops",
        email="bridge@sailspipeline.com",
        password="BridgePass1!",
    )

    try:
        bootstrap_platform_operator(
            db,
            username="other.bridge",
            email="other@sailspipeline.com",
            password="BridgePass1!",
        )
        raised = False
    except BridgeLaunchError:
        raised = True

    assert raised is True


def test_run_bridge_launch_check_only(db):
    report = run_bridge_launch(
        db,
        username="bridge.ops",
        email="bridge@sailspipeline.com",
        password="BridgePass1!",
        check_only=True,
        public_registration_enabled=False,
    )

    assert report.schema_ready is True
    assert report.platform_operator_count == 0
