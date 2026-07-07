import json
import re
from datetime import date
from decimal import Decimal
from typing import Any

import google.generativeai as genai
from pydantic import ValidationError

from app.schemas import ProposedCruiseCreate, ProposedCruiseIncludes


class GeminiConfigurationError(Exception):
    pass


class GeminiParseError(Exception):
    pass


def _default_includes() -> dict[str, Any]:
    return ProposedCruiseIncludes().model_dump()


_DATE_PLACEHOLDERS = frozenset({"", "tbd", "n/a", "na", "unknown", "null", "none", "-", "—"})


def _is_missing_date_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in _DATE_PLACEHOLDERS
    return False


def _coerce_date(value: Any, fallback: date | None = None) -> date:
    if isinstance(value, date):
        return value
    if not _is_missing_date_value(value) and isinstance(value, str):
        cleaned = value.strip()[:10]
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", cleaned):
            return date.fromisoformat(cleaned)
    if fallback is not None:
        return fallback
    raise ValueError("A valid date is required.")


def _coerce_decimal(value: Any, default: str = "0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    cleaned = str(value).strip().replace("$", "").replace(",", "")
    if not cleaned:
        return Decimal(default)
    return Decimal(cleaned)


def _normalize_includes(raw: Any) -> dict[str, Any]:
    base = _default_includes()
    if not isinstance(raw, dict):
        return base

    for key in ("drink_package", "wifi", "specialty_dining"):
        item = raw.get(key)
        if isinstance(item, dict):
            base[key]["included"] = bool(item.get("included", False))
            name = item.get("name")
            base[key]["name"] = str(name).strip() if name else None

    for key in ("excursion_credit", "onboard_credit", "gift_obc"):
        item = raw.get(key)
        if isinstance(item, dict):
            base[key]["included"] = bool(item.get("included", False))
            amount = item.get("amount")
            base[key]["amount"] = _coerce_decimal(amount) if amount not in (None, "") else None

    if "tips" in raw:
        base["tips"] = bool(raw["tips"])
    if "excursion" in raw:
        base["excursion"] = bool(raw["excursion"])

    return base


def _normalize_cruise_payload(
    raw: dict[str, Any],
    *,
    request_context: dict[str, Any],
) -> dict[str, Any]:
    fallback_departure = None
    fallback_return = None
    if request_context.get("departure_date"):
        fallback_departure = date.fromisoformat(str(request_context["departure_date"])[:10])
    if request_context.get("return_date"):
        fallback_return = date.fromisoformat(str(request_context["return_date"])[:10])

    departure_date = _coerce_date(raw.get("departure_date"), fallback_departure)
    deposit_due = _coerce_date(raw.get("deposit_due_date"), departure_date)
    final_due = _coerce_date(
        raw.get("final_payment_due_date"),
        fallback_return or deposit_due,
    )
    if final_due < deposit_due:
        final_due = deposit_due

    room_number = str(raw.get("room_number") or "TBD").strip() or "TBD"
    passengers_in_room = int(raw.get("passengers_in_room") or request_context.get("passengers") or 2)

    preference = request_context.get("cruise_line_preference")
    if isinstance(preference, list):
        cruise_line_default = preference[0] if preference else "TBD"
    else:
        cruise_line_default = str(preference or "TBD")

    return {
        "departure_date": departure_date,
        "cruise_line": str(raw.get("cruise_line") or cruise_line_default).strip()[:120],
        "ship": str(raw.get("ship") or "TBD").strip()[:120],
        "number_of_nights": max(1, int(raw.get("number_of_nights") or 7)),
        "itinerary_name": str(raw.get("itinerary_name") or raw.get("itinerary") or "TBD").strip()[:160],
        "room_category": str(raw.get("room_category") or "TBD").strip()[:120],
        "room_number": room_number[:40],
        "passengers_in_room": max(1, passengers_in_room),
        "deposit_amount": _coerce_decimal(raw.get("deposit_amount")),
        "deposit_due_date": deposit_due,
        "final_payment_due_date": final_due,
        "cost": _coerce_decimal(raw.get("cost")),
        "includes": _normalize_includes(raw.get("includes")),
        "passenger_ids": raw.get("passenger_ids") or [],
    }


def _build_prompt(research_text: str, request_context: dict[str, Any]) -> str:
    return f"""You extract structured proposed cruise options from agency research notes.

Travel request context (use to fill gaps and stay consistent):
{json.dumps(request_context, indent=2, default=str)}

Research document:
{research_text}

Return JSON only, with this exact shape:
{{
  "cruises": [
    {{
      "departure_date": "YYYY-MM-DD",
      "cruise_line": "string",
      "ship": "string",
      "number_of_nights": 7,
      "itinerary_name": "string",
      "room_category": "string",
      "room_number": "string",
      "passengers_in_room": 2,
      "deposit_amount": 0,
      "deposit_due_date": "YYYY-MM-DD",
      "final_payment_due_date": "YYYY-MM-DD",
      "cost": 0,
      "includes": {{
        "drink_package": {{"included": false, "name": null}},
        "wifi": {{"included": false, "name": null}},
        "specialty_dining": {{"included": false, "name": null}},
        "tips": false,
        "excursion": false,
        "excursion_credit": {{"included": false, "amount": null}},
        "onboard_credit": {{"included": false, "amount": null}},
        "gift_obc": {{"included": false, "amount": null}}
      }}
    }}
  ]
}}

Rules:
- Include every distinct cruise option found in the research document.
- Use ISO dates (YYYY-MM-DD) for all date fields. Never use "TBD" for dates.
- If a cruise date is missing, use the request departure_date or return_date from context.
- Use "TBD" only for unknown room numbers.
- Amounts are USD numbers without currency symbols.
- Do not include passenger names or ids.
"""


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def generate_proposed_cruises_from_research(
    *,
    api_key: str,
    model_name: str,
    research_text: str,
    request_context: dict[str, Any],
) -> tuple[list[ProposedCruiseCreate], str]:
    if not api_key.strip():
        raise GeminiConfigurationError("Gemini API key is not configured.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    prompt = _build_prompt(research_text, request_context)

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
    except Exception as exc:
        raise GeminiParseError(f"Gemini request failed: {exc}") from exc

    response_text = getattr(response, "text", None) or ""
    if not response_text.strip():
        raise GeminiParseError("Gemini returned an empty response.")

    try:
        payload = _extract_json(response_text)
    except json.JSONDecodeError as exc:
        raise GeminiParseError("Gemini returned invalid JSON.") from exc

    raw_cruises = payload.get("cruises")
    if not isinstance(raw_cruises, list) or not raw_cruises:
        raise GeminiParseError("No proposed cruises were found in the research document.")

    cruises: list[ProposedCruiseCreate] = []
    errors: list[str] = []

    for index, raw in enumerate(raw_cruises, start=1):
        if not isinstance(raw, dict):
            errors.append(f"Option {index} was not an object.")
            continue
        try:
            normalized = _normalize_cruise_payload(raw, request_context=request_context)
            cruises.append(ProposedCruiseCreate.model_validate(normalized))
        except (ValidationError, ValueError, TypeError) as exc:
            errors.append(f"Option {index}: {exc}")

    if not cruises:
        detail = "; ".join(errors) if errors else "No valid cruise options could be parsed."
        raise GeminiParseError(detail)

    return cruises, model_name


def _build_proposal_email_prompt(
    request_context: dict[str, Any],
    proposed_cruises: list[dict[str, Any]],
) -> str:
    return f"""You write client-facing cruise proposal emails for a travel agency.

Travel request context:
{json.dumps(request_context, indent=2, default=str)}

Proposed cruise options to include (present every option clearly):
{json.dumps(proposed_cruises, indent=2, default=str)}

Return JSON only with this exact shape:
{{
  "email_subject": "string",
  "intro": "string",
  "closing": "string"
}}

Rules:
- email_subject is the client-facing email subject line (concise and specific to the proposal).
- intro is 1-2 warm, professional paragraphs greeting the client by first name when available in client_name, summarizing the research, and introducing the options below. Plain text only.
- closing is 1 short paragraph inviting questions and a reply with their preferred option. Plain text only.
- Do not write cruise option details, pricing, or itinerary content in intro or closing. Those appear in the formatted email layout separately.
- Do not include HTML or markdown in intro or closing.
- Do not invent cruise options beyond what is provided.
- Do not include internal ids or passenger ids.
"""


def generate_research_communication_from_proposals(
    *,
    api_key: str,
    model_name: str,
    request_context: dict[str, Any],
    proposed_cruises: list[dict[str, Any]],
) -> tuple[str, str, str, str]:
    if not api_key.strip():
        raise GeminiConfigurationError("Gemini API key is not configured.")
    if not proposed_cruises:
        raise GeminiParseError("No proposed cruises were provided.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    prompt = _build_proposal_email_prompt(request_context, proposed_cruises)

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.4,
            ),
        )
    except Exception as exc:
        raise GeminiParseError(f"Gemini request failed: {exc}") from exc

    response_text = getattr(response, "text", None) or ""
    if not response_text.strip():
        raise GeminiParseError("Gemini returned an empty response.")

    try:
        payload = _extract_json(response_text)
    except json.JSONDecodeError as exc:
        raise GeminiParseError("Gemini returned invalid JSON.") from exc

    email_subject = str(payload.get("email_subject") or payload.get("subject") or "").strip()
    intro = str(payload.get("intro") or payload.get("greeting") or "").strip()
    closing = str(payload.get("closing") or payload.get("sign_off") or "").strip()

    if not email_subject:
        raise GeminiParseError("Gemini returned an empty email subject.")
    if not intro:
        raise GeminiParseError("Gemini returned an empty intro.")
    if not closing:
        raise GeminiParseError("Gemini returned an empty closing.")

    return email_subject, intro, closing, model_name


_COMMUNICATION_KIND_LABELS = {
    "transcripts": "call transcript",
    "chats": "chat log",
}

_MAX_COMMUNICATION_CHARS = 80_000


def _truncate_communication_text(text: str) -> str:
    cleaned = text.strip()
    if len(cleaned) <= _MAX_COMMUNICATION_CHARS:
        return cleaned
    return (
        f"{cleaned[:_MAX_COMMUNICATION_CHARS]}\n\n"
        "[Communication truncated for AI processing due to length.]"
    )


def _build_communication_summary_prompt(
    *,
    communication_kind: str,
    filename: str,
    communication_text: str,
    request_context: dict[str, Any],
) -> str:
    kind_label = _COMMUNICATION_KIND_LABELS.get(communication_kind, "communication")
    return f"""You analyze travel-agency client communications and produce CRM notes for cruise advisors.

Communication type: {kind_label}
Source file: {filename}

Travel request context (use to connect details and avoid contradicting known facts):
{json.dumps(request_context, indent=2, default=str)}

Communication content:
{communication_text}

Return JSON only with this exact shape:
{{
  "summary": "string",
  "research_brief": "string"
}}

Rules for summary:
- Write 2-4 concise sentences in plain language for the advisor.
- Capture who said what that matters: preferences, objections, pricing discussed, dates, ships/itineraries, and scheduling.
- Mention explicit follow-ups or next steps (calls, deadlines, documents needed).
- Do not invent facts that are not supported by the communication or request context.

Rules for research_brief:
- Markdown bullet list (use - bullets) aimed at the research/proposal workflow.
- Include sections only when there is content: Client preferences, Constraints, Budget/pricing signals, Ships/itineraries mentioned, Follow-up actions.
- Pull out concrete facts (dates, prices, cabin types, promotions, locations) when present.
- Flag open questions the advisor still needs to answer.
- Keep it scannable and actionable; no filler.
"""


def generate_communication_ai_summary(
    *,
    api_key: str,
    model_name: str,
    communication_kind: str,
    filename: str,
    communication_text: str,
    request_context: dict[str, Any],
) -> tuple[str, str]:
    if not api_key.strip():
        raise GeminiConfigurationError("Gemini API key is not configured.")

    cleaned_text = _truncate_communication_text(communication_text)
    if not cleaned_text:
        raise GeminiParseError("Communication content is empty.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    prompt = _build_communication_summary_prompt(
        communication_kind=communication_kind,
        filename=filename,
        communication_text=cleaned_text,
        request_context=request_context,
    )

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )
    except Exception as exc:
        raise GeminiParseError(f"Gemini request failed: {exc}") from exc

    response_text = getattr(response, "text", None) or ""
    if not response_text.strip():
        raise GeminiParseError("Gemini returned an empty response.")

    try:
        payload = _extract_json(response_text)
    except json.JSONDecodeError as exc:
        raise GeminiParseError("Gemini returned invalid JSON.") from exc

    summary = str(payload.get("summary") or "").strip()
    research_brief = str(payload.get("research_brief") or "").strip()

    if not summary:
        raise GeminiParseError("Gemini returned an empty summary.")
    if not research_brief:
        raise GeminiParseError("Gemini returned an empty research brief.")

    return summary, research_brief


def generate_sales_analytics_copilot_answer(
    *,
    api_key: str,
    model_name: str,
    question: str,
    analytics_context: dict,
) -> str:
    if not api_key.strip():
        raise GeminiConfigurationError("Gemini API key is not configured.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    prompt = (
        "You are First Mate, a concise sales analytics copilot for a cruise travel agency CRM called SailsPipeline. "
        "Answer in 2-4 short sentences using only the provided analytics JSON. "
        "Be specific with numbers and percentages when available. "
        "Do not invent data.\n\n"
        f"Question: {question.strip()}\n\n"
        f"Analytics JSON:\n{json.dumps(analytics_context, default=str)}"
    )

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(temperature=0.35),
        )
    except Exception as exc:
        raise GeminiParseError(f"Gemini request failed: {exc}") from exc

    answer = (getattr(response, "text", None) or "").strip()
    if not answer:
        raise GeminiParseError("Gemini returned an empty response.")
    return answer
