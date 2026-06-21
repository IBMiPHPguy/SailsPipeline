# SailsPipeline — Performance & Multi-Tenant Pre-Flight Audit

**Executive Summary**  
**Date:** June 20, 2026  
**Scope:** Database schema (`db/init.sql` + migrations), ORM models, request/passenger/report/analytics services, auth, and file-attachment patterns.

> **Update (June 2026):** Phases 0 and 1 of multi-tenant isolation are implemented. See `[multi-tenant-design.md](multi-tenant-design.md)` for the current architecture. This document remains a historical pre-flight snapshot of gaps that existed before that work.

---

## Overview

The relational schema is **well-normalized with foreign-key constraints** for the core CRM graph (requests → passengers, cruises, workflows, communications). That is a solid foundation for a **single-agency** deployment.

The codebase is **not multi-tenant ready**. There is no `tenant_id` or `agency_id`, no row-level isolation, and every authenticated user can read the full dataset. Reports and Sales Analytics **load entire tables into Python** and filter in memory — acceptable at seed scale, but a scaling bottleneck before you add tenants.

---

## Status at a Glance


| Category               | Status          | Headline                                                            |
| ---------------------- | --------------- | ------------------------------------------------------------------- |
| Schema & FK integrity  | 🟢 Mostly ready | Strong FK coverage and cascade deletes across the CRM graph         |
| Multi-tenant isolation | 🔴 Blocker      | No tenant column, no query scoping, shared passenger registry       |
| Indexing               | 🟡 Gap          | No secondary indexes beyond PK/UNIQUE                               |
| Reports & analytics    | 🔴 / 🟡         | Full-table scans + in-memory filtering on hot paths                 |
| File storage           | 🟢 Mostly ready | Transcripts, chat logs, and research docs on disk via `stored_path` |


---

## 🟢 Ready for scale (single agency)

- **FK coverage** — Requests, passengers, proposed cruises, workflows, communications, notes, audits, and attachments use explicit foreign keys with appropriate cascade behavior.
- **Junction tables** — `request_passengers` and `proposed_cruise_passengers` use composite unique keys for correct many-to-many modeling.
- **Attachment offload** — Call transcripts, chat logs, and research documents store `stored_path` on the filesystem, not as DB blobs.
- **Paginated list endpoints** — Closed-request search and client registry paginate in SQL with `LIMIT`/`OFFSET`.
- **Detail-view loading** — Request workspace uses eager loading to avoid N+1 queries when opening a single request.

---

## 🟡 Fix soon (performance & hardening)

- **No secondary indexes** — Add indexes on high-frequency filters: `travel_requests(status, created_at, created_by_id)`, `proposed_cruises(status, cruise_line, travel_request_id)`, `passengers(is_active, state_or_province)`, and audit lookup columns.
- **Missing FK** — `request_passenger_audits.request_passenger_id` has no FK to `request_passengers`.
- **Advisor identity** — Reports group by `User.username` strings rather than stable relational IDs.
- **Large TEXT in-row** — Communication bodies, note content, audit snapshots, and `itinerary_details` still live in the database; defer or split for list/report queries.
- **JSON qualifiers** — Passenger qualifier filtering cannot use B-tree indexes without normalization or generated columns.

---

## 🔴 Critical — block multi-tenant until resolved

### Data isolation

- **No `agency_id` / `tenant_id`** anywhere in schema or application code.
- **Auth validates identity only** — JWT login does not scope queries to an agency.
- **Global data access** — Lists, dashboard, reports, analytics, and passenger registry query the full dataset with no ownership filter.
- **Shared passenger registry** — All agencies would share one `passengers` table; email/phone collisions and cross-agency visibility are likely.
- **No global query filter** — SQLAlchemy session has no `with_loader_criteria` or equivalent tenant hook.

### Query anti-patterns at scale

- **Reports engine** — `_reports_query(db).all()` loads every request with cruises and workflow tasks, then filters in Python. All five reports and Excel export repeat this pattern.
- **Passenger demographics** — Loads all passengers, filters qualifiers/state in Python.
- **Sales Analytics** — Multiple full-table scans of `proposed_cruises` and `travel_requests` per dashboard load.

### Storage

- **Attachment paths** — `stored_path` has no agency prefix; shared storage needs `{agency_id}/...` paths and ownership checks on download.

---

## Minimum multi-tenant requirements

Before safely hosting multiple agencies on one database:

1. Add `**agencies`** table and `**agency_id**` on `**users**`, `**travel_requests**`, and `**passengers**` (P0).
2. Enforce **API-layer ownership checks** on every read/write by ID.
3. Implement **session-level global query filtering** (e.g. SQLAlchemy `with_loader_criteria`).
4. Scope **file storage paths** per agency.
5. Rewrite **reports and analytics** to filter and paginate in SQL, scoped by `agency_id`.

---

## Recommended priority roadmap


| Phase       | Work                                                                         | Blocks multi-tenant?          |
| ----------- | ---------------------------------------------------------------------------- | ----------------------------- |
| **Phase 0** | `agencies` + `agency_id` on root tables; auth scoping; global query filter   | **Yes**                       |
| **Phase 1** | Secondary indexes; SQL-filtered paginated reports/analytics                  | No (required for performance) |
| **Phase 2** | Audit FK; advisor relational IDs; deferred/lazy large TEXT columns           | No                            |
| **Phase 3** | Analytics rollup tables; cached meta endpoints; tenant-scoped object storage | No                            |


---

## Bottom line

**Safe today:** Single-agency deployment with moderate data volume — schema integrity and file offload are in good shape.

**Fix before multi-tenant:** Introduce and enforce `agency_id` across data, queries, and storage. Without that, multiple agencies on one database will cause **data bleed**.

**Fix before scale:** Add indexes and move report/analytics filtering from Python into SQL. Current full-table load patterns will degrade linearly as request and passenger counts grow.

---

*Full audit detail available in project conversation history (schema tables, index DDL, service-level findings, and ORM filter patterns).*