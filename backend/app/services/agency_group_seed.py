"""Seed representative agency group shells for development and tests."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.models import Agency, AgencyGroup, AgencyGroupInventory

SEED_GROUP_NAME = "Caribbean Alumni Block 2027"


def _new_id() -> str:
    return str(uuid.uuid4())


def seed_agency_groups(db: Session, agency_id: str) -> AgencyGroup | None:
    agency = db.get(Agency, agency_id)
    if agency is None:
        return None

    existing = (
        db.query(AgencyGroup)
        .filter(
            AgencyGroup.agency_id == agency_id,
            AgencyGroup.group_name == SEED_GROUP_NAME,
        )
        .first()
    )
    if existing is not None:
        return existing

    group = AgencyGroup(
        id=_new_id(),
        agency_id=agency_id,
        group_name=SEED_GROUP_NAME,
        cruise_line="Royal Caribbean International",
        ship_name="Symphony of the Seas",
        sailing_date=date(2027, 3, 14),
        disembarkation_date=date(2027, 3, 21),
        group_id_code="RCG-ALUM-2027",
        group_amenities=(
            "Welcome cocktail party for the group\n"
            "GAP cocktail reception on embarkation day\n"
            "Dedicated group dining on formal night\n"
            "Onboard credit: $50 per stateroom"
        ),
        tc_ratio="1:16",
        is_active=True,
    )
    db.add(group)
    db.flush()

    inventory_rows = [
        {
            "cabin_category": "4D",
            "cabin_type": "Interior",
            "cabin_description": "Interior stateroom, forward/midship",
            "price_per_cabin": 899.00,
            "deposit_per_cabin": 150.00,
            "cabins_allocated": 12,
        },
        {
            "cabin_category": "8C",
            "cabin_type": "Balcony",
            "cabin_description": "Spacious balcony overlooking the ocean",
            "price_per_cabin": 1299.00,
            "deposit_per_cabin": 200.00,
            "cabins_allocated": 20,
        },
        {
            "cabin_category": "V1",
            "cabin_type": "Suite",
            "cabin_description": "Grand suite with priority boarding perks",
            "price_per_cabin": 2499.00,
            "deposit_per_cabin": 500.00,
            "cabins_allocated": 4,
        },
    ]
    for row in inventory_rows:
        db.add(
            AgencyGroupInventory(
                id=_new_id(),
                group_id=group.id,
                cabin_category=row["cabin_category"],
                cabin_type=row["cabin_type"],
                cabin_description=row["cabin_description"],
                price_per_cabin=row["price_per_cabin"],
                deposit_per_cabin=row["deposit_per_cabin"],
                cabins_allocated=row["cabins_allocated"],
                cabins_reserved=0,
            )
        )

    db.flush()
    return group


def seed_all_agency_groups(db: Session) -> None:
    agency_ids = [row.id for row in db.query(Agency.id).all()]
    for agency_id in agency_ids:
        seed_agency_groups(db, agency_id)
