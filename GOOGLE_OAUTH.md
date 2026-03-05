# Google OAuth Setup (WWW-Only)

This project uses Google Identity Services (GIS) with backend ID token verification.

Public frontend:
- `https://www.upbrando.com`

Local frontend:
- `http://localhost:5173`

## 1) Create OAuth Client
1. Open Google Cloud Console.
2. Select project (or create one).
3. Go to:
   - APIs & Services -> Credentials
4. Create Credentials -> OAuth client ID.
5. Application type:
   - Web application

## 2) Configure Allowed Origins (Required)
Set Authorized JavaScript origins to:
- `https://www.upbrando.com`
- `http://localhost:5173`

Do not use `app.upbrando.com`.

## 3) Configure Redirect URIs (Only if redirect mode is used)
If your GIS flow is popup/credential mode, redirect URIs may not be needed.
If redirect mode is enabled, add exact callback URI(s) used by your frontend.

## 4) Copy Client ID
Copy the generated OAuth Web Client ID.

Set env vars:
- Backend: `GOOGLE_CLIENT_ID=<same_client_id>`
- Frontend: `VITE_GOOGLE_CLIENT_ID=<same_client_id>`

These values must match.

## 5) Backend Validation Expectations
Backend login endpoint verifies:
- token signature/integrity
- `aud == GOOGLE_CLIENT_ID`
- issuer is Google
- token not expired
- `email_verified=true`
- company domain/allowlist policy
- invite-only onboarding policy

## 6) Verification Checklist (Screenshots Recommended)
Capture screenshots of:
1. OAuth client details page with correct origins.
2. Vercel env variable `VITE_GOOGLE_CLIENT_ID`.
3. Backend env variable `GOOGLE_CLIENT_ID` in App Runner.
4. Browser Network request:
   - `POST https://www.upbrando.com/api/v1/auth/google/login`
5. Successful `GET https://www.upbrando.com/api/v1/auth/me` after login.

## 7) Common Failures
- `Invalid Google token`:
  - wrong client id in backend or frontend
- `Google account email is not allowed`:
  - email domain/allowlist restriction triggered
- login works locally but not prod:
  - missing `https://www.upbrando.com` in authorized origins
