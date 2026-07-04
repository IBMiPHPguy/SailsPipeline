# SailsPipeline — Architecture & Route Map

**Last updated:** July 2026

SailsPipeline is a multi-tenant SaaS CRM for cruise travel agencies. Each **agency** is an isolated tenant. Platform operators provision and monitor tenants through **The Bridge** (`/bridge`). Agency owners and agents work in the CRM. Tenant workspaces support **dynamic white-labeling** (logos, colors, email signatures, Master Terms) via per-agency settings.

---

## Three-layer bootstrap

Application startup is intentionally **zero-seed**: the API reconciles schema only. No default tenant, demo agency, or platform operator is created automatically.

| Layer | When | What runs | Data created |
| --- | --- | --- | --- |
| **1. Infrastructure boot** | Every container start | `db/init.sql` on fresh volumes; API `create_all` + `schema_migrations` | Tables and indexes only |
| **2. Bridge launch** | Once per environment | `bridge_launch.py` via Compose `launch` profile or exec | Single `platform_super_admin` for The Bridge |
| **3. Tenant onboarding** | Per customer | `POST /api/public/register` or Bridge invite → `/onboarding` | Agency, owner, settings, 7-day trial window |

See [README — Local development quickstart](../README.md#local-development-quickstart) and [deployment-readiness.md](deployment-readiness.md) for operational commands.

---

## Multi-tenant boundary guardrails

### Tenant identity

| Concept | Storage | Notes |
| --- | --- | --- |
| **Tenant** | `agencies` row (`CHAR(36)` UUID) | Primary isolation key |
| **Organization handle** | `agencies.organization_handle` | Unique slug used at CRM login (e.g. `bluehorizon`) |
| **Subscription** | `agencies.subscription_state` | `Active`, `Trialing`, `Past Due`, `Locked` |
| **Trial window** | `agencies.trial_ends_at` | Set on self-service or invite onboarding; background scheduler locks expired trials |

### Organization handle scoping and duplicate emails

CRM authentication is **two-part**: `organization_handle` + `username` + `password`.

1. `POST /api/auth/login` resolves the agency by **organization handle** first.
2. The API then looks up the user **within that agency only** (`users.agency_id`).
3. Per-agency email uniqueness is enforced: `UNIQUE (agency_id, email)`.

The same email address may exist in **entirely separate agencies** because login always routes through the tenant slug layer. Password recovery (`/forgot-password`) also requires organization handle + email, scoping reset tokens to one tenant.

Platform operators (`platform_super_admin`) sign in through `POST /api/auth/bridge/login` with **no** organization handle; their `agency_id` is null.

### Defense in depth

| Layer | Mechanism |
| --- | --- |
| **JWT claims** | `user_id`, `agency_id`, `role` on every CRM token |
| **Tenant context middleware** | Binds `agency_id` from JWT before route handlers run |
| **ORM session filter** | `with_loader_criteria` on tenant-scoped models when context is set |
| **Route/service checks** | Ownership helpers return **404 Not Found** (no cross-tenant existence leak) |
| **Attachment paths** | `{agency_id}/requests/{request_id}/{kind}/...` under `ATTACHMENTS_DIR` |
| **Brand assets** | Local dev: `backend/static/uploads/`; stage/prod: S3 bucket (`S3_BRAND_*`) |
| **Reports / analytics** | Explicit `agency_id` filters; dashboard rollups keyed per agency |
| **Subscription gatekeeper** | HTTP **402** when subscription is Past Due or Locked; `/api/auth/me` still allowed |

### Trial locking

New tenant workspaces created via `/register` or onboarding start in **Trialing** with `trial_ends_at = now + TRIAL_PERIOD_DAYS` (default 7).

A background scheduler (`trial_scheduler.py`) polls on `TRIAL_SCHEDULER_POLL_SECONDS` and transitions expired trials to **Locked**. Locked agencies receive HTTP 402 on CRM routes; login returns a trial-expired message. Bridge operators can restore access by updating subscription state.

---

## User roles

| Role | Portal | Access |
| --- | --- | --- |
| `tenant_agent` | CRM | One agency; workflow and request workspace |
| `tenant_super_user` | CRM | Agency owner; Team workspace, Agency Settings, workflows catalog |
| `platform_super_admin` | The Bridge | Cross-tenant provisioning and agency ledger (no CRM data by default) |

Inactive users (`is_active = false`) cannot sign in; profiles remain for reporting.

CRM and Bridge use separate browser tokens (`sailspipeline_crm_token` / `sailspipeline_bridge_token`) so both portals can stay open in different tabs.

---

## White-label branding

Each agency has an `agency_settings` row seeded at onboarding:

- Agency display name, primary/secondary colors
- Logo upload (`POST /api/agency/settings/upload-logo`)
- Email signature HTML and inline signature images
- Master Terms & Conditions vault
- Corporate contact and business address

**CRM chrome** loads branding via `GET /api/agency/branding` and applies CSS variables dynamically.

**Public portals** (password reset, CC auth, terms, insurance) load tenant branding via `GET /api/public/agency/{agency_id}/branding`.

**Transactional email** merges agency branding into HTML templates (welcome, password reset, CC authorization, terms, insurance waiver).

Local development stores logos under `BRAND_UPLOADS_DIR` (default `static/uploads`) and serves them at `/static/uploads/...` through Nginx. Staging and production require `S3_BRAND_BUCKET` configuration.

---

## Local staging tools

| Tool | URL / command | Purpose |
| --- | --- | --- |
| **Nginx (primary app entry)** | http://localhost:8080 | CRM, Bridge, API proxy, static brand assets |
| **Mailpit UI** | http://localhost:8025 | View intercepted transactional HTML email (branded templates) |
| **Mailpit SMTP** | `mailpit:1025` (Docker network) | All outbound mail in `APP_ENV=development` |
| **OpenAPI** | http://localhost:8080/docs | Interactive API docs when `EXPOSE_OPENAPI=true` |
| **Frontend dev server** | http://localhost:5173 | Vite HMR (optional; Nginx is the usual entry point) |
| **MySQL** | `localhost:3306` | Direct DB access for debugging |

When testing email flows locally, open Mailpit after triggering an action (password reset, team invite, welcome email, CC auth link). Links in emails should use `PUBLIC_APP_BASE_URL=http://localhost:8080` so Nginx serves the correct frontend routes.

---

## Frontend route map

Routes are resolved in `frontend/src/main.tsx` before the CRM shell loads.

| Path | Page | Auth |
| --- | --- | --- |
| `/` | CRM dashboard and workspace (view state in `App.tsx`) | CRM JWT |
| `/bridge`, `/bridge/*` | The Bridge platform portal | Bridge JWT |
| `/register` | Self-service agency registration (dev) | Public |
| `/onboarding?token=…` | Bridge platform invitation acceptance | Public |
| `/register-agent?token=…` | Team agent invitation acceptance | Public |
| `/forgot-password` | Request password reset email | Public |
| `/reset-password?token=…` | Set new password from email link | Public |
| `/subscription-restore` | Subscription lock explanation | CRM JWT (locked tenant) |
| `/cc-auth/:token` | Passenger credit-card authorization portal | Token |
| `/accept-terms/:token` | Master Terms clickwrap portal | Token |
| `/insurance-auth/:token` | Insurance waiver portal | Token |

### CRM sidebar views (in-app navigation)

| View | Audience | Notes |
| --- | --- | --- |
| Dashboard | All agents | Open/stale/closed requests, pipeline value |
| Sales Analytics | All agents | Year metrics, funnel, optional Gemini copilot |
| Marketing Campaigns | All agents | Campaign ledger and ROI summary |
| Clients | All agents | Passenger registry |
| Reports | All agents | Five interactive ledgers + Excel export |
| Workflows & Tasks | Super user | Workflow template catalog and custom tasks |
| Group Blocks | Super user | Group inventory and intake |
| Agency Settings | Super user | White-label branding, terms, communications |
| Team | Super user | Invites, user management, deactivation |

---

## API route map (summary)

Unauthenticated routes are listed first. All other `/api/*` routes require a bearer JWT unless noted.

### Public / health

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness |
| `POST` | `/api/public/register` | Self-service tenant provisioning (`ALLOW_PUBLIC_REGISTRATION`) |
| `GET` | `/api/public/agency/{agency_id}/branding` | Public portal branding |
| `POST` | `/api/public/auth/forgot-password` | Issue password reset email |
| `GET` | `/api/public/auth/reset-password/validate/{token}` | Validate reset token + load branding |
| `POST` | `/api/public/auth/reset-password` | Complete password reset |

### Authentication

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/auth/login` | CRM login (`organization_handle`, `username`, `password`) |
| `POST` | `/api/auth/bridge/login` | Bridge login (no organization handle) |
| `GET` | `/api/auth/me` | Current user profile |
| `POST` | `/api/auth/register` | Legacy single-user register (disabled; use `/api/public/register`) |

### Onboarding

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/onboarding/invites/verify` | Verify Bridge platform invitation |
| `POST` | `/api/onboarding/accept` | Accept platform invitation → agency owner |
| `GET` | `/api/onboarding/agent/invites/verify` | Verify Team agent invitation |
| `POST` | `/api/onboarding/agent/accept` | Accept agent invitation |

### The Bridge (`platform_super_admin`)

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/bridge/summary` | Agency ledger summary |
| `POST` | `/api/bridge/invites` | Issue platform invitation → `/onboarding?token=…` |
| `DELETE` | `/api/bridge/invites/{id}` | Revoke pending invitation |
| `GET` | `/api/bridge/tenants/{agency_id}` | Tenant detail |
| `PATCH` | `/api/bridge/tenants/{agency_id}` | Edit handle, subscription state |

### Agency team & settings (`tenant_super_user` where noted)

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/agency/team` | Users and pending invites |
| `POST` | `/api/agency/invites` | Team invitation |
| `DELETE` | `/api/agency/invites/{id}` | Revoke team invite |
| `PATCH` | `/api/agency/users/{user_id}` | Role, email, `is_active` |
| `GET` | `/api/agency/profile` | Agency profile |
| `PATCH` | `/api/agency/profile` | Update agency profile |
| `GET` | `/api/agency/branding` | CRM chrome branding |
| `GET` | `/api/agency/settings` | Full agency settings |
| `PUT` | `/api/agency/settings` | Update settings |
| `POST` | `/api/agency/settings/upload-logo` | Logo upload |
| `POST` | `/api/agency/settings/upload-signature-image` | Signature image upload |

### Core CRM domains

| Prefix | Domain |
| --- | --- |
| `/api/dashboard` | Dashboard rollups and open request summaries |
| `/api/requests` | Travel requests, notes, attachments, proposed cruises, insurance, research |
| `/api/passengers` | Client registry and request passenger links |
| `/api/communications` | Request communications and AI draft generation |
| `/api/workflows` | Workflow lifecycle and task updates |
| `/api/workflow-templates` | Template definitions |
| `/api/analytics/sales` | Sales analytics and copilot |
| `/api/reports` | Interactive report ledgers and meta |
| `/api/marketing-campaigns` | Campaign CRUD and ROI summary |
| `/api/agency-groups` | Group blocks and inventory |

### Passenger portals (token-based)

| Prefix | Domain |
| --- | --- |
| `/api/cc-auth` | Credit-card authorization validate/complete/send |
| `/api/cc-auth/agent` | Agent CC auth ledger, reveal, purge |
| `/api/terms` | Master Terms validate/accept/send |
| `/api/insurance` | Insurance waiver validate/sign/send |

Full endpoint list with query parameters is in [README — API endpoints](../README.md#api-endpoints) and at `/docs` when OpenAPI is enabled.

---

## Backend module layout

| Area | Location |
| --- | --- |
| Application factory | `backend/app/application.py` |
| Settings | `backend/app/config.py` |
| Email tier routing | `backend/app/email_config.py` |
| Tenant middleware | `backend/app/tenant_middleware.py` |
| Subscription gatekeeper | `backend/app/subscription_gatekeeper.py` |
| Trial scheduler | `backend/app/trial_scheduler.py` |
| Rollup scheduler | `backend/app/agency_rollup_scheduler.py` |
| Bridge launch CLI | `backend/scripts/bridge_launch.py` |
| HTTP routers | `backend/app/routers/` |
| Business logic | `backend/app/services/` |

---

## Docker Compose services

| Service | Role |
| --- | --- |
| `db` | MySQL 8.4 with persistent volume |
| `backend` | FastAPI API with auto-reload |
| `frontend` | React 19 + Vite dev server |
| `nginx` | Reverse proxy: `/api`, `/static`, `/docs` → backend; `/` → frontend |
| `mailpit` | Local SMTP capture and web UI (development) |
| `bridge-launch` | One-shot `launch` profile job for platform operator bootstrap |
| `test-db`, `backend-test`, `frontend-test` | Ephemeral test profile |

Request attachment uploads use the `attachment_uploads` volume at `/app/uploads` in the backend container.
