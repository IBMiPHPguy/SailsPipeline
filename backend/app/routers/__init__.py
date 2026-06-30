from fastapi import FastAPI

from app.routers import auth, agency, bridge, communications, dashboard, health, marketing_campaigns, onboarding, passengers, reports, requests, sales_analytics, workflows


def register_routers(application: FastAPI) -> None:
    application.include_router(health.router)
    application.include_router(auth.router)
    application.include_router(bridge.router)
    application.include_router(onboarding.router)
    application.include_router(agency.router)
    application.include_router(dashboard.router)
    application.include_router(marketing_campaigns.router)
    application.include_router(sales_analytics.router)
    application.include_router(reports.router)
    application.include_router(passengers.router)
    application.include_router(passengers.request_passengers_router)
    application.include_router(communications.router)
    application.include_router(workflows.templates_router)
    application.include_router(workflows.settings_router)
    application.include_router(workflows.catalog_router)
    application.include_router(workflows.router)
    application.include_router(requests.router)
