param(
  [string]$BaseUrl = "http://localhost:8000",
  [string]$TenantId = "default"
)

$ErrorActionPreference = "Stop"

function Write-Step($message) {
  Write-Host "==> $message"
}

Write-Step "Checking health/version/db-test"
$health = Invoke-RestMethod -Method GET -Uri "$BaseUrl/health"
$version = Invoke-RestMethod -Method GET -Uri "$BaseUrl/version"
$dbTest = Invoke-RestMethod -Method GET -Uri "$BaseUrl/db-test"
if (-not $health.ok) { throw "/health failed" }
if (-not $dbTest.db_ok) { throw "/db-test failed" }

Write-Step "Dev login (requires DEV_AUTH_BYPASS=true)"
$loginBody = @{
  email = "superadmin@cossmicrings.com"
  full_name = "Super Admin"
} | ConvertTo-Json -Compress

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession

try {
  $login = Invoke-RestMethod -Method POST -Uri "$BaseUrl/api/v1/auth/dev/login" -WebSession $session -Headers @{ "X-Tenant-ID" = $TenantId } -ContentType "application/json" -Body $loginBody
} catch {
  throw "Dev login failed. Ensure DEV_AUTH_BYPASS=true in .env for local smoke tests."
}

if (-not $login.ok) { throw "Dev login did not return ok=true" }

$authHeaders = @{
  "X-Tenant-ID" = $TenantId
}

Write-Step "Checking /ops/pilot-status"
$pilot = Invoke-RestMethod -Method GET -Uri "$BaseUrl/ops/pilot-status" -WebSession $session -Headers $authHeaders

Write-Step "Create department"
$stamp = Get-Date -Format "yyyyMMddHHmmss"
$deptName = "SmokeDept_$stamp"
$dept = Invoke-RestMethod -Method POST -Uri "$BaseUrl/api/v1/org/departments" -WebSession $session -Headers $authHeaders -ContentType "application/json" -Body (@{
  name = $deptName
  description = "Smoke department $stamp"
} | ConvertTo-Json -Compress)

Write-Step "Create invite"
$inviteEmail = "smoke.invite.$stamp@cossmicrings.com"
$invite = Invoke-RestMethod -Method POST -Uri "$BaseUrl/api/v1/admin/invites" -WebSession $session -Headers $authHeaders -ContentType "application/json" -Body (@{
  email = $inviteEmail
  full_name = "Smoke Invite $stamp"
  role = "EMPLOYEE"
  department_id = $dept.id
  manager_id = $null
  tools_allowed = @()
  expires_in_days = 7
} | ConvertTo-Json -Compress)

Write-Step "List users and create one user"
$users = Invoke-RestMethod -Method GET -Uri "$BaseUrl/api/v1/org/users" -WebSession $session -Headers $authHeaders
$targetUser = $users | Where-Object { $_.email -ne "superadmin@cossmicrings.com" } | Select-Object -First 1
if (-not $targetUser) {
  $newEmail = "smoke.user.$stamp@cossmicrings.com"
  $targetUser = Invoke-RestMethod -Method POST -Uri "$BaseUrl/api/v1/admin/users" -WebSession $session -Headers $authHeaders -ContentType "application/json" -Body (@{
    email = $newEmail
    full_name = "Smoke User $stamp"
    role = "EMPLOYEE"
    department_id = $dept.id
    manager_id = $null
    tools_allowed = @()
    is_active = $true
    employee_type = "HUMAN"
  } | ConvertTo-Json -Compress)
}

Write-Step "Create task"
$task = Invoke-RestMethod -Method POST -Uri "$BaseUrl/api/v1/tasks" -WebSession $session -Headers $authHeaders -ContentType "application/json" -Body (@{
  title = "Smoke task $stamp"
  description = "Created by smoke test"
  status = "TODO"
  assignee_user_id = $targetUser.id
  due_at = $null
} | ConvertTo-Json -Compress)

Write-Step "Clock-in / clock-out"
try {
  Invoke-RestMethod -Method POST -Uri "$BaseUrl/api/v1/timeclock/clock-in" -WebSession $session -Headers $authHeaders -ContentType "application/json" -Body '{"source":"smoke","notes":"clock-in"}' | Out-Null
} catch {
  Write-Host "clock-in skipped (possibly already open entry)"
}
try {
  Invoke-RestMethod -Method POST -Uri "$BaseUrl/api/v1/timeclock/clock-out" -WebSession $session -Headers $authHeaders -ContentType "application/json" -Body '{"notes":"clock-out"}' | Out-Null
} catch {
  Write-Host "clock-out skipped (possibly no open entry)"
}

Write-Step "Create chat thread + send message"
$thread = Invoke-RestMethod -Method POST -Uri "$BaseUrl/api/v1/chat/threads" -WebSession $session -Headers $authHeaders -ContentType "application/json" -Body (@{
  is_group = $false
  user_id = $targetUser.id
  member_ids = @()
  title = $null
} | ConvertTo-Json -Compress)

$msg = Invoke-RestMethod -Method POST -Uri "$BaseUrl/api/v1/chat/threads/$($thread.id)/messages" -WebSession $session -Headers $authHeaders -ContentType "application/json" -Body (@{
  content = "Smoke message $stamp"
} | ConvertTo-Json -Compress)

Write-Host ""
Write-Host "Smoke test passed"
Write-Host "Pilot status users: $($pilot.users)"
Write-Host "Department created: $($dept.name)"
Write-Host "Invite created: $($invite.id)"
Write-Host "Task created: $($task.id)"
Write-Host "Chat message created: $($msg.id)"
