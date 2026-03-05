# Apps/API Local Guide

## Ports
- Web (Vite): `http://localhost:5175` (recommended on this machine)
- API (Express): `http://localhost:5174`
- API prefix: `/api/v1`

If `5173` is occupied (common on Docker Desktop/WSL setups), run web with:

```bash
pnpm --dir apps/web dev --port 5175
```

## Default Dev Admin
- Email: `admin@upbrando.local`
- Password: `Admin@12345`

## Auth Cookies
- Login sets HttpOnly cookies: `sid` and `sid_refresh`.
- Frontend sends cookies with `credentials: "include"`.
- `GET /api/v1/auth/me` returns `401` if cookies/session are missing or invalid.

## Run Locally
1. Install:
```bash
pnpm install
```
2. Create API env:
```bash
cp apps/api/.env.example apps/api/.env
```
3. Generate Prisma client:
```bash
pnpm --dir apps/api db:generate
```
4. Apply migrations:
```bash
pnpm --dir apps/api db:migrate
```
5. Seed data:
```bash
pnpm --dir apps/api db:seed
```
6. Run API + Web:
```bash
pnpm --dir apps/api dev
pnpm --dir apps/web dev --port 5175
```

## Troubleshooting
- CORS blocked:
  - Ensure `CORS_ORIGIN=http://localhost:5175` in `apps/api/.env`.
- Cookies not persisted:
  - Keep `AUTH_COOKIE_SECURE=false` and `AUTH_COOKIE_SAMESITE=lax` in local dev.
  - Verify frontend requests still use `credentials: "include"`.
- Prisma setup:
  - Ensure `DATABASE_URL=file:./dev.db` in `apps/api/.env`.
  - Re-run `db:migrate`, then `db:seed`.
  - If `db:generate` fails with EPERM, stop running API process and retry.
