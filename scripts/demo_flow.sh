#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"
TENANT_ID="${TENANT_ID:-default}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Starting docker compose stack"
docker compose up --build -d

echo "==> Running migrations with advisory lock"
docker compose exec -T backend python scripts/migrate.py

echo "==> Seeding superadmin (idempotent)"
docker compose exec -T backend python scripts/seed_superadmin.py

echo "==> Seeding pilot data (idempotent)"
docker compose exec -T backend python scripts/seed_pilot.py

echo "==> Checking backend smoke endpoints"
curl -sSf "$BASE_URL/health" >/dev/null
curl -sSf "$BASE_URL/version" >/dev/null
curl -sSf "$BASE_URL/db-test" >/dev/null
curl -sSf "$BASE_URL/docs" >/dev/null

echo "==> Checking frontend availability"
curl -sSf "$FRONTEND_URL" >/dev/null

echo "==> Checking DEV_AUTH_BYPASS flag inside backend"
DEV_BYPASS="$(docker compose exec -T backend python -c "from app.core.config import settings; print('true' if settings.DEV_AUTH_BYPASS else 'false')" | tail -n 1 | tr '[:upper:]' '[:lower:]')"

if [ "$DEV_BYPASS" = "true" ]; then
  echo "==> Running API smoke flow (dev bypass enabled)"
  BASE_URL="$BASE_URL" TENANT_ID="$TENANT_ID" bash "$SCRIPT_DIR/smoke_test.sh"
else
  echo "DEV_AUTH_BYPASS=false; skipping scripted auth flow."
fi

VERSION="$(curl -sS "$BASE_URL/version" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("version","unknown"))')"
echo ""
echo "DEMO READY"
echo "Backend:  $BASE_URL"
echo "Frontend: $FRONTEND_URL"
echo "Version:  $VERSION"
