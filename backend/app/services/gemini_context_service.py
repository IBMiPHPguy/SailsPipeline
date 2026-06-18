from fastapi import HTTPException

from app.constants import PROPOSED_CRUISE_STATUS_PROPOSED
from app.models import ProposedCruise, TravelRequest


def build_request_context_for_gemini(request: TravelRequest) -> dict[str, object]:
    passenger_details = [
        {
            "name": f"{link.first_name} {link.last_name}".strip(),
            "email": link.email,
            "phone": link.phone,
            "qualifiers": link.qualifiers or [],
            "is_primary": link.is_primary,
        }
        for link in sorted(
            request.request_passengers,
            key=lambda item: (not item.is_primary, item.id),
        )
    ]
    aggregate_qualifiers: list[str] = []
    seen_qualifiers: set[str] = set()
    for passenger in passenger_details:
        for qualifier in passenger["qualifiers"]:
            if qualifier not in seen_qualifiers:
                seen_qualifiers.add(qualifier)
                aggregate_qualifiers.append(qualifier)

    return {
        "request_id": request.id,
        "client_name": f"{request.first_name} {request.last_name}".strip(),
        "client_first_name": request.first_name,
        "client_email": request.email,
        "cruise_line_preference": request.cruise_lines,
        "excluded_cruise_lines": request.excluded_cruise_lines,
        "destination": request.destination,
        "destination_details": request.destination_details,
        "departure_date": request.departure_date.isoformat(),
        "return_date": request.return_date.isoformat(),
        "cabin_types": request.cabin_types,
        "qualifiers": aggregate_qualifiers,
        "passenger_details": passenger_details,
        "passengers": request.passengers,
        "cabins_needed": request.cabins_needed,
    }


def proposed_cruise_label(cruise: ProposedCruise) -> str:
    return f"{cruise.cruise_line} · {cruise.ship} (departs {cruise.departure_date.isoformat()})"


def validate_proposed_cruises_for_proposal_email(cruises: list[ProposedCruise]) -> list[ProposedCruise]:
    proposed = [cruise for cruise in cruises if cruise.status == PROPOSED_CRUISE_STATUS_PROPOSED]
    issues: list[str] = []

    if not proposed:
        issues.append(
            "No proposed cruises in Proposed status were found. Add priced cruise options before drafting the email."
        )

    for cruise in proposed:
        label = proposed_cruise_label(cruise)
        if cruise.cost <= 0:
            issues.append(f"{label}: cruise cost must be greater than $0.")
        if cruise.deposit_amount <= 0:
            issues.append(f"{label}: deposit amount must be greater than $0.")

    if issues:
        raise HTTPException(status_code=400, detail=" ".join(issues))

    return proposed


def proposed_cruise_to_gemini_dict(cruise: ProposedCruise, option_number: int) -> dict[str, object]:
    return {
        "option_number": option_number,
        "departure_date": cruise.departure_date.isoformat(),
        "cruise_line": cruise.cruise_line,
        "ship": cruise.ship,
        "number_of_nights": cruise.number_of_nights,
        "itinerary_name": cruise.itinerary_name,
        "itinerary_details": cruise.itinerary_details,
        "room_category": cruise.room_category,
        "room_number": cruise.room_number,
        "passengers_in_room": cruise.passengers_in_room,
        "deposit_amount": str(cruise.deposit_amount),
        "deposit_due_date": cruise.deposit_due_date.isoformat(),
        "final_payment_due_date": cruise.final_payment_due_date.isoformat(),
        "cost": str(cruise.cost),
        "includes": cruise.includes or {},
    }
