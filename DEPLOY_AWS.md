# AWS Deployment Runbook (App Runner + RDS + S3)

Target production API:
- `https://api.upbrando.com`

Frontend (Vercel) origin:
- `https://www.upbrando.com`

## 1) Prerequisites
- AWS CLI configured (`aws configure`)
- Docker installed
- IAM permissions for ECR, App Runner, RDS, S3, IAM, CloudWatch Logs
- Domain managed in GoDaddy (or Route53)

## 2) Create ECR Repo
```powershell
aws ecr create-repository --repository-name upbrando-backend --region ap-south-1
```

## 3) Build + Push Backend Image
Replace `<account-id>` and `<tag>`:

```powershell
$ACCOUNT_ID="<account-id>"
$REGION="ap-south-1"
$REPO="upbrando-backend"
$TAG="v1"

aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

docker build -t "$REPO:$TAG" .
docker tag "$REPO:$TAG" "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO:$TAG"
docker push "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO:$TAG"
```

## 4) Create RDS PostgreSQL
Recommended pilot baseline:
- Engine: PostgreSQL 15+
- Enable automated backups
- Multi-AZ optional for pilot
- Security group:
  - Inbound: `5432` only from trusted sources (App Runner egress / VPC connector SG / office IP)
  - No open `0.0.0.0/0` if avoidable

Connection URL format:
```txt
postgresql+asyncpg://<db_user>:<db_password>@<rds-endpoint>:5432/<db_name>
```

## 5) Create S3 Bucket (Private)
```powershell
aws s3api create-bucket --bucket upbrando-ems-attachments --region ap-south-1 --create-bucket-configuration LocationConstraint=ap-south-1
aws s3api put-public-access-block --bucket upbrando-ems-attachments --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

Grant App Runner role permissions:
- `s3:PutObject`
- `s3:GetObject`
- `s3:ListBucket`
for bucket `upbrando-ems-attachments`.

## 6) Create App Runner Service
In AWS Console:
1. App Runner -> Create service
2. Source: ECR
3. Image: `upbrando-backend:<tag>`
4. Port: `8000`
5. Instance role: attach S3 permissions
6. Health check path: `/health`

## 7) Required App Runner Env Vars (Production)
Set these explicitly:

```txt
ENV=prod
PORT=8000
APP_NAME=Upbrando EMS Backend
APP_VERSION=1.0.0
API_PREFIX=/api/v1
DEFAULT_TENANT_ID=default
MIGRATE_ON_START=false

DATABASE_URL=postgresql+asyncpg://<user>:<password>@<rds-endpoint>:5432/<db>

JWT_SECRET=<strong_32+_char_secret>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_MINUTES=30
REFRESH_TOKEN_DAYS=14
FERNET_KEY=<fernet_key>

GOOGLE_CLIENT_ID=<prod_google_web_client_id>
COMPANY_EMAIL_DOMAIN=upbrando.com
COMPANY_EMAIL_ALLOWLIST=

CORS_ALLOWED_ORIGINS=https://www.upbrando.com

AUTH_ACCESS_COOKIE_NAME=ems_access_token
AUTH_REFRESH_COOKIE_NAME=ems_refresh_token
AUTH_COOKIE_SAMESITE=lax
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_DOMAIN=.upbrando.com

RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_AUTH_REQUESTS=10
RATE_LIMIT_CHAT_REQUESTS=60

DEV_AUTH_BYPASS=false
OFFICE_IP_ALLOWLIST=

S3_BUCKET=upbrando-ems-attachments
S3_REGION=ap-south-1
S3_ENDPOINT_URL=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
S3_FORCE_PATH_STYLE=false
PRESIGNED_URL_EXPIRES_SECONDS=900
MAX_UPLOAD_BYTES=26214400
ATTACHMENTS_ALLOWED_CONTENT_TYPES=image/png,image/jpeg,application/pdf,text/plain

SUPERADMIN_EMAIL=superadmin@upbrando.com
SUPERADMIN_PASSWORD=
```

Notes:
- Do not use `*` in `CORS_ALLOWED_ORIGINS`.
- `DEV_AUTH_BYPASS` stays `false` in prod.
- Cookie policy for prod is mandatory: `Secure=true`, `Domain=.upbrando.com`.
- `AUTH_COOKIE_SAMESITE=lax` is recommended with Vercel `/api` rewrites (same-site browser requests).
- Use `AUTH_COOKIE_SAMESITE=none` only if cross-site calls remain.

## 8) Migrations Strategy
Use one approach:

1. Manual (recommended):
   - Start service with `MIGRATE_ON_START=false`
   - Run one-off migrate job/command:
   ```powershell
   python scripts/migrate.py
   ```

2. Automatic on startup:
   - Temporarily set `MIGRATE_ON_START=true`
   - Deploy once
   - Confirm logs
   - Set back to `false`

`scripts/migrate.py` uses Postgres advisory lock to reduce concurrent migration risk.

## 9) App Runner Verification
```powershell
curl.exe https://<apprunner-default-domain>/health
curl.exe https://<apprunner-default-domain>/version
curl.exe https://<apprunner-default-domain>/db-test
```

## 10) Attach Custom API Domain
In App Runner:
1. Add custom domain `api.upbrando.com`
2. Copy required validation + target DNS values
3. Add records in GoDaddy (see `DNS_GODADDY.md`)

## 11) Post-Deploy Functional Checks
1. `https://api.upbrando.com/health` returns 200
2. Frontend login from `https://www.upbrando.com`
3. Verify public API path through Vercel rewrite:
   - `https://www.upbrando.com/api/v1/health` returns 200
3. Browser devtools:
   - Auth request is made to `https://www.upbrando.com/api/v1/auth/google/login`
   - `Set-Cookie` contains `HttpOnly`, `Secure`, `Domain=.upbrando.com`
   - `https://www.upbrando.com/api/v1/auth/me` succeeds with cookies

## 12) Google OAuth Production Console Settings
In Google Cloud Console (OAuth 2.0 Client ID used by frontend GIS + backend verification):
- Authorized JavaScript origins:
  - `https://www.upbrando.com`
  - `http://localhost:5173`
- Authorized redirect URIs:
  - Add only if your frontend uses redirect UX mode; include the exact callback URL.
- Ensure backend `GOOGLE_CLIENT_ID` exactly matches frontend `VITE_GOOGLE_CLIENT_ID`.
