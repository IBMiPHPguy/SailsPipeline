"""Diagnose proposed-cruise PATCH failures for a travel request.

Usage (inside the backend container):
  python scripts/diagnose_proposed_cruise_patch.py --request-id 8
  python scripts/diagnose_proposed_cruise_patch.py --request-id 8 --cruise-id 12

Optional auth (otherwise uses SEED_ADMIN_* / first tenant super-user):
  --organization-handle default --username admin --password '...'
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import ProposedCruise, TravelRequest, User
from app.schemas import ProposedCruiseUpdate
from app.services.proposed_cruise_record_service import update_proposed_cruise
from app.tenant_context import set_current_agency_id


def _build_round_trip_payload(cruise: ProposedCruise, cabins_needed: int) -> dict[str, Any]:
    from app.services.proposed_cruise_service import proposed_cruise_to_read

    read_model = proposed_cruise_to_read(cruise, cabins_needed)
    payload = read_model.model_dump(mode="json")
    payload.pop("id", None)
    payload.pop("created_by", None)
    payload.pop("updated_by", None)
    payload.pop("created_at", None)
    payload.pop("updated_at", None)
    payload.pop("passengers", None)
    payload.pop("room_passengers", None)

    room_passenger_ids = [
        [passenger.id for passenger in room] for room in read_model.room_passengers
    ]
    payload["room_passenger_ids"] = room_passenger_ids
    payload["passenger_ids"] = [pid for room in room_passenger_ids for pid in room]
    return payload


def _resolve_actor(db: Session, agency_id: str) -> User:
    user = (
        db.query(User)
        .filter(User.agency_id == agency_id, User.is_active.is_(True))
        .order_by(User.id.asc())
        .first()
    )
    if user is None:
        raise RuntimeError(f"No active user found for agency {agency_id}")
    return user


def diagnose_request(*, request_id: int, cruise_id: int | None) -> int:
    ok = True
    with SessionLocal() as db:
        request = db.get(TravelRequest, request_id)
        if request is None:
            print(f"FAIL — travel request {request_id} not found")
            return 1

        set_current_agency_id(request.agency_id)
        actor = _resolve_actor(db, request.agency_id)

        cruises = (
            db.query(ProposedCruise)
            .filter(ProposedCruise.travel_request_id == request_id)
            .order_by(ProposedCruise.id.asc())
            .all()
        )
        if cruise_id is not None:
            cruises = [cruise for cruise in cruises if cruise.id == cruise_id]

        if not cruises:
            print(f"No proposed cruises found for request {request_id}")
            return 1

        print(f"Request {request_id} — agency {request.agency_id} — cabins_needed {request.cabins_needed}")
        print(f"Actor: {actor.username} (id {actor.id})")
        print()

        for cruise in cruises:
            print(f"Cruise {cruise.id} — {cruise.cruise_line} / {cruise.ship} — status {cruise.status}")
            payload_dict = _build_round_trip_payload(cruise, request.cabins_needed)

            try:
                validated = ProposedCruiseUpdate.model_validate(payload_dict)
                print("  [OK] ProposedCruiseUpdate schema validation")
            except Exception as exc:
                ok = False
                print(f"  [FAIL] ProposedCruiseUpdate schema validation: {exc}")
                continue

            try:
                update_proposed_cruise(
                    db,
                    request_id=request_id,
                    cruise_id=cruise.id,
                    payload=validated,
                    current_user=actor,
                )
                db.rollback()
                print("  [OK] update_proposed_cruise (rolled back)")
            except Exception as exc:
                ok = False
                print(f"  [FAIL] update_proposed_cruise: {exc}")

            cruise_line = payload_dict.get("cruise_line")
            if cruise_line:
                from app.constants import CRUISE_LINES
                from app.schemas import normalize_cruise_line_value

                normalized = normalize_cruise_line_value(str(cruise_line))
                if normalized not in CRUISE_LINES:
                    print(
                        f"  [WARN] cruise_line {cruise_line!r} is not in CRUISE_LINES "
                        f"(normalized: {normalized!r})"
                    )

            passenger_ids = [
                pid for room in payload_dict.get("room_passenger_ids", []) for pid in room
            ]
            if passenger_ids:
                from app.models import RequestPassenger

                valid_ids = {
                    row.id
                    for row in db.query(RequestPassenger)
                    .filter(RequestPassenger.travel_request_id == request_id)
                    .all()
                }
                invalid = [pid for pid in passenger_ids if pid not in valid_ids]
                if invalid:
                    ok = False
                    print(f"  [FAIL] stale passenger IDs on cruise: {invalid}")

            print()

    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-id", type=int, required=True)
    parser.add_argument("--cruise-id", type=int, default=None)
    args = parser.parse_args()

    os.environ.setdefault("APP_ENV", os.environ.get("APP_ENV", "production"))
    return diagnose_request(request_id=args.request_id, cruise_id=args.cruise_id)


if __name__ == "__main__":
    sys.exit(main())
