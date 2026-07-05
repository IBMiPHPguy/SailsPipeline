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

REQUIRED_PRODUCTION_CORS_ORIGINS = frozenset(
    {
        "https://sailspipeline.com",
        "https://app.sailspipeline.com",
    }
)

LOCALHOST_CORS_MARKERS = ("localhost", "127.0.0.1")


def _validate_production_cors(settings: Settings, errors: list[str]) -> None:
    origins = settings.cors_origin_list

    if not origins:
        errors.append(
            "CORS_ORIGINS must be set for production. "
            "Required: https://sailspipeline.com,https://app.sailspipeline.com"
        )
        return

    for origin in origins:
        if "*" in origin:
            errors.append("CORS_ORIGINS must list explicit origins; '*' is not allowed.")
        if not origin.startswith("https://"):
            errors.append(f"CORS origin must use https:// in production: {origin}")
        origin_lower = origin.lower()
        if any(marker in origin_lower for marker in LOCALHOST_CORS_MARKERS):
            errors.append(
                "CORS_ORIGINS must not include localhost in production. "
                "Set CORS_ORIGINS=https://sailspipeline.com,https://app.sailspipeline.com"
            )

    missing_required = REQUIRED_PRODUCTION_CORS_ORIGINS - set(origins)
    if missing_required:
        errors.append(
            "CORS_ORIGINS must include all required production domains: "
            + ", ".join(sorted(REQUIRED_PRODUCTION_CORS_ORIGINS))
            + f". Missing: {', '.join(sorted(missing_required))}."
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

    _validate_production_cors(settings, errors)

    if settings.expose_openapi:
        errors.append("EXPOSE_OPENAPI must be false.")

    if not (settings.resolved_mailgun_api_key or settings.email_api_key):
        errors.append("MAILGUN_API_KEY must be set for production email delivery.")

    if errors:
        message = "Refusing to start with insecure production configuration:\n- " + "\n- ".join(errors)
        raise RuntimeError(message)
