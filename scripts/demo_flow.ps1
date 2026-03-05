param(
  [string]$BaseUrl = "http://localhost:8000",
  [string]$FrontendUrl = "http://localhost:5173",
  [string]$TenantId = "default"
)

$ErrorActionPreference = "Stop"

function Write-Step($message) {
  Write-Host "==> $message"
}

Write-Step "Starting docker compose stack"
docker compose up --build -d

Write-Step "Running migrations with advisory lock"
docker compose exec -T backend python scripts/migrate.py

Write-Step "Seeding superadmin (idempotent)"
docker compose exec -T backend python scripts/seed_superadmin.py

Write-Step "Seeding pilot data (idempotent)"
docker compose exec -T backend python scripts/seed_pilot.py

Write-Step "Checking backend smoke endpoints"
$health = Invoke-RestMethod -Method GET -Uri "$BaseUrl/health"
$version = Invoke-RestMethod -Method GET -Uri "$BaseUrl/version"
$dbTest = Invoke-RestMethod -Method GET -Uri "$BaseUrl/db-test"
$docs = Invoke-WebRequest -UseBasicParsing -Method GET -Uri "$BaseUrl/docs"
if (-not $health.ok) { throw "/health failed" }
if (-not $dbTest.db_ok) { throw "/db-test failed" }
if ($docs.StatusCode -ne 200) { throw "/docs failed with status $($docs.StatusCode)" }

Write-Step "Checking frontend availability"
$frontend = Invoke-WebRequest -UseBasicParsing -Method GET -Uri $FrontendUrl
if ($frontend.StatusCode -ne 200) {
  throw "Frontend check failed with status $($frontend.StatusCode)"
}

Write-Step "Checking DEV_AUTH_BYPASS flag inside backend"
$devBypassRaw = docker compose exec -T backend python -c "from app.core.config import settings; print('true' if settings.DEV_AUTH_BYPASS else 'false')"
$devBypass = ($devBypassRaw | Select-Object -Last 1).Trim().ToLower()

if ($devBypass -eq "true") {
  Write-Step "Running API smoke flow (dev bypass enabled)"
  & "$PSScriptRoot\\smoke_test.ps1" -BaseUrl $BaseUrl -TenantId $TenantId
} else {
  Write-Host "DEV_AUTH_BYPASS=false; skipping scripted auth flow."
}

Write-Host ""
Write-Host "DEMO READY"
Write-Host "Backend:  $BaseUrl"
Write-Host "Frontend: $FrontendUrl"
Write-Host "Version:  $($version.version)"
