from app.config import Settings

INSECURE_JWT_SECRETS = frozenset(
    {
        "change-me-in-production",
        "test-jwt-secret",
        "test-jwt-secret-for-tests",
    }
)

INSECURE_DATABASE_PASSWORD_FRAGMENTS = (
    "cruisesecret",
    "rootsecret",
    "password",
    "testroot",
)


def validate_production_settings(settings: Settings) -> None:
    if settings.app_env not in {"production", "prod"}:
        return

    errors: list[str] = []

    if settings.jwt_secret in INSECURE_JWT_SECRETS or len(settings.jwt_secret) < 32:
        errors.append("JWT_SECRET must be a unique value of at least 32 characters.")

    database_url = settings.database_url.lower()
    if any(fragment in database_url for fragment in INSECURE_DATABASE_PASSWORD_FRAGMENTS):
        errors.append("DATABASE_URL must not use default or example passwords.")

    if settings.allow_public_registration:
        errors.append("ALLOW_PUBLIC_REGISTRATION must be false.")

    if "*" in settings.cors_origin_list:
        errors.append("CORS_ORIGINS must list explicit origins; '*' is not allowed.")

    if settings.expose_openapi:
        errors.append("EXPOSE_OPENAPI must be false.")

    if not settings.email_api_key:
        errors.append("EMAIL_API_KEY must be set for production email delivery.")

    if errors:
        message = "Refusing to start with insecure production configuration:\n- " + "\n- ".join(errors)
        raise RuntimeError(message)
