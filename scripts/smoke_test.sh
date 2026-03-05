#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
TENANT_ID="${TENANT_ID:-default}"
COOKIE_JAR="$(mktemp)"
trap 'rm -f "$COOKIE_JAR"' EXIT

echo "==> Checking health/version/db-test"
curl -sSf "$BASE_URL/health" >/dev/null
curl -sSf "$BASE_URL/version" >/dev/null
curl -sSf "$BASE_URL/db-test" >/dev/null

echo "==> Dev login (requires DEV_AUTH_BYPASS=true)"
LOGIN_JSON="$(curl -sS -X POST "$BASE_URL/api/v1/auth/dev/login" \
  -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{"email":"superadmin@cossmicrings.com","full_name":"Super Admin"}')"

LOGIN_OK="$(python3 -c 'import json,sys; print("true" if json.load(sys.stdin).get("ok") else "false")' <<<"$LOGIN_JSON")"
if [ "$LOGIN_OK" != "true" ]; then
  echo "Dev login failed. Ensure DEV_AUTH_BYPASS=true in local .env"
  exit 1
fi

AUTH=(-c "$COOKIE_JAR" -b "$COOKIE_JAR" -H "X-Tenant-ID: $TENANT_ID" -H "Content-Type: application/json")
STAMP="$(date +%Y%m%d%H%M%S)"
DEPT_NAME="SmokeDept_$STAMP"

echo "==> Checking /ops/pilot-status"
curl -sS "$BASE_URL/ops/pilot-status" "${AUTH[@]}" >/dev/null

echo "==> Create department"
DEPT_JSON="$(curl -sS -X POST "$BASE_URL/api/v1/org/departments" "${AUTH[@]}" \
  -d "{\"name\":\"$DEPT_NAME\",\"description\":\"Smoke department $STAMP\"}")"
DEPT_ID="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"$DEPT_JSON")"

echo "==> Create invite"
INVITE_EMAIL="smoke.invite.$STAMP@cossmicrings.com"
INVITE_JSON="$(curl -sS -X POST "$BASE_URL/api/v1/admin/invites" "${AUTH[@]}" \
  -d "{\"email\":\"$INVITE_EMAIL\",\"full_name\":\"Smoke Invite $STAMP\",\"role\":\"EMPLOYEE\",\"department_id\":\"$DEPT_ID\",\"manager_id\":null,\"tools_allowed\":[],\"expires_in_days\":7}")"
INVITE_ID="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"$INVITE_JSON")"

echo "==> List users / create one if needed"
USERS_JSON="$(curl -sS "$BASE_URL/api/v1/org/users" "${AUTH[@]}")"
TARGET_USER_ID="$(python3 - <<'PY' "$USERS_JSON"
import json
import sys
rows = json.loads(sys.argv[1])
for row in rows:
    if row.get("email") != "superadmin@cossmicrings.com":
        print(row["id"])
        break
else:
    print("")
PY
)"

if [ -z "$TARGET_USER_ID" ]; then
  NEW_EMAIL="smoke.user.$STAMP@cossmicrings.com"
  USER_JSON="$(curl -sS -X POST "$BASE_URL/api/v1/admin/users" "${AUTH[@]}" \
    -d "{\"email\":\"$NEW_EMAIL\",\"full_name\":\"Smoke User $STAMP\",\"role\":\"EMPLOYEE\",\"department_id\":\"$DEPT_ID\",\"manager_id\":null,\"tools_allowed\":[],\"is_active\":true,\"employee_type\":\"HUMAN\"}")"
  TARGET_USER_ID="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"$USER_JSON")"
fi

echo "==> Create task"
TASK_JSON="$(curl -sS -X POST "$BASE_URL/api/v1/tasks" "${AUTH[@]}" \
  -d "{\"title\":\"Smoke task $STAMP\",\"description\":\"Created by smoke test\",\"status\":\"TODO\",\"assignee_user_id\":\"$TARGET_USER_ID\",\"due_at\":null}")"
TASK_ID="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"$TASK_JSON")"

echo "==> Clock-in / clock-out"
set +e
curl -sS -X POST "$BASE_URL/api/v1/timeclock/clock-in" "${AUTH[@]}" -d '{"source":"smoke","notes":"clock-in"}' >/dev/null
curl -sS -X POST "$BASE_URL/api/v1/timeclock/clock-out" "${AUTH[@]}" -d '{"notes":"clock-out"}' >/dev/null
set -e

echo "==> Create chat thread + message"
THREAD_JSON="$(curl -sS -X POST "$BASE_URL/api/v1/chat/threads" "${AUTH[@]}" \
  -d "{\"is_group\":false,\"user_id\":\"$TARGET_USER_ID\",\"member_ids\":[],\"title\":null}")"
THREAD_ID="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"$THREAD_JSON")"
MESSAGE_JSON="$(curl -sS -X POST "$BASE_URL/api/v1/chat/threads/$THREAD_ID/messages" "${AUTH[@]}" \
  -d "{\"content\":\"Smoke message $STAMP\"}")"
MESSAGE_ID="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"$MESSAGE_JSON")"

echo "Smoke test passed"
echo "Department created: $DEPT_NAME"
echo "Invite id: $INVITE_ID"
echo "Task id: $TASK_ID"
echo "Message id: $MESSAGE_ID"
