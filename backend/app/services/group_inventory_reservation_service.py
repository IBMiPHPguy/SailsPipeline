"""Reserve group block inventory when a linked request closes as purchased."""

from __future__ import annotations

from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.models import AgencyGroupInventory, TravelRequest
from app.services.agency_group_service import compute_cabins_remaining, get_agency_group_inventory_for_agency


class GroupInventoryReservationError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def build_group_inventory_reservation_increments(request: TravelRequest) -> dict[str, int]:
    increments: dict[str, int] = defaultdict(int)

    if request.group_bookings:
        for booking in request.group_bookings:
            cabins = max(1, int(booking.cabins_requested))
            increments[booking.group_inventory_id] += cabins
        return dict(increments)

    if request.group_inventory_id:
        cabins = max(1, int(request.cabins_needed or 1))
        increments[request.group_inventory_id] = cabins

    return dict(increments)


def apply_group_inventory_reservation_on_purchase(
    db: Session,
    *,
    request: TravelRequest,
    agency_id: str,
) -> None:
    if request.group_inventory_reservation_applied:
        return

    increments = build_group_inventory_reservation_increments(request)
    if not increments:
        return

    for inventory_id, cabins_to_reserve in increments.items():
        inventory = (
            db.query(AgencyGroupInventory)
            .filter(AgencyGroupInventory.id == inventory_id)
            .with_for_update()
            .one_or_none()
        )
        if inventory is None:
            raise GroupInventoryReservationError("Linked group inventory was not found.")

        get_agency_group_inventory_for_agency(db, inventory_id, agency_id)

        remaining = compute_cabins_remaining(
            cabins_allocated=inventory.cabins_allocated,
            cabins_reserved=inventory.cabins_reserved,
        )
        if cabins_to_reserve > remaining:
            raise GroupInventoryReservationError(
                f"Only {remaining} cabins remain for {inventory.cabin_category}."
            )

        inventory.cabins_reserved = int(inventory.cabins_reserved) + cabins_to_reserve

    request.group_inventory_reservation_applied = True


def load_request_for_group_inventory_reservation(db: Session, request_id: int) -> TravelRequest:
    return (
        db.query(TravelRequest)
        .options(selectinload(TravelRequest.group_bookings))
        .filter(TravelRequest.id == request_id)
        .one()
    )


def maybe_apply_group_inventory_reservation_on_purchase(
    db: Session,
    *,
    request_id: int,
    agency_id: str,
    next_status: str,
    next_close_reason: str | None,
) -> None:
    from app.constants import PRIMARY_CLOSE_REASON, REQUEST_STATUS_CLOSED

    if next_status != REQUEST_STATUS_CLOSED or next_close_reason != PRIMARY_CLOSE_REASON:
        return

    request = load_request_for_group_inventory_reservation(db, request_id)
    try:
        apply_group_inventory_reservation_on_purchase(db, request=request, agency_id=agency_id)
    except GroupInventoryReservationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
