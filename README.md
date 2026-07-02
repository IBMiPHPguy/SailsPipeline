# SailsPipeline

Web app for managing cruise travel requests from intake through research, client communication, and booking prep.

Agents use a workflow-driven workspace for each open request: capture client details, upload research, propose cruises, draft and send communications, track follow-ups, record client decisions, and close or reopen requests as needed.

SailsPipeline is **multi-tenant**: CRM data is isolated by agency. Each agency signs in with an **organization handle** (tenant slug). Platform operators use **The Bridge** (`/bridge`) to provision new agencies. Agency owners use the CRM **Team** workspace to invite agents and manage user access. See [`docs/multi-tenant-design.md`](docs/multi-tenant-design.md) for architecture, roles, and verification checklist.

## Stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19 + TypeScript + Vite |
| Backend API | Python 3.12 + FastAPI |
| Auth | JWT bearer tokens + bcrypt password hashing |
| AI (optional) | Google Gemini via `google-generativeai` |
| Web server | Nginx (reverse proxy) |
| Database | MySQL 8.4 |
| Containers | Docker Compose |

Python was chosen for the API because it is widely used for modern web services, pairs well with FastAPI for workflow APIs, and keeps the backend easy to extend as the cruise request workflow grows.

## Quick start

1. Copy environment defaults if needed:

```powershell
Copy-Item .env.example .env
```

2. Start the full stack:

```powershell
docker compose up --build
```

3. Open the app:

| URL | Purpose |
| --- | --- |
| http://localhost:8080 | CRM app (via Nginx) |
| http://localhost:8080/bridge | The Bridge (platform admin portal) |
| http://localhost:5173 | Frontend dev server |
| http://localhost:8080/docs | OpenAPI / Swagger docs |
| localhost:3306 | MySQL |

4. Sign in to the CRM with the seeded admin account from `.env`:

- Organization handle: `default` (default agency slug)
- Username: `admin`
- Password: value of `SEED_ADMIN_PASSWORD` in `.env`

Passwords must be more than 10 characters and include at least one uppercase letter, one lowercase letter, one numeral, and one special character. Spaces are not allowed.

**The Bridge:** open http://localhost:8080/bridge and sign in with `SEED_BRIDGE_ADMIN_USERNAME` / `SEED_BRIDGE_ADMIN_PASSWORD` from `.env` to provision new tenant agencies.

New CRM users join through **team invitations** issued by a tenant super user (Team workspace), not self-registration from the login screen. Public registration at `/register` is for **new agency onboarding** from Bridge-issued platform invitations when `ALLOW_PUBLIC_REGISTRATION=true`.

## Application overview

### Multi-tenant roles

| Role | Access |
| --- | --- |
| `tenant_agent` | CRM for one agency |
| `tenant_super_user` | CRM plus Team workspace (invites, user management) |
| `platform_super_admin` | The Bridge only (cross-tenant provisioning and agency ledger) |

Inactive agency users (`is_active = false`) cannot sign in; their profiles remain for reporting and can be reactivated from Team.

When an agency subscription is **Past Due** or **Locked**, most CRM API routes return **HTTP 402** and the app shows a subscription restore page. `/api/auth/me` still works so the user can sign out.

### Dashboard

The signed-in home screen shows:

- **Open requests** — active travel requests with destination, dates, and workflow context
- **Stale requests** — open requests with no activity in 3+ days (`STALE_DAYS`)
- **Closed requests** — clickable tile that opens the closed-requests list
- **Pipeline value** — sums booked cruise costs on open requests (back-to-back accepted cruises count in full); otherwise uses the highest active quote per request

Each open request row shows the next open workflow task, last worked timestamp, and whether it is stale.

Dashboard tile counts and pipeline value are served from **per-agency rollup rows** (`agency_dashboard_rollups`), refreshed on a schedule and when requests close or proposed cruises are accepted, deposited, or rejected.

### Sales Analytics

The **Sales Analytics** sidebar view summarizes pipeline and booking performance:

- Year-scoped **key metrics** (booked volume, commission, close ratio) from **Accepted and Deposited** proposed cruises — each cruise row counts separately (back-to-back and side-by-side bookings sum correctly)
- **Cruise line brand share** and funnel-stage counts at the cruise-row level
- Optional **copilot Q&A** when `GEMINI_API_KEY` is configured

Endpoints live under `/api/analytics/sales`.

### Reports

The **Reports** sidebar view lists five interactive ledgers grouped by category. Each report opens in a full-page HTML table with filter controls, pagination, and **Export to Excel** (styled `.xlsx` via ExcelJS, exporting all rows that match the current filters).

| Report | Filters (high level) |
| --- | --- |
| Sales Volume & Target Manifest | Cruise line, timeframe, pipeline status, workflow task |
| Supplier Share & Volume Ledger | Cruise line, timeframe |
| Funnel Leak & Lost Business Analysis | Cruise line, timeframe, loss segment, rejection reason |
| Advisor Productivity & Quota Scorecard | Timeframe, advisor |
| Passenger Demographics & Qualifier Ledger | State, qualifier (multi-select, OR logic) |

Report data is served from `/api/reports/*`. Filter metadata (workflow tasks, advisor names, residence states) comes from `GET /api/reports/meta` (advisor and state lists are cached per agency).

### Marketing campaigns

Agency-scoped campaign tracking lives under `/api/marketing-campaigns`. The CRM sidebar includes a **Marketing Campaigns** page (create form + ledger with active/past filters). When creating or editing a travel request, agents can set **Source** to bind referrals or marketing campaigns.

- `GET /api/marketing-campaigns?timeframe=all|active|past`
- `POST /api/marketing-campaigns`
- `GET /api/marketing-campaigns/{campaign_id}`
- `PATCH /api/marketing-campaigns/{campaign_id}`
- `DELETE /api/marketing-campaigns/{campaign_id}`

All routes enforce tenant isolation; a campaign ID from another agency returns **404 Not Found**.

Marketing ROI summary cards read from the Phase 3a `agency_dashboard_rollups` cache (refreshed with dashboard rollups when campaigns change or booked cruises update).

**Booked-cruise aggregation:** Sales manifest gross/commission totals sum all Accepted and Deposited cruises on a request. The supplier ledger groups volume, commission, and booking counts by cruise line at the cruise-row level (side-by-side lines on one request each get their own ledger row).

Phone numbers in report and client **display** views use `(xxx) xxx-xxxx` formatting; input fields keep the raw stored value.

### Travel requests

Each request stores client contact info, destination (with region-specific details), travel dates, cabin preferences, qualifiers, and cabin count. Requests can be **Open** or **Closed** with a close reason. Optional lead attribution fields include `lead_source`, `referral_source_name` (when source is Referral), and `marketing_campaign_id` (when source is Marketing Campaign).

Closing a request records the reason and prevents most edits until reopened. Reopen is available from the closed-requests page unless the close reason is **Purchased - Trip Created**.

Close reasons:

- Purchased - Trip Created
- Cost - Went with Competitor
- Communication - Went with Competitor
- Changed Vacation Plans
- General Inquiry - Fishing

### Request workspace layout

When editing a request, the workspace uses a responsive two-column layout:

- **Left column:** Request Details (questionnaire fields, save, close request)
- **Right column (top to bottom):**
  - Passengers
  - Proposed cruises / Quoted insurance tabs
  - Call transcripts / Chat logs / Communications tabs
  - Workflows
  - Notes & research
  - Change history

The client content card (passengers through communications) stays beside request details when there is room. It expands to full width only when it would otherwise sit below the request details panel.

### Passengers and clients

- Add passengers manually or link from the shared passenger registry
- Search existing passengers with `GET /api/passengers/search`
- Primary passenger contact fields sync back to the request header
- Passenger field changes are audited

**Clients page** (`/clients`) manages reusable passenger profiles across requests:

- List, search, view, and edit client profiles
- **Deactivate** inactive clients (they stay on existing requests but cannot be added to new ones)
- **Reactivate** previously inactive clients
- Deactivation uses a confirmation modal with an explicit opt-in checkbox

Inactive passengers are visually flagged in request passenger lists.

### Team (tenant super user)

The **Team** sidebar view (`tenant_super_user` only) manages agency users:

- Issue team invitations (3-day expiry) for agents or other super users
- Revoke pending invitations
- Edit user email and role
- Deactivate or reactivate users (inactive users cannot sign in; history stays in reports)
- Filter the agency users table: Active only (default), Inactive only, or both

Invited agents complete registration at `/register-agent?token=…`.

### The Bridge (platform super admin)

**The Bridge** at `/bridge` is a separate portal for platform operators:

- Issue platform invitations to provision new tenant companies
- Review the agency ledger and pending platform invitations
- Edit agency subscription state and organization handle
- Revoke pending platform invitations

New agency owners complete onboarding at `/register?token=…`, which creates the agency and first `tenant_super_user` in one step.

CRM and Bridge use separate browser tokens so both can stay open in different tabs.

### Proposed cruises and quoted insurance

**Proposed cruises** support Proposed, Accepted, Deposited, and Rejected statuses. The UI splits them into **Proposed & accepted** and **Rejected** sub-tabs.

- Add cruises manually or bulk-generate from a research document (Gemini)
- **Back-to-back / side-by-side bookings:** accept multiple cruises on one request without auto-rejecting the others; each accepted cruise keeps its own cabin-hold reservation IDs and payment checklist in Enter Trip in CRM
- Accepted/rejected state drives workflow outcomes in **Record client response**

**Quoted insurance** tracks Proposed, Accepted, and Declined quotes. Adding new quotes is hidden once a proposed cruise has been accepted.

### Notes, attachments, and communications

- **Notes** — free-text notes with AI-generated summaries and change history
- **Call transcripts** and **chat logs** — uploaded as `.txt` files, stored on disk under `ATTACHMENTS_DIR`
- **Research documents** — `.txt` uploads used for AI extraction and new research cycles
- **Communications** — draft/sent/archived messages (research proposal, follow-up, booking, agency, etc.); draft communications can be deleted from the request workspace

### Workflows

Each open request has at most one **active** workflow at a time. Completing the Research workflow automatically starts **Communicate Research** as a linked successor workflow.

Workflow templates:

| Workflow | Purpose |
| --- | --- |
| Research | Research options, upload findings, create proposals, draft communication |
| Communicate Research | Send proposal, follow up, record client response |
| Enter Trip in CRM | Post-booking checklist (passenger verification, cabin holds, payments, CRM entry) |

#### Research workflow tasks

1. Research cruise options
2. Upload research document
3. Create proposed cruises
4. Draft research communication

Task panels guide each step. The draft step can generate a client email from proposed cruises using Gemini.

#### Communicate Research workflow tasks

Tasks run in a linear order in the UI (later tasks stay locked until prerequisites are done), with one exception noted below.

1. **Send research communication** — pick a draft research-proposal communication, copy subject/body, mark sent when delivered. Completing this schedules the follow-up due date **3 days** later.
2. **Follow up on research communication** — optional **Mark as reached out** resets the due date +3 days without completing the task. Tasks show **Late** when overdue and client response is not yet recorded. Follow-up does **not** block recording the client response.
3. **Record client response** — accept one or more proposed cruises, or reject all options:
   - **Accept:** mark each cruise the client wants as accepted; other cruises stay proposed until you reject them explicitly
   - **Reject all:** choose to close the request (with close reason) or start a new Research workflow (requires uploading a new research document first). **Purchased - Trip Created** is hidden when all cruises are rejected

When at least one cruise is accepted, the Communicate Research workflow can complete and the **Enter Trip in CRM** workflow can be started manually.

#### Task updates

`PATCH /api/requests/{id}/tasks/{task_id}` supports:

- `status` — Open or Done
- `due_at` — manual due date override
- `reached_out` — record follow-up outreach and push due date +3 days
- `result` — structured task result payload

## Gemini AI (optional)

Set `GEMINI_API_KEY` in `.env` to enable AI features. Default model: `GEMINI_MODEL=gemini-2.5-flash-lite`.

Without a key, the app still runs; AI actions return a configuration error.

| Feature | Endpoint |
| --- | --- |
| Extract proposed cruises from a research `.txt` | `POST .../proposed-cruises/generate-from-research` |
| Draft research proposal email from proposed cruises | `POST .../communications/generate-from-proposals` |

After changing `.env`, restart the backend:

```powershell
docker compose up -d backend
```

## Authentication

CRM sign-in:

- `POST /api/auth/login` — body includes `organization_handle`, `username`, and `password`; returns a JWT access token scoped to that agency
- `GET /api/auth/me` — current signed-in user (`role`, `is_active`, `agency_id`, etc.)
- Inactive users are rejected at login and on token validation

Bridge sign-in:

- `POST /api/auth/bridge/login` — platform operator username and password (no organization handle)

Onboarding (unauthenticated):

- `GET/POST /api/onboarding/invites/verify` and `/api/onboarding/accept` — new agency owner registration from Bridge invite (`/register`)
- `GET/POST /api/onboarding/agent/invites/verify` and `/api/onboarding/agent/accept` — agent registration from Team invite (`/register-agent`)

Legacy self-registration (optional):

- `POST /api/auth/register` — only when `ALLOW_PUBLIC_REGISTRATION=true`; not used by the CRM login screen

All other `/api/*` endpoints require authentication. CRM routes require a tenant JWT; Bridge routes require a platform super admin JWT.

## Audit tracking

Each travel request stores:

- `created_by` and `created_at` when the request is submitted
- `updated_by` and `updated_at` when the request is changed

Request, passenger, and note changes are recorded in change history views. These values are shown in the request list and workspace.

## Services

| Service | Role |
| --- | --- |
| `nginx` | Serves the frontend and proxies `/api` to the backend |
| `frontend` | React dev server with hot reload |
| `backend` | FastAPI with auto-reload |
| `db` | MySQL with persistent storage |

Uploaded files (transcripts, chats, research documents) live in the `attachment_uploads` Docker volume, mounted at `/app/uploads` in the backend container.

## Backend layout

The FastAPI app is created in `backend/app/application.py` and mounted for Uvicorn via `backend/app/main.py`. HTTP routes are grouped by domain under `backend/app/routers/`; business logic lives in `backend/app/services/`.

| Module | Responsibility |
| --- | --- |
| `routers/health.py`, `routers/auth.py` | Health check and CRM/Bridge authentication |
| `routers/onboarding.py` | Platform and agent invite verification and acceptance |
| `routers/agency.py` | Team workspace: users, invites, user updates |
| `routers/bridge.py` | The Bridge: tenant provisioning, agency ledger |
| `routers/dashboard.py` | Dashboard aggregates |
| `routers/requests.py` | Travel requests, notes, attachments, proposed cruises, insurance, research documents |
| `routers/passengers.py` | Client registry and request passenger links |
| `routers/communications.py` | Request communications |
| `routers/workflows.py` | Workflow templates, workflow lifecycle, task updates |
| `routers/sales_analytics.py` | Sales analytics aggregates and copilot |
| `routers/reports.py` | Interactive report pages (manifest, ledger, funnel leak, scorecard, demographics) |
| `services/agency_invite_service.py` | Agency team invites and user management |
| `services/auth_service.py` | CRM and Bridge credential authentication |
| `services/bridge_service.py` | Platform invitations and agency provisioning |
| `services/agency_service.py` | Default agency bootstrap and tenant ownership checks |
| `subscription_gatekeeper.py` | HTTP 402 when subscription is Past Due or Locked |
| `services/request_service.py` | Request queries, detail assembly, open-request guards |
| `services/dashboard_service.py` | Dashboard response building (rollup-backed counts) |
| `services/agency_rollup_service.py` | Per-agency dashboard rollups and report metadata cache refresh |
| `services/booked_cruise_metrics.py` | Shared Accepted/Deposited cruise SQL aggregates (volume, counts, commission) |
| `services/passenger_service.py`, `passenger_helpers.py` | Passenger registry and request sync |
| `services/communication_service.py` | Communication CRUD and Gemini draft generation |
| `services/workflow_service.py` | Workflow creation, completion, and task updates |
| `services/proposed_cruise_record_service.py` | Proposed cruise persistence and Gemini extraction |
| `services/sales_analytics_service.py` | Sales analytics metrics and funnel assembly |
| `services/reports_service.py` | Filtered report queries and pagination |

Domain helpers (cabin normalization, workflow templates, research email HTML, etc.) remain in focused modules beside `services/`.

## Environment variables

See `.env.example` for defaults.

| Variable | Purpose |
| --- | --- |
| `MYSQL_*` | Database credentials |
| `JWT_SECRET`, `JWT_EXPIRE_MINUTES` | Auth token signing |
| `SEED_ADMIN_*` | Initial CRM tenant super user created on startup |
| `SEED_BRIDGE_ADMIN_*` | Optional platform operator for The Bridge (`/bridge`) |
| `ATTACHMENTS_DIR` | Upload root inside the backend container |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Optional AI integration |
| `*_PORT` | Host ports for nginx, frontend, backend |
| `ALLOW_PUBLIC_REGISTRATION` | When `false`, `/api/auth/register` returns 403 |
| `CORS_ORIGINS` | Comma-separated browser origins allowed by the API |
| `EXPOSE_OPENAPI` | When `false`, hides `/docs` and `/openapi.json` on the backend |
| `AUTH_RATE_LIMIT` | slowapi limit for login/register (default `10/minute`) |
| `APP_ENV` | Set to `production` to enforce secure startup checks |
| `ROLLUP_SCHEDULER_ENABLED` | When `true`, background job refreshes agency analytics rollups (default `true`; disabled in test) |
| `ROLLUP_REFRESH_POLL_SECONDS` | How often queued rollup refreshes are processed (default `30`) |
| `ROLLUP_DAILY_REFRESH_HOUR_UTC` | Hour (UTC) for a full rollup refresh of all agencies (default `3`) |

Change `JWT_SECRET`, database passwords, and the seeded admin password before deploying outside local development.

## Security

Development defaults are convenient, not hardened. For production:

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Production overlay (`docker-compose.prod.yml`):

- Stops publishing MySQL, backend, and frontend ports on the host (nginx HTTPS only)
- Sets `ALLOW_PUBLIC_REGISTRATION=false` and `EXPOSE_OPENAPI=false`
- Uses `nginx/nginx.prod.conf` with TLS, HSTS, security headers, and blocked API docs
- Requires TLS certs in `nginx/certs/fullchain.pem` and `nginx/certs/privkey.pem`

When `APP_ENV=production`, the backend refuses to start unless:

- `JWT_SECRET` is at least 32 characters and not a known default
- `DATABASE_URL` does not use example passwords
- `ALLOW_PUBLIC_REGISTRATION=false`
- `CORS_ORIGINS` lists explicit origins (no `*`)
- `EXPOSE_OPENAPI=false`

Other P0 controls already in place:

- bcrypt password hashing and JWT bearer auth on all CRM routes
- Login/register rate limiting (`AUTH_RATE_LIMIT`)
- Attachment path containment (blocks `..` and paths outside the upload root)
- nginx security headers on the dev proxy (`nginx/nginx.conf`)

Local development still exposes ports. CRM login is sign-in only; team and platform onboarding use invitation links when `ALLOW_PUBLIC_REGISTRATION=true`.

## API endpoints

All routes below require authentication unless noted.

### Health and auth

- `GET /api/health`
- `POST /api/auth/login` — CRM login (`organization_handle`, `username`, `password`)
- `POST /api/auth/bridge/login` — Bridge login
- `GET /api/auth/me`
- `POST /api/auth/register` — optional legacy self-registration when enabled

### Onboarding

- `GET /api/onboarding/invites/verify?token=` — verify Bridge platform invitation
- `POST /api/onboarding/accept` — accept platform invitation and create agency owner
- `GET /api/onboarding/agent/invites/verify?token=` — verify Team agent invitation
- `POST /api/onboarding/agent/accept` — accept agent invitation

### Agency team (tenant super user)

- `GET /api/agency/team` — agency users and pending invitations
- `POST /api/agency/invites`
- `DELETE /api/agency/invites/{invitation_id}`
- `PATCH /api/agency/users/{user_id}` — role, email, `is_active`

### The Bridge (platform super admin)

- `GET /api/bridge/summary`
- `POST /api/bridge/invites`
- `DELETE /api/bridge/invites/{invitation_id}`
- `GET /api/bridge/tenants/{agency_id}`
- `PATCH /api/bridge/tenants/{agency_id}`

### Dashboard and requests

- `GET /api/dashboard` — open/stale/closed counts and open request summaries
- `GET /api/requests`
- `GET /api/requests/closed`
- `POST /api/requests`
- `GET /api/requests/{id}`
- `PATCH /api/requests/{id}` — update fields or close request (`status`, `close_reason`)
- `POST /api/requests/{id}/reopen`
- `GET /api/requests/{id}/change-history`

### Notes

- `GET /api/requests/{id}/notes`
- `GET /api/requests/{id}/notes/{note_id}`
- `POST /api/requests/{id}/notes`
- `PATCH /api/requests/{id}/notes/{note_id}`

### Attachments

- `POST /api/requests/{id}/transcripts`
- `GET /api/requests/{id}/transcripts/{transcript_id}/content`
- `POST /api/requests/{id}/chats`
- `GET /api/requests/{id}/chats/{chat_id}/content`

### Proposed cruises and insurance

- `POST /api/requests/{id}/proposed-cruises`
- `POST /api/requests/{id}/proposed-cruises/generate-from-research`
- `POST /api/requests/{id}/proposed-cruises/bulk`
- `PATCH /api/requests/{id}/proposed-cruises/{cruise_id}`
- `POST /api/requests/{id}/quoted-insurance`
- `PATCH /api/requests/{id}/quoted-insurance/{quote_id}`

### Passengers and client registry

- `GET /api/passengers/search?q=&limit=`
- `GET /api/passengers`
- `GET /api/passengers/{passenger_id}`
- `PATCH /api/passengers/{passenger_id}`
- `POST /api/passengers/{passenger_id}/deactivate`
- `POST /api/passengers/{passenger_id}/activate`
- `POST /api/requests/{id}/passengers`
- `PATCH /api/requests/{id}/passengers/{passenger_id}`
- `DELETE /api/requests/{id}/passengers/{passenger_id}`

### Workflows and tasks

- `GET /api/workflow-templates`
- `POST /api/requests/{id}/workflows`
- `PATCH /api/requests/{id}/workflows/{workflow_id}`
- `PATCH /api/requests/{id}/tasks/{task_id}`

### Communications and research documents

- `GET /api/requests/{id}/communications/{communication_id}`
- `POST /api/requests/{id}/communications`
- `PATCH /api/requests/{id}/communications/{communication_id}`
- `DELETE /api/requests/{id}/communications/{communication_id}` — draft only
- `POST /api/requests/{id}/communications/generate-from-proposals`
- `POST /api/requests/{id}/research-documents`
- `GET /api/requests/{id}/research-documents/{document_id}/content`

### Sales analytics

- `GET /api/analytics/sales` — dashboard aggregates (funnel, brand share, rejection reasons)
- `GET /api/analytics/sales/key-metrics/{year}` — year-scoped booked volume and commission metrics
- `POST /api/analytics/sales/copilot` — natural-language Q&A over analytics data (requires Gemini)

### Reports

Shared query parameters include `page`, `page_size`, and `timeframe` where applicable.

- `GET /api/reports/meta` — workflow task groups, advisor names, residence states
- `GET /api/reports/sales-manifest` — `cruise_line`, `pipeline_status`, `workflow_task`, `timeframe`
- `GET /api/reports/supplier-ledger` — `cruise_line`, `timeframe`
- `GET /api/reports/funnel-leak` — `cruise_line`, `timeframe`, `loss_segment`, `rejection_reason`
- `GET /api/reports/advisor-scorecard` — `timeframe`, `advisor`
- `GET /api/reports/passenger-demographics` — `state`, `qualifier` (repeat for multi-select OR filter)

Marketing campaigns (tenant-scoped):

- `GET /api/marketing-campaigns?timeframe=all|active|past`
- `POST /api/marketing-campaigns`
- `GET /api/marketing-campaigns/{campaign_id}`
- `PATCH /api/marketing-campaigns/{campaign_id}`
- `DELETE /api/marketing-campaigns/{campaign_id}`
- `GET /api/marketing-campaigns/summary` — cached ROI summary (`active_monthly_budget`, `top_roi_campaign_name`, `top_roi_percent`, `total_attributed_volume`) from `agency_dashboard_rollups`

Interactive docs with request/response schemas: http://localhost:8080/docs

## Testing

The project includes backend unit tests, API integration tests, and frontend unit tests. Test services use the Docker Compose `test` profile with an ephemeral MySQL database (`test-db`). The current suite includes **186 backend tests** and **22 frontend tests** (report export/layout helpers, domain helpers, and API client utilities).

Run the full suite:

```powershell
docker compose --profile test rm -sf test-db
docker compose --profile test up -d test-db
.\scripts\run-tests.ps1
```

The test database uses a fresh MySQL container with `db/init.sql`. Recreate `test-db` after schema changes.

Run only backend unit tests (enforces 95% coverage on unit-testable helper modules: workflow, proposed cruise, passenger, audit, security, research email HTML, gemini context, and proposed cruise read assembly; request CRUD is covered by integration tests):

```powershell
.\scripts\run-tests.ps1 -Suite unit
```

Run only backend integration tests:

```powershell
.\scripts\run-tests.ps1 -Suite integration
```

Run only frontend tests:

```powershell
.\scripts\run-tests.ps1 -Suite frontend
```

Equivalent Docker commands:

```powershell
docker compose --profile test up -d test-db
docker compose --profile test run --rm backend-test
docker compose --profile test run --rm frontend-test
```

To run a subset of backend tests, pass arguments after the service name (dev dependencies are installed automatically):

```powershell
docker compose --profile test run --rm backend-test pytest tests/unit -q
```

Backend layout:

- `backend/tests/unit/` — domain/helper tests (workflow logic, cabin normalization, passenger activation, audit/security helpers, dashboard assembly, research email HTML, **reports service**, sales analytics, **agency invites**, **Bridge**, **auth**, multi-tenant schema)
- `backend/tests/integration/` — FastAPI endpoint tests against MySQL (auth, requests, communications, passenger reactivation, **reports endpoints**, **agency team**, **Bridge**, **multi-tenant isolation**)
- `backend/pytest.ini`, `backend/requirements-dev.txt`, `backend/.coveragerc` — pytest configuration, dev dependencies, and unit-test coverage scope

Frontend tests live beside source files as `*.test.ts` and run with Vitest (`apiClient.test.ts`, `domainHelpers.test.ts`, **manifest/supplier/funnel/advisor/passenger report export tests**).

Use `scripts/run-tests.ps1` as the recommended entry point; it starts `test-db` when needed and runs the selected suites.

## Database migrations

Fresh installs use `db/init.sql` via Docker entrypoint (includes multi-tenant Phases 0–2, Phase 3a rollups, per-cruise cabin-hold reservation IDs, and marketing campaigns with lead attribution). Existing volumes may need incremental migrations applied manually:

```powershell
# Auth (users table)
Get-Content db\migrate_auth.sql | docker compose exec -T db mysql -uroot -prootsecret sailspipeline

# Multi-tenant (run in order on older databases)
Get-Content db\migrate_multi_tenant_phase0.sql | docker compose exec -T db mysql -uroot -prootsecret sailspipeline
Get-Content db\migrate_multi_tenant_phase1.sql | docker compose exec -T db mysql -uroot -prootsecret sailspipeline
Get-Content db\migrate_multi_tenant_phase2.sql | docker compose exec -T db mysql -uroot -prootsecret sailspipeline
Get-Content db\migrate_multi_tenant_phase3_rollups.sql | docker compose exec -T db mysql -uroot -prootsecret sailspipeline
Get-Content db\migrate_proposed_cruise_reservation_ids.sql | docker compose exec -T db mysql -uroot -prootsecret sailspipeline
Get-Content db\migrate_marketing_campaigns.sql | docker compose exec -T db mysql -uroot -prootsecret sailspipeline
Get-Content db\migrate_marketing_campaign_rollups.sql | docker compose exec -T db mysql -uroot -prootsecret sailspipeline
Get-Content db\migrate_platform_operator_null_agency.sql | docker compose exec -T db mysql -uroot -prootsecret sailspipeline
Get-Content db\migrate_invitation_cancellation.sql | docker compose exec -T db mysql -uroot -prootsecret sailspipeline

# Other migrations (run as needed for older databases)
Get-Content db\migrate_questionnaire.sql | docker compose exec -T db mysql -uroot -prootsecret sailspipeline
Get-Content db\migrate_dashboard.sql | docker compose exec -T db mysql -uroot -prootsecret sailspipeline
Get-Content db\migrate_passengers.sql | docker compose exec -T db mysql -uroot -prootsecret sailspipeline
Get-Content db\migrate_passenger_registry.sql | docker compose exec -T db mysql -uroot -prootsecret sailspipeline
Get-Content db\migrate_cabins.sql | docker compose exec -T db mysql -uroot -prootsecret sailspipeline
Get-Content db\migrate_proposed_cruises.sql | docker compose exec -T db mysql -uroot -prootsecret sailspipeline
Get-Content db\migrate_quoted_insurance.sql | docker compose exec -T db mysql -uroot -prootsecret sailspipeline
Get-Content db\migrate_request_notes.sql | docker compose exec -T db mysql -uroot -prootsecret sailspipeline
Get-Content db\migrate_request_workflows.sql | docker compose exec -T db mysql -uroot -prootsecret sailspipeline
Get-Content db\migrate_attachments_to_files.sql | docker compose exec -T db mysql -uroot -prootsecret sailspipeline

docker compose restart backend
```

Replace `rootsecret` with your `MYSQL_ROOT_PASSWORD` if you changed it.

## Useful commands

```powershell
docker compose up --build
docker compose up -d backend          # after .env changes
docker compose down
docker compose logs -f backend
docker compose logs -f frontend
```
