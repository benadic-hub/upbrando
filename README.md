# Upbrando EMS Backend (Pilot)

FastAPI + PostgreSQL backend for an Employee Management Software pilot with humans + AI agents.

## Stack
- FastAPI (API-first, OpenAPI docs at `/docs`)
- SQLAlchemy Async + asyncpg
- Alembic migrations
- JWT auth (access + refresh)
- Google OAuth ID token login (company domain restricted)
- AWS S3 presigned uploads/downloads
- Docker + docker-compose

## Auth Mode
- Production auth is Google-only (`POST /api/v1/auth/google/login` with Google `id_token`).
- Password login is not supported.
- Session tokens are stored in HttpOnly cookies (`access` + `refresh`), not in browser JS storage.
- Production cookie policy: `Secure=true`, `HttpOnly=true`, `Domain=.upbrando.com`, and `SameSite=lax` (or `none` only if cross-site flows remain).
- Google onboarding is invite-only (except configured superadmin bootstrap/login paths).
- Bearer header fallback is available only in `ENV=dev`; production uses cookie sessions.
- Optional local helper is available only when `ENV=dev` and `DEV_AUTH_BYPASS=true`: `POST /api/v1/auth/dev/login`.

## Implemented Pilot Modules
- Auth (`Google OAuth`, invite-only onboarding, JWT refresh rotation, bootstrap superadmin)
- Tenanting (`tenant_id` in all core tables + `X-Tenant-ID` enforcement, default `default`)
- Org/Directory (departments, manager hierarchy, search + org chart)
- Time Clock (check-in/out, breaks, configurable per-user break/lunch/work hours, OT logic)
- Agents (agent profiles, tools_allowed, heartbeat, permission-check placeholder)
- Tasks (CRUD + status workflow)
- Helpdesk (ticket auto-creates task)
- Chat DM (threads/messages/unread counters/read markers)
- Announcements (admin post + read receipts)
- Knowledge Base (categories + article CRUD + title search)
- Forms (templates + encrypted submissions via Fernet)
- Attachments (S3 presign upload/download + metadata)
- Security (strict schemas, CORS allowlist, auth/chat rate limits, audit logs, admin IP allowlist)
- Ops (`/health`, `/db-test`, `/version`)

## Project Layout
```txt
app/
  api/            # shared deps + router composition
  core/           # settings, security, tenancy, rate limiter
  db/             # SQLAlchemy base/models/session
  modules/        # domain routers (auth, admin, org, tasks, etc.)
  schemas/        # Pydantic request/response models
  services/       # integrations + reusable domain services
alembic/          # migrations
scripts/          # operational scripts (migrate/seed/smoke/demo)
tests/            # minimal tests
frontend/         # Vite + React + TypeScript pilot UI
```

## Local Run (Docker)
1. Copy environment file:
```bash
cp .env.example .env
```
PowerShell alternative:
```powershell
Copy-Item .env.example .env
```

2. Start services:
```bash
docker compose up --build -d
```

3. Run migrations:
```bash
docker compose exec backend alembic upgrade head
```
Alternative (with advisory lock):
```bash
docker compose exec backend python scripts/migrate.py
```

4. Seed first superadmin (only works when no users exist):
```bash
docker compose exec backend python scripts/seed_superadmin.py
```

5. Seed pilot data (idempotent):
```bash
docker compose exec backend python scripts/seed_pilot.py
```

6. Open API docs:
- `http://localhost:8000/docs`

7. Open frontend:
- `http://localhost:5173`
  - Configure Google client id for frontend sign-in:
    - `frontend/.env`: `VITE_GOOGLE_CLIENT_ID=<google web client id>`
    - compose default maps `GOOGLE_CLIENT_ID` into frontend container
  - If `5173` is occupied on your machine, run web on `5175` and set API CORS origin to `http://localhost:5175`.

## Local Run (without Docker)
1. Install Python 3.11 and PostgreSQL.
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Set `DATABASE_URL` to local postgres in `.env`.
4. Run migrations:
```bash
alembic upgrade head
```
5. Start API:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Superadmin Bootstrap Options
- Script: `python scripts/seed_superadmin.py`
- One-time endpoint: `POST /api/v1/bootstrap/superadmin`
  - Requires no users in DB.
  - Requires body email/password matching `SUPERADMIN_EMAIL` + `SUPERADMIN_PASSWORD`.
  - If `OFFICE_IP_ALLOWLIST` is set, caller IP must match allowlist.

## Key Curl Flows
Use tenant header in all protected routes:
```bash
-H "X-Tenant-ID: default"
```

1. Health + version + DB:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/version
curl http://localhost:8000/db-test
```

2. Bootstrap superadmin (one-time):
```bash
curl -X POST http://localhost:8000/api/v1/bootstrap/superadmin \
  -H "Content-Type: application/json" \
  -d '{
    "email":"superadmin@upbrando.com",
    "password":"ChangeMeNow_UseStrongPassword",
    "full_name":"Pilot Superadmin"
  }'
```

3. Google login:
```bash
curl -c cookies.txt -b cookies.txt -X POST http://localhost:8000/api/v1/auth/google/login \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: default" \
  -d '{"id_token":"<google-id-token>"}'
```

3b. Dev helper login (local only, gated by `ENV=dev` + `DEV_AUTH_BYPASS=true`):
```bash
curl -c cookies.txt -b cookies.txt -X POST http://localhost:8000/api/v1/auth/dev/login \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: default" \
  -d '{"email":"superadmin@upbrando.com","full_name":"Super Admin"}'
```

4. Refresh token:
```bash
curl -c cookies.txt -b cookies.txt -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "X-Tenant-ID: default"
```

5. Current user:
```bash
curl -b cookies.txt http://localhost:8000/api/v1/auth/me \
  -H "X-Tenant-ID: default"
```

6. Logout:
```bash
curl -c cookies.txt -b cookies.txt -X POST http://localhost:8000/api/v1/auth/logout \
  -H "X-Tenant-ID: default"
```

7. Create department (admin):
```bash
curl -X POST http://localhost:8000/api/v1/admin/departments \
  -b cookies.txt \
  -H "X-Tenant-ID: default" \
  -H "Content-Type: application/json" \
  -d '{"name":"Engineering","description":"Core engineering department"}'
```

8. Invite user (admin, invite-only onboarding):
```bash
curl -X POST http://localhost:8000/api/v1/admin/invites \
  -b cookies.txt \
  -H "X-Tenant-ID: default" \
  -H "Content-Type: application/json" \
  -d '{
    "email":"employee@upbrando.com",
    "full_name":"Employee One",
    "role":"EMPLOYEE",
    "expires_in_days":7
  }'
```

9. Create helpdesk ticket (auto-creates task):
```bash
curl -X POST http://localhost:8000/api/v1/helpdesk/tickets \
  -b cookies.txt \
  -H "X-Tenant-ID: default" \
  -H "Content-Type: application/json" \
  -d '{"title":"VPN not working","description":"Cannot connect from home"}'
```

10. Pilot status (admin-authenticated):
```bash
curl http://localhost:8000/ops/pilot-status \
  -b cookies.txt \
  -H "X-Tenant-ID: default"
```

## Smoke Tests
PowerShell (Windows):
```powershell
./scripts/smoke_test.ps1
```

Shell (Linux/macOS):
```bash
bash ./scripts/smoke_test.sh
```

End-to-end demo (build + migrate + seed + checks):
- PowerShell: `./scripts/demo_flow.ps1`
- Bash: `bash ./scripts/demo_flow.sh`

## Rate Limiting
- Auth endpoints: `RATE_LIMIT_AUTH_REQUESTS` per `RATE_LIMIT_WINDOW_SECONDS`
- Chat endpoints: `RATE_LIMIT_CHAT_REQUESTS` per `RATE_LIMIT_WINDOW_SECONDS`
- Current backend: in-memory (designed to be swappable)

## Deployment Runbook (AWS App Runner + RDS + S3)
Detailed production runbooks:
- AWS backend: [DEPLOY_AWS.md](DEPLOY_AWS.md)
- Vercel frontend: [DEPLOY_VERCEL.md](DEPLOY_VERCEL.md)
- GoDaddy DNS: [DNS_GODADDY.md](DNS_GODADDY.md)
- Google OAuth setup: [GOOGLE_OAUTH.md](GOOGLE_OAUTH.md)

Target production hosts:
- Frontend: `https://www.upbrando.com`
- API: `https://api.upbrando.com`

Google OAuth production settings:
- Authorized JavaScript origins:
  - `https://www.upbrando.com`
  - `http://localhost:5173`
- Authorized redirect URI:
  - If your GIS integration uses redirect mode, add the exact callback URL used by your frontend.
- Backend verification:
  - `GOOGLE_CLIENT_ID` must match the frontend GIS client id.
  - Backend strictly verifies `aud`, `iss`, token integrity, and `email_verified`.

## Production Verification Checklist (WWW Only)
Browser checks:
1. Open `https://www.upbrando.com`.
2. Click Google Sign-In.
3. In DevTools -> Network, confirm auth request URL:
   - `https://www.upbrando.com/api/v1/auth/google/login`
4. Verify response includes `Set-Cookie` with:
   - `HttpOnly`
   - `Secure`
   - `Domain=.upbrando.com`
5. Verify `https://www.upbrando.com/api/v1/auth/me` returns `200` after login.
6. Clear cookies and verify `https://www.upbrando.com/api/v1/auth/me` returns `401`.
7. Logout via `POST https://www.upbrando.com/api/v1/auth/logout` and verify cookies are cleared.

Curl checks (production):
```bash
curl -I https://www.upbrando.com
curl -i https://www.upbrando.com/api/v1/health
curl -i https://www.upbrando.com/api/v1/version
curl -i https://www.upbrando.com/api/v1/db-test
```

## Notes
- Do not commit real secrets in `.env`.
- Auth uses Argon2 for password hashing (no bcrypt 72-byte issue).
- Sensitive form responses are encrypted at rest with Fernet key.
- Frontend uses HttpOnly cookies (`credentials: include`) and does not store JWTs in localStorage/sessionStorage.
- Browser check: open DevTools -> Network -> request headers and confirm cookies are sent for `/api/v1/**`.
