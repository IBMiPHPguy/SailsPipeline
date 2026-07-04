# Pre-Flight Cloud Readiness

Use this checklist when moving SailsPipeline from local Docker to a staging or production cloud server. Complete items in order; several steps are **one-time per environment**.

---

## 1. Infrastructure

- [ ] Provision a host or container platform with Docker Compose (or equivalent orchestration).
- [ ] Provision **MySQL 8.4** (managed service or container) with strong credentials — not `cruisesecret` / `rootsecret`.
- [ ] Point `DATABASE_URL` at the production database:  
  `mysql+pymysql://<user>:<password>@<host>:3306/sailspipeline`
- [ ] On first deploy, allow the API to run `create_all` + `schema_migrations`, or apply `db/init.sql` to a fresh database volume.
- [ ] Place TLS certificates at `nginx/certs/fullchain.pem` and `nginx/certs/privkey.pem`.
- [ ] Start with the production overlay:  
  `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`

The production overlay stops publishing MySQL, backend, and frontend ports on the host (HTTPS via Nginx only), sets `APP_ENV=production`, and disables public registration and OpenAPI.

---

## 2. Cryptographic secrets

Generate unique values for every environment. Never reuse development defaults.

| Variable | Requirement |
| --- | --- |
| `JWT_SECRET` | At least **32 characters**; not `change-me-in-production` or other known defaults |
| `MYSQL_ROOT_PASSWORD` / `MYSQL_PASSWORD` | Strong random passwords |
| `CC_AUTH_ENCRYPTION_KEY` | Fernet key for transient card vault encryption |
| `CC_AUTH_VAULT_ACCESS_KEY` | Strong random access key for agent reveal endpoints |

Generate a Fernet key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Generate a JWT secret (example):

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

When `APP_ENV=production`, the backend **refuses to start** if `JWT_SECRET`, database passwords, `CORS_ORIGINS`, `ALLOW_PUBLIC_REGISTRATION`, `EXPOSE_OPENAPI`, or `EMAIL_API_KEY` fail validation (`backend/app/security_config.py`).

---

## 3. Application environment tier

| Setting | Staging | Production |
| --- | --- | --- |
| `APP_ENV` | `staging` | `production` |
| `ALLOW_PUBLIC_REGISTRATION` | `false` (recommended) | **`false` required** |
| `EXPOSE_OPENAPI` | `false` (recommended) | **`false` required** |
| `CORS_ORIGINS` | Explicit staging origin(s) | Explicit production origin(s) — no `*` |
| `PUBLIC_APP_BASE_URL` | `https://staging.your-domain.example` | `https://your-domain.example` |

---

## 4. Email delivery (leave Mailpit behind)

Local development routes all mail through the **Mailpit** container (`mailpit:1025`). Cloud deployments must use a transactional provider.

| Tier | Transport | Required variables |
| --- | --- | --- |
| `development` | Mailpit SMTP | None (automatic) |
| `staging` | Cloud API (Resend, etc.) | `EMAIL_API_KEY_STAGING`, optional `EMAIL_FROM_ADDRESS_STAGING` |
| `production` | Cloud API | `EMAIL_API_KEY`, `EMAIL_FROM_ADDRESS` |

Steps:

1. Create accounts and verified sending domains with your provider (e.g. Resend, Postmark).
2. Set `EMAIL_API_PROVIDER` (default `resend`).
3. Configure API keys in `.env` or your secrets manager.
4. Verify branded templates render correctly (welcome, password reset, invitations, CC auth, terms, insurance).
5. Update portal base URLs to production HTTPS origins:
   - `PUBLIC_APP_BASE_URL`
   - `CC_AUTH_PORTAL_BASE_URL`
   - `TERMS_PORTAL_BASE_URL`
   - `INSURANCE_PORTAL_BASE_URL`

---

## 5. Static and brand asset storage

| Tier | Mechanism | Configuration |
| --- | --- | --- |
| `development` | Local filesystem | `BRAND_UPLOADS_DIR=static/uploads` (served at `/static/uploads/`) |
| `staging` / `production` | Object storage (S3-compatible) | `S3_BRAND_BUCKET`, `S3_BRAND_REGION`, `S3_BRAND_PUBLIC_BASE_URL` |

Request attachments (transcripts, research documents) use `ATTACHMENTS_DIR` on disk in the default Compose setup. For multi-node production, plan a shared volume or migrate attachments to object storage.

Brand logo upload to S3 is scaffolded in `backend/app/brand_logo_storage.py` — enable boto3 upload and verify bucket policy before go-live.

---

## 6. Bridge launch (one-time platform operator)

The API does **not** create a platform operator at boot. After the database and backend are healthy:

```bash
# Set SEED_BRIDGE_ADMIN_USERNAME, SEED_BRIDGE_ADMIN_EMAIL, SEED_BRIDGE_ADMIN_PASSWORD in .env
docker compose --profile launch run --rm bridge-launch
```

Or exec into the running backend:

```bash
docker compose exec backend python scripts/bridge_launch.py
```

Preflight only:

```bash
docker compose exec backend python scripts/bridge_launch.py --check-only
```

`SEED_ADMIN_*` variables are **legacy placeholders** and are not consumed during application startup. Only `SEED_BRIDGE_ADMIN_*` is read by the Bridge launch CLI.

---

## 7. Tenant provisioning strategy

| Environment | Recommended path |
| --- | --- |
| **Production** | Bridge platform invitations → `/onboarding?token=…` |
| **Staging** | Bridge invitations or controlled `ALLOW_PUBLIC_REGISTRATION=true` |
| **Local dev** | `/register` self-service when `ALLOW_PUBLIC_REGISTRATION=true` |

New tenants receive a **7-day trial** (`TRIAL_PERIOD_DAYS`). Ensure `TRIAL_SCHEDULER_ENABLED=true` in production so expired trials lock automatically.

---

## 8. Trial and subscription operations

- [ ] Confirm `TRIAL_PERIOD_DAYS` matches your commercial policy (default 7).
- [ ] Confirm `TRIAL_SCHEDULER_ENABLED=true` and `TRIAL_SCHEDULER_POLL_SECONDS` is acceptable (default 300s).
- [ ] Document how Bridge operators restore locked tenants (`PATCH /api/bridge/tenants/{agency_id}` → `subscription_state: Active`).
- [ ] Plan billing webhook integration (optional future work) if self-service restore is required.

---

## 9. Security verification

- [ ] `GET /api/health` returns `{"status":"ok",...}` behind Nginx.
- [ ] `/docs` and `/openapi.json` are **not** reachable in production.
- [ ] CRM login requires `organization_handle` and rejects cross-tenant ID access with 404.
- [ ] Login and registration rate limiting active (`AUTH_RATE_LIMIT`, default `10/minute`).
- [ ] Nginx prod config serves HSTS and security headers (`nginx/nginx.prod.conf`).
- [ ] Optional: configure `GEMINI_API_KEY` only if AI features are required in production.

---

## 10. Post-deploy smoke test

1. Sign in to The Bridge at `https://your-domain.example/bridge`.
2. Issue a platform invitation and complete onboarding at `/onboarding`.
3. Sign in to the CRM with the new agency's organization handle.
4. Upload a logo in Agency Settings; confirm `/static` or S3 URL resolves.
5. Trigger a password reset; confirm email delivery and `/reset-password` flow.
6. Create a travel request, attachment, and communication to verify upload volume permissions.
7. Run the test suite against a staging database before promoting:

```bash
docker compose --profile test rm -sf test-db
docker compose --profile test up -d test-db
./scripts/run-tests.ps1
```

---

## Quick reference: development vs production

| Concern | Local Docker | Cloud production |
| --- | --- | --- |
| Entry URL | http://localhost:8080 | `https://your-domain.example` |
| Email | Mailpit → http://localhost:8025 | Resend/Postmark via `EMAIL_API_KEY` |
| Brand logos | `static/uploads/` on disk | `S3_BRAND_BUCKET` |
| JWT / DB passwords | Dev defaults | Cryptographically secure, validated at boot |
| Platform operator | `bridge-launch` one-shot | Same one-shot per environment |
| New agencies | `/register` (dev) | Bridge invitations |
| OpenAPI | http://localhost:8080/docs | Disabled |
