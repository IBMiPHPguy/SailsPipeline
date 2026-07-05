from sqlalchemy.orm import Session

from app.gemini_service import (
    GeminiConfigurationError,
    GeminiParseError,
    generate_sales_analytics_copilot_answer,
)
from app.schemas import SalesAnalyticsResponse
from app.services.gemini_config_service import resolve_gemini_credentials, uses_tenant_gemini_api_key


def _build_analytics_context(analytics: SalesAnalyticsResponse) -> dict:
    top_months = sorted(
        analytics.commission_timeline,
        key=lambda item: item.total_commission,
        reverse=True,
    )[:6]
    return {
        "win_rate_percent": analytics.win_rate_percent,
        "total_commission_forecast": analytics.total_commission_forecast,
        "funnel": [stage.model_dump() for stage in analytics.funnel_stages],
        "top_commission_months": [month.model_dump() for month in top_months if month.total_commission > 0],
        "rejection_reasons": [reason.model_dump() for reason in analytics.rejection_reasons[:8]],
        "cruise_line_shares": [share.model_dump() for share in analytics.cruise_line_shares[:8]],
    }


def _fallback_answer(question: str, analytics: SalesAnalyticsResponse) -> str:
    import json

    normalized = question.lower()
    context = _build_analytics_context(analytics)

    if "high-value" in normalized or "premium" in normalized:
        top_lines = ", ".join(
            share.cruise_line for share in analytics.cruise_line_shares[:3]
        ) or "No booked cruise lines yet"
        return (
            f"You have {analytics.funnel_stages[0].count if analytics.funnel_stages else 0} active leads and "
            f"{analytics.funnel_stages[3].count if len(analytics.funnel_stages) > 3 else 0} accepted bookings. "
            f"Top booked partners right now: {top_lines}. "
            f"Projected booked commission is ${analytics.total_commission_forecast:,.2f}."
        )

    if "bottleneck" in normalized or "pipeline" in normalized:
        funnel = " → ".join(f"{stage.label}: {stage.count}" for stage in analytics.funnel_stages)
        pending = next((stage.count for stage in analytics.funnel_stages if stage.label == "Proposals pending"), 0)
        return (
            f"Pipeline funnel: {funnel}. "
            f"{'Proposals pending review is the largest friction point.' if pending else 'Most leads are still before the proposal stage.'} "
            f"Win rate across closed requests and open bookings is {analytics.win_rate_percent if analytics.win_rate_percent is not None else 'not available yet'}%."
        )

    if "reject" in normalized or "lost" in normalized:
        if not analytics.rejection_reasons:
            return "No rejected quotes or lost-close reasons recorded yet."
        reasons = "; ".join(
            f"{item.segment}: {item.reason} ({item.count})" for item in analytics.rejection_reasons[:8]
        )
        return f"Top quote rejection drivers: {reasons}."

    if "commission" in normalized or "cash" in normalized or "revenue" in normalized:
        active_months = [month for month in analytics.commission_timeline if month.total_commission > 0]
        if not active_months:
            return "No accepted booking commission is scheduled in the next 18 months yet."
        peak = max(active_months, key=lambda item: item.total_commission)
        return (
            f"Forecast agency commission across booked sailings is "
            f"${analytics.total_commission_forecast:,.2f}. "
            f"The strongest sailing month is {peak.label} at ${peak.total_commission:,.2f} "
            f"across {peak.booking_count} booking(s)."
        )

    return (
        "Here is a quick portfolio snapshot: "
        f"{json.dumps(context, default=str)}. "
        "Ask about premium leads, bottlenecks, rejections, or commission timing for a sharper answer."
    )


def answer_sales_copilot_question(
    db: Session,
    *,
    agency_id: str,
    question: str,
    analytics: SalesAnalyticsResponse,
) -> str:
    context = _build_analytics_context(analytics)
    try:
        api_key, model_name = resolve_gemini_credentials(db, agency_id=agency_id)
        return generate_sales_analytics_copilot_answer(
            api_key=api_key,
            model_name=model_name,
            question=question,
            analytics_context=context,
        )
    except GeminiConfigurationError:
        raise
    except GeminiParseError:
        if uses_tenant_gemini_api_key():
            raise
        return _fallback_answer(question, analytics)
