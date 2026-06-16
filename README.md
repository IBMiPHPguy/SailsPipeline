# CruiseTravelNow

Web app for managing cruise travel requests from intake through research, client communication, and booking prep.

Agents use a workflow-driven workspace for each open request: capture client details, upload research, propose cruises, draft and send communications, track follow-ups, record client decisions, and close or reopen requests as needed.

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
| http://localhost:8080 | App (via Nginx) |
| http://localhost:5173 | Frontend dev server |
| http://localhost:8080/docs | OpenAPI / Swagger docs |
| localhost:3306 | MySQL |

4. Sign in with the seeded admin account from `.env`:

- Username: `admin`
- Password: value of `SEED_ADMIN_PASSWORD` in `.env`

You can also register a new account from the Register tab. Passwords must be more than 10 characters and include at least one uppercase letter, one lowercase letter, one numeral, and one special character. Spaces are not allowed.

## Application overview

### Dashboard

The signed-in home screen shows:

- **Open requests** — active travel requests with destination, dates, and workflow context
- **Stale requests** — open requests with no activity in 3+ days (`STALE_DAYS`)
- **Closed requests** — clickable tile that opens the closed-requests list

Each open request row shows the next open workflow task, last worked timestamp, and whether it is stale.

### Travel requests

Each request stores client contact info, destination (with region-specific details), travel dates, cabin preferences, qualifiers, and cabin count. Requests can be **Open** or **Closed** with a close reason.

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

### Passengers

- Add passengers manually or link from the shared passenger registry
- Search existing passengers with `GET /api/passengers/search`
- Primary passenger contact fields sync back to the request header
- Passenger field changes are audited

### Proposed cruises and quoted insurance

**Proposed cruises** support Proposed, Accepted, and Rejected statuses. The UI splits them into **Proposed & accepted** and **Rejected** sub-tabs.

- Add cruises manually or bulk-generate from a research document (Gemini)
- When one cruise is accepted, adding more proposed cruises is hidden
- Accepted/rejected state drives workflow outcomes in **Record client response**

**Quoted insurance** tracks Proposed, Accepted, and Declined quotes. Adding new quotes is hidden once a proposed cruise has been accepted.

### Notes, attachments, and communications

- **Notes** — free-text notes with AI-generated summaries and change history
- **Call transcripts** and **chat logs** — uploaded as `.txt` files, stored on disk under `ATTACHMENTS_DIR`
- **Research documents** — `.txt` uploads used for AI extraction and new research cycles
- **Communications** — draft/sent/archived messages (research proposal, follow-up, booking, agency, etc.)

### Workflows

Each open request has at most one **active** workflow at a time. Completing the Research workflow automatically starts **Communicate Research** as a linked successor workflow.

Workflow templates:

| Workflow | Purpose |
| --- | --- |
| Research | Research options, upload findings, create proposals, draft communication |
| Communicate Research | Send proposal, follow up, record client response |
| Enter Trip in CRM | Post-booking checklist (passenger verification, CRM steps, payments, OBC) |

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
3. **Record client response** — accept one proposed cruise or reject all options:
   - **Accept:** remaining proposed cruises are auto-rejected; save is available once every proposed cruise has a decision
   - **Reject all:** choose to close the request (with close reason) or start a new Research workflow (requires uploading a new research document first). **Purchased - Trip Created** is hidden when all cruises are rejected

When a cruise is accepted, the Communicate Research workflow can complete and the **Enter Trip in CRM** workflow can be started manually.

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

- `POST /api/auth/register` — create a new user
- `POST /api/auth/login` — returns a JWT access token
- `GET /api/auth/me` — current signed-in user
- All other `/api/*` endpoints require authentication

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

## Environment variables

See `.env.example` for defaults.

| Variable | Purpose |
| --- | --- |
| `MYSQL_*` | Database credentials |
| `JWT_SECRET`, `JWT_EXPIRE_MINUTES` | Auth token signing |
| `SEED_ADMIN_*` | Initial admin user created on startup |
| `ATTACHMENTS_DIR` | Upload root inside the backend container |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Optional AI integration |
| `*_PORT` | Host ports for nginx, frontend, backend |

Change `JWT_SECRET`, database passwords, and the seeded admin password before deploying outside local development.

## API endpoints

All routes below require authentication unless noted.

### Health and auth

- `GET /api/health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`

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

### Passengers

- `GET /api/passengers/search?q=&limit=`
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
- `POST /api/requests/{id}/communications/generate-from-proposals`
- `POST /api/requests/{id}/research-documents`
- `GET /api/requests/{id}/research-documents/{document_id}/content`

Interactive docs with request/response schemas: http://localhost:8080/docs

## Database migrations

Fresh installs use `db/init.sql` via Docker entrypoint. Existing volumes may need incremental migrations applied manually:

```powershell
# Auth (users table)
Get-Content db\migrate_auth.sql | docker compose exec -T db mysql -uroot -prootsecret cruisetravelnow

# Other migrations (run as needed for older databases)
Get-Content db\migrate_questionnaire.sql | docker compose exec -T db mysql -uroot -prootsecret cruisetravelnow
Get-Content db\migrate_dashboard.sql | docker compose exec -T db mysql -uroot -prootsecret cruisetravelnow
Get-Content db\migrate_passengers.sql | docker compose exec -T db mysql -uroot -prootsecret cruisetravelnow
Get-Content db\migrate_passenger_registry.sql | docker compose exec -T db mysql -uroot -prootsecret cruisetravelnow
Get-Content db\migrate_cabins.sql | docker compose exec -T db mysql -uroot -prootsecret cruisetravelnow
Get-Content db\migrate_proposed_cruises.sql | docker compose exec -T db mysql -uroot -prootsecret cruisetravelnow
Get-Content db\migrate_quoted_insurance.sql | docker compose exec -T db mysql -uroot -prootsecret cruisetravelnow
Get-Content db\migrate_request_notes.sql | docker compose exec -T db mysql -uroot -prootsecret cruisetravelnow
Get-Content db\migrate_request_workflows.sql | docker compose exec -T db mysql -uroot -prootsecret cruisetravelnow
Get-Content db\migrate_attachments_to_files.sql | docker compose exec -T db mysql -uroot -prootsecret cruisetravelnow

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
