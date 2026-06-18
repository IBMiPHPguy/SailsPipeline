from fastapi import FastAPI

from app.routers import auth, communications, dashboard, health, passengers, requests, workflows


def register_routers(application: FastAPI) -> None:
    application.include_router(health.router)
    application.include_router(auth.router)
    application.include_router(dashboard.router)
    application.include_router(passengers.router)
    application.include_router(passengers.request_passengers_router)
    application.include_router(communications.router)
    application.include_router(workflows.templates_router)
    application.include_router(workflows.router)
    application.include_router(requests.router)
