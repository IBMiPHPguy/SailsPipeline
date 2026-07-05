import json
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import RequestPassenger, RequestPassengerAudit, TravelRequest, TravelRequestAudit, User

TRAVEL_REQUEST_AUDIT_FIELDS = (
    "first_name",
    "last_name",
    "email",
    "phone",
    "cruise_lines",
    "excluded_cruise_lines",
    "destination",
    "destination_details",
    "departure_date",
    "return_date",
    "cabin_types",
    "passengers",
    "cabins_needed",
    "cabin_hold_reservation_ids",
    "status",
    "close_reason",
    "lead_source",
    "referral_source_name",
    "marketing_campaign_id",
    "intake_mode",
    "intake_social_platform",
    "ship_name",
    "group_id",
    "group_inventory_id",
)

PASSENGER_AUDIT_FIELDS = (
    "first_name",
    "last_name",
    "email",
    "phone",
    "date_of_birth",
    "address_line_1",
    "address_line_2",
    "city",
    "state_or_province",
    "postal_code",
    "country",
    "qualifiers",
    "has_annual_insurance",
    "annual_insurance_expires_at",
    "annual_insurance_policy_number",
)


def passenger_name_label(passenger: RequestPassenger) -> str:
    return f"{passenger.first_name} {passenger.last_name}".strip()


def serialize_audit_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def values_differ(old_value: Any, new_value: Any) -> bool:
    return serialize_audit_value(old_value) != serialize_audit_value(new_value)


def record_travel_request_field_changes(
    db: Session,
    request: TravelRequest,
    field_changes: dict[str, tuple[Any, Any]],
    current_user: User,
) -> None:
    for field_name, (from_value, to_value) in field_changes.items():
        if not values_differ(from_value, to_value):
            continue
        db.add(
            TravelRequestAudit(
                travel_request_id=request.id,
                field_name=field_name,
                from_value=serialize_audit_value(from_value),
                to_value=serialize_audit_value(to_value),
                changed_by_id=current_user.id,
            )
        )


def record_passenger_field_changes(
    db: Session,
    passenger: RequestPassenger,
    field_changes: dict[str, tuple[Any, Any]],
    current_user: User,
) -> None:
    label = passenger_name_label(passenger)
    for field_name, (from_value, to_value) in field_changes.items():
        if not values_differ(from_value, to_value):
            continue
        db.add(
            RequestPassengerAudit(
                travel_request_id=passenger.travel_request_id,
                request_passenger_id=passenger.id,
                passenger_label=label,
                field_name=field_name,
                from_value=serialize_audit_value(from_value),
                to_value=serialize_audit_value(to_value),
                changed_by_id=current_user.id,
            )
        )


def collect_field_changes(
    entity: Any,
    updates: dict[str, Any],
    fields: tuple[str, ...],
) -> dict[str, tuple[Any, Any]]:
    changes: dict[str, tuple[Any, Any]] = {}
    for field_name in fields:
        if field_name not in updates:
            continue
        old_value = getattr(entity, field_name)
        new_value = updates[field_name]
        if values_differ(old_value, new_value):
            changes[field_name] = (old_value, new_value)
    return changes


def apply_updates(entity: Any, updates: dict[str, Any]) -> None:
    for field_name, value in updates.items():
        setattr(entity, field_name, value)


def record_passenger_deletion(
    db: Session,
    passenger: RequestPassenger,
    current_user: User,
) -> None:
    label = passenger_name_label(passenger)
    passenger_label = f"{label} (#{passenger.id})"
    db.add(
        RequestPassengerAudit(
            travel_request_id=passenger.travel_request_id,
            request_passenger_id=passenger.id,
            passenger_label=label,
            field_name="passenger_removed",
            from_value=passenger_label,
            to_value=None,
            changed_by_id=current_user.id,
        )
    )
    for field_name in PASSENGER_AUDIT_FIELDS:
        from_value = getattr(passenger, field_name)
        if from_value is None:
            continue
        db.add(
            RequestPassengerAudit(
                travel_request_id=passenger.travel_request_id,
                request_passenger_id=passenger.id,
                passenger_label=label,
                field_name=field_name,
                from_value=serialize_audit_value(from_value),
                to_value=None,
                changed_by_id=current_user.id,
            )
        )
