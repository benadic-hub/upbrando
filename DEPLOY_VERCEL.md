# Vercel Deployment Runbook (WWW-Only Frontend + API Rewrite)

Public entrypoint:
- `https://www.upbrando.com`

Technical backend origin:
- `https://api.upbrando.com`

Browser requirement:
- frontend calls only `https://www.upbrando.com/api/...`
- Vercel rewrites `/api/*` to `https://api.upbrando.com/api/*`

## 1) Create / Connect Vercel Project
1. Go to Vercel dashboard.
2. Import this repository.
3. Set root directory to `frontend`.
4. Framework preset: `Vite`.

## 2) Confirm Rewrite Config
This repo includes:
- `frontend/vercel.json`

Expected rewrite:
```json
{
  "source": "/api/:path*",
  "destination": "https://api.upbrando.com/api/:path*"
}
```

WebSocket note:
- Vercel rewrites cover standard HTTP API traffic.
- If you later expose chat WebSocket endpoints, test them explicitly; route WS directly to `wss://api.upbrando.com/...` if rewrite behavior is insufficient.

## 3) Configure Vercel Env Vars
Set in Vercel Project -> Settings -> Environment Variables:

```txt
VITE_API_BASE_URL=https://www.upbrando.com
VITE_GOOGLE_CLIENT_ID=<prod_google_oauth_web_client_id>
```

Use same values for Production and Preview unless you explicitly separate environments.

## 4) Deploy
1. Trigger deploy.
2. Wait for successful build.
3. Open generated Vercel URL and verify app shell loads.

## 5) Attach Custom Domain
1. Vercel -> Project -> Settings -> Domains.
2. Add `www.upbrando.com`.
3. Copy DNS values Vercel provides.
4. Configure GoDaddy records (see `DNS_GODADDY.md`).

## 6) Verification (WWW Only)
At `https://www.upbrando.com`:
1. Google sign-in button appears.
2. Login request goes to:
   - `https://www.upbrando.com/api/v1/auth/google/login`
3. Request is rewritten to backend origin by Vercel.
4. Response includes auth cookies for `.upbrando.com`.
5. `/api/v1/auth/me` on `www` returns 200 after login.
6. Logout clears cookies and `/api/v1/auth/me` returns 401.

## 7) Troubleshooting
- If login fails:
  - verify `VITE_GOOGLE_CLIENT_ID`.
  - verify Google OAuth origins include `https://www.upbrando.com`.
- If API calls fail:
  - verify `frontend/vercel.json` rewrite exists and deployed.
- If cookie/session fails:
  - backend prod cookie config must be:
    - `AUTH_COOKIE_SECURE=true`
    - `AUTH_COOKIE_DOMAIN=.upbrando.com`
    - `AUTH_COOKIE_SAMESITE=lax` (recommended with same-site rewrite)
