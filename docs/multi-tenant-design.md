# SailsPipeline Multi-Tenant Design

**Last updated:** June 2026  
**Deployment:** Local Docker only (single default agency in daily use)

---

## Overview

SailsPipeline isolates CRM data by **agency** (`agency_id`, UUID). All authenticated API traffic is scoped to the agency encoded in the JWT. Cross-tenant access to records by ID returns **HTTP 404** (no existence leak).

| Phase | Status | Summary |
|-------|--------|---------|
| **0** | Complete | Root tables, JWT claims, ORM read filter, default agency backfill |
| **1** | Complete | Child-table `agency_id`, route-level ownership checks, tenant attachment paths, reports/analytics SQL scoping |
| **2** | Complete | Onboarding schema, roles, invitation ledgers, Team workspace, agent onboarding, subscription gatekeeper, user deactivation |
| **3** | Planned | Per-agency analytics rollups, operational tooling |

---

## Tenant model

| Concept | Implementation |
|---------|----------------|
| **Tenant** | `agencies` row (`CHAR(36)` UUID) |
| **Login handle** | `agencies.organization_handle` (unique slug, e.g. `bluehorizon`) |
| **Subscription** | `agencies.subscription_state`: Active, Trialing, Past Due, Locked |
| **Default agency** | `00000000-0000-4000-8000-000000000001` / handle `default` |
| **Root scoped tables** | `users`, `travel_requests`, `passengers` |
| **Child scoped tables (Phase 1)** | `proposed_cruises`, `request_notes`, `request_workflows`, `request_tasks`, `request_communications`, `call_transcripts`, `chat_logs`, `request_research_documents`, `quoted_insurance` |

---

## User roles (Phase 2)

| Role | Purpose |
|------|---------|
| `platform_super_admin` | Cross-tenant access to **The Bridge** (platform admin portal) |
| `tenant_super_user` | Agency owner; team management, invites, full agency visibility |
| `tenant_agent` | Sub-agent or independent contractor within one agency |

Permission columns on `users`:

- `is_active` — instant access revocation; inactive users cannot sign in but remain in the database for reporting
- `can_view_all_agency_leads` — future restriction for contractors who should only see assigned leads

Per-agency email uniqueness: `UNIQUE (agency_id, email)`.

---

## Invitation ledgers (Phase 2)

### `platform_invitations` — The Bridge

Platform super-admins provision new tenant companies. Columns include `target_agency_name`, `target_organization_handle`, `invite_email`, secure `token`, `is_used`, `expires_at`, and `cancelled_at`.

### `agency_invitations` — tenant team scaling

Tenant super users invite sub-agents from the CRM **Team** workspace. Scoped by `agency_id`, with `role` defaulting to `tenant_agent`. Invitations expire after 3 days and can be revoked before acceptance (`cancelled_at`).

---

## Auth and request context

1. **Login** accepts `organization_handle`, `username`, and `password`. The API resolves the agency by handle, then authenticates the user within that tenant. Inactive users are rejected at login.
2. **Login** issues JWT with `user_id`, `agency_id`, `role`, and `sub` (username).
3. **`TenantContextMiddleware`** decodes the JWT and sets tenant context before sync route handlers run.
4. **`get_current_user`** validates `user_id`, `agency_id`, `role`, and `is_active` against `users`.
5. **`/api/auth/me`** returns `role`, `is_active`, and `can_view_all_agency_leads`.

Unauthenticated routes (login, register, health) run without tenant context.

CRM and Bridge use separate browser tokens (`sailspipeline_crm_token` / `sailspipeline_bridge_token`) so both portals can stay open in different tabs.

---

## Subscription gatekeeper (Phase 2)

`SubscriptionGatekeeperMiddleware` returns **HTTP 402** when an agency's `subscription_state` is **Past Due** or **Locked**, blocking most CRM API routes.

| Still allowed when locked | Blocked when locked |
|---------------------------|---------------------|
| `/api/auth/me`, logout | Dashboard, requests, passengers, reports |
| Subscription restore page data | Team invites and other write paths |

The frontend redirects 402 responses to `/subscription-restore`.

---

## Defense in depth

| Layer | Behavior |
|-------|----------|
| **ORM session filter** | `with_loader_criteria` on all tenant-scoped models when `agency_id` context is set |
| **Route/service checks** | `agency_service` helpers → **404 Not found.** |
| **Attachment paths** | `{agency_id}/requests/{request_id}/{kind}/...` |
| **Reports / analytics** | Explicit `agency_id` filters on all aggregation queries |

---

## Phase 2 CRM Team workspace

Tenant super users open **Team** in the CRM sidebar.

| Capability | API / UI |
|------------|----------|
| List agency users and pending invites | `GET /api/agency/team` |
| Issue team invitation | `POST /api/agency/invites` → `/register-agent?token=…` |
| Revoke pending invitation | `DELETE /api/agency/invites/{id}` |
| Edit user email, role, active flag | `PATCH /api/agency/users/{user_id}` |
| Deactivate / reactivate user | Same PATCH (`is_active`); table actions + confirmation modal |
| Filter users by status | Team UI: Active only (default), Inactive only, or both |

Agent onboarding:

1. `GET /api/onboarding/agent/invites/verify?token=…`
2. `POST /api/onboarding/agent/accept` — creates `tenant_agent` (or invited role) under the issuing agency

Self-service rules: a super user cannot deactivate their own account or change their own role via PATCH.

---

## Schema and migrations

**Fresh installs** use `db/init.sql` (Phases 0–2 onboarding columns).

**Existing local Docker MySQL volume** (one-time, as needed):

```powershell
Get-Content db\migrate_multi_tenant_phase2.sql | docker compose exec -T db mysql -u<user> -p<pass> cruisetravelnow
Get-Content db\migrate_invitation_cancellation.sql | docker compose exec -T db mysql -u<user> -p<pass> cruisetravelnow
```

Prior phases: `migrate_multi_tenant_phase0.sql`, `migrate_multi_tenant_phase1.sql`.

**Automated tests** use disposable `test-db` from `init.sql`:

```powershell
docker compose --profile test rm -sf test-db
docker compose --profile test up -d test-db
docker compose --profile test run --rm backend-test
```

---

## Verification checklist

### Phase 0–1 (unchanged)

- [x] Login returns `user.agency_id` and `user.role` in `/api/auth/me`
- [x] Cross-tenant request and passenger IDs return 404
- [x] Reports and dashboard queries scoped by `agency_id`

### Phase 2 — roles and auth

- [x] CRM login requires `organization_handle` + username + password
- [x] Team sidebar link visible only to `tenant_super_user`
- [x] `GET /api/agency/team` returns 403 for `tenant_agent`
- [x] JWT and `/api/auth/me` reject inactive users
- [x] Inactive agency users cannot sign in (`is_active = false`)

### Phase 2 — agency team

- [x] Super user issues agency invite; token verifies at `/api/onboarding/agent/invites/verify`
- [x] Agent accepts invite at `/register-agent`; new user appears on team list
- [x] Super user revokes pending invite (`DELETE /api/agency/invites/{id}` → status Cancelled)
- [x] Invitations expire after 3 days
- [x] Super user PATCHes user role, email, and `is_active`
- [x] Self-deactivation and self-role change blocked
- [x] Team UI: deactivate/reactivate with confirmation; filter Active / Inactive / both (default Active)

### Phase 2 — subscription gatekeeper

- [x] Locked or Past Due agency receives HTTP 402 on protected CRM routes
- [x] `/api/auth/me` still works when subscription is Past Due or Locked
- [x] Frontend 402 handler navigates to subscription restore page

### Phase 2 — The Bridge

- [x] Bridge provisioning UI and onboarding APIs (`POST /api/bridge/invites`, `/register?token=…`)
- [x] Platform invitation revoke; tenant detail and subscription update from Bridge

---

## The Bridge

Platform operators with `platform_super_admin` open `/bridge` to issue tenant invitations and review the agency ledger.

1. `POST /api/bridge/invites` creates a `platform_invitations` row and returns `/register?token=…`
2. Owners complete onboarding at `/register`, which provisions `agencies` + `tenant_super_user` in one transaction

Seed a local Bridge operator via `SEED_BRIDGE_ADMIN_USERNAME` / `SEED_BRIDGE_ADMIN_PASSWORD` in `.env`.

---

## Phase 3 (planned)

- Per-agency analytics rollups
- Operational tooling (bulk tenant actions, audit exports)
