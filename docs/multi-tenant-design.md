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
| **2** | Planned | Agency provisioning, invites, per-agency username policy |
| **3** | Planned | Per-agency analytics rollups, operational tooling |

---

## Tenant model

| Concept | Implementation |
|---------|----------------|
| **Tenant** | `agencies` row (`CHAR(36)` UUID) |
| **Default agency** | `00000000-0000-4000-8000-000000000001` / slug `default` |
| **Root scoped tables** | `users`, `travel_requests`, `passengers` |
| **Child scoped tables (Phase 1)** | `proposed_cruises`, `request_notes`, `request_workflows`, `request_tasks`, `request_communications`, `call_transcripts`, `chat_logs`, `request_research_documents`, `quoted_insurance` |

---

## Auth and request context

1. **Login** issues JWT with `sub` (username) and `agency_id`.
2. **`TenantContextMiddleware`** decodes the JWT and sets tenant context before sync route handlers run (required because FastAPI runs dependencies and handlers in separate worker threads).
3. **`get_current_user`** validates username + agency against `users`.
4. **`get_db`** clears tenant context when the request finishes.

Unauthenticated routes (login, register, health) run without tenant context.

---

## Defense in depth

| Layer | Behavior |
|-------|----------|
| **ORM session filter** | `with_loader_criteria` on all tenant-scoped models when `agency_id` context is set |
| **Route/service checks** | `agency_service.get_travel_request_for_agency`, `require_record_for_agency`, `assert_child_belongs_to_request` → **404 Not found.** |
| **Attachment paths** | Files stored under `{agency_id}/requests/{request_id}/{kind}/...`; `resolve_attachment_path` blocks traversal and wrong-agency prefixes |
| **Reports / analytics** | Explicit `.filter(Model.agency_id == current_user.agency_id)` on all aggregation queries |

---

## Data stamping on write

| Path | `agency_id` source |
|------|-------------------|
| User registration / seed admin | Default agency |
| New travel request | `current_user.agency_id` |
| Child records (notes, workflows, cruises, attachments, …) | Parent `travel_request.agency_id` |
| New passenger / client | `require_current_agency_id()` |
| Client import rows | Tenant context from authenticated import route |

---

## Schema and migrations

**Fresh installs** use `db/init.sql` (includes Phase 0 + Phase 1 columns and indexes).

**Existing local Docker MySQL volume** (one-time, already applied on dev):

```powershell
Get-Content db\migrate_multi_tenant_phase0.sql | docker compose exec -T db mysql -u<user> -p<pass> cruisetravelnow
Get-Content db\migrate_multi_tenant_phase1.sql | docker compose exec -T db mysql -u<user> -p<pass> cruisetravelnow
```

After Phase 1 SQL, move on-disk attachments from `uploads/requests/...` to `uploads/{agency_id}/requests/...` to match updated `stored_path` values.

**Automated tests** use a disposable `test-db` container built from `init.sql`:

```powershell
docker compose --profile test rm -sf test-db
docker compose --profile test up -d test-db
docker compose --profile test run --rm backend-test
```

---

## Verification

- [x] Login returns `user.agency_id` in `/api/auth/me`
- [x] Cross-tenant request and passenger IDs return 404 (`tests/integration/test_multi_tenant.py`)
- [x] Open-request lists exclude other agencies' data
- [x] Request detail, attachments, reports, and analytics respect tenant scope

---

## Phase 2 preview

- Agency admin UI and provisioning API
- Invite / onboarding flow for additional agencies
- Policy for per-agency vs global username/email uniqueness
