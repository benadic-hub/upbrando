# GoDaddy DNS Runbook (`www.upbrando.com` + `api.upbrando.com`)

This setup supports WWW-only public usage:
- Users browse `https://www.upbrando.com`
- Browser API calls hit `https://www.upbrando.com/api/...`
- Vercel rewrites to backend origin `https://api.upbrando.com/api/...`

## 1) `www.upbrando.com` -> Vercel
1. In Vercel:
   - Project -> Settings -> Domains -> add `www.upbrando.com`.
   - Copy DNS value Vercel provides (often `cname.vercel-dns.com` or a project-specific CNAME target).
2. In GoDaddy DNS:
   - Type: `CNAME`
   - Host: `www`
   - Points to: `<value from Vercel>`
   - TTL: `600` seconds during setup (increase later if desired).

## 2) Optional apex redirect (`upbrando.com` -> `www.upbrando.com`)
Recommended so users always end up on `www`:
1. In GoDaddy domain forwarding:
   - Forward `https://upbrando.com` to `https://www.upbrando.com`
   - Type: Permanent (301)
2. If you use DNS-level apex handling instead, follow Vercel’s apex-domain instructions.

## 3) `api.upbrando.com` -> AWS App Runner
1. In AWS App Runner:
   - Service -> Custom domains -> add `api.upbrando.com`.
   - Copy all DNS records AWS provides:
     - service target CNAME
     - validation CNAME records (if shown)
2. In GoDaddy DNS:
   - Type: `CNAME`
   - Host: `api`
   - Points to: `<App Runner target>`
   - TTL: `600` seconds
3. Add validation records exactly as App Runner specifies.

## 4) Avoid Conflicts
- Remove conflicting `A`/`AAAA`/`CNAME` records for `www` and `api`.
- Keep only the records required by Vercel and App Runner.

## 5) Verification
After propagation:

```powershell
nslookup www.upbrando.com
nslookup api.upbrando.com

curl.exe -I https://www.upbrando.com
curl.exe -I https://api.upbrando.com/health
curl.exe -I https://www.upbrando.com/api/v1/health
```

Expected:
- `www.upbrando.com` resolves to Vercel and returns HTTPS.
- `api.upbrando.com/health` returns `200`.
- `www.upbrando.com/api/v1/health` returns backend health via Vercel rewrite.

## 6) SSL
- Vercel issues/manages SSL for `www.upbrando.com`.
- App Runner issues/manages SSL for `api.upbrando.com`.
- Wait for both certificate statuses to become active before go-live.
