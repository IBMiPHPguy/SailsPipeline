from __future__ import annotations


def render_insurance_waiver_text(*, agency_name: str, passenger_name: str) -> str:
    _ = (agency_name, passenger_name)

    return """IMPORTANT LEGAL DOCUMENT: DECLINATION OF TRAVEL PROTECTION AND LIABILITY WAIVER

This Travel Insurance Waiver ("Waiver") is a legally binding contract between the undersigned traveler, on behalf of themselves and all accompanying members of their traveling party (collectively referred to as "the Client"), and the booking travel agency ("the Agency").

Section 1: Explicit Offer and Importance of Travel Protection
The Client acknowledges that the Agency has strongly recommended the purchase of comprehensive travel protection and trip cancellation insurance. The Client understands that travel insurance offers vital protection against unforeseen circumstances, including but not limited to: trip cancellations, severe trip interruptions, missed port connections, travel delays, lost or delayed baggage, emergency medical evacuations, and illness or injury sustained while outside the United States.

Section 2: Comprehensive Risk Assumption and Forfeiture of Funds
By executing this Waiver, the Client acknowledges that cruise lines, airlines, tour operators, and other third-party travel suppliers enforce extremely strict, non-negotiable cancellation schedules and financial penalties. In the event of a cancellation, modification, or interruption of the scheduled itinerary for any reason—including personal medical emergencies, family crises, or global events—the Client accepts sole and absolute financial responsibility for all non-refundable deposits, prepaid fares, change fees, and cancellation penalties.

Section 3: Supplier Autonomy and Itinerary Changes
The Client recognizes that the booked Cruise Line retains the absolute legal right to alter itineraries, bypass scheduled ports of call, substitute vessels, or cancel sailings at its sole discretion. The Client agrees that the Agency bears no financial liability or operational responsibility for supplier schedule adjustments, mechanical failures, or cancellations, and that travel insurance is the exclusive mechanism available to recoup related losses.

Section 4: Medical and Evacuation Costs Disclaimer
The Client explicitly understands that standard domestic health insurance policies, including Medicare, rarely provide comprehensive coverage outside the United States or onboard international cruise vessels. The Client assumes full financial liability for any medical expenses, doctor fees, hospitalizations, or multi-thousand-dollar emergency maritime evacuations required during the course of travel.

Section 5: Indemnification and Release of Liability
The Client hereby releases, waives, and forever discharges the Agency, its officers, employees, and independent contractors from any and all claims, demands, actions, or financial losses arising out of or related to trip disruptions, injuries, medical emergencies, or supplier defaults. The Client agrees to indemnify and hold harmless the Agency against any expenses incurred due to the Client's decision to travel without adequate protection.

Section 6: Continuous Effect and Governing Law
This Waiver applies explicitly to the current travel request and remains legally active for any modifications, extensions, or subsequent segments attached to this booking. This Agreement shall be governed by, construed, and enforced in accordance with the laws of the state where the Agency's primary business operations are legally registered, without regard to conflict of law principles."""
