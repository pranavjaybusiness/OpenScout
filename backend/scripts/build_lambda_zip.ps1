# Build openscout-lambda.zip for AWS Lambda (Linux deps via Docker).
# Prereqs: Docker Desktop running, new PowerShell after install.

$ErrorActionPreference = "Stop"
$BackendRoot = Split-Path -Parent $PSScriptRoot
Set-Location $BackendRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "docker not found. Start Docker Desktop, then open a NEW PowerShell window and run this script again." -ForegroundColor Red
    exit 1
}

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker is not running. Start Docker Desktop and wait until it says Running." -ForegroundColor Red
    exit 1
}

Write-Host "Building Lambda zip (may take a few minutes on first run)..." -ForegroundColor Cyan

$buildCmd = "set -e; rm -rf /var/task/package /var/task/openscout-lambda.zip; pip install -q -r /var/task/requirements.txt -t /var/task/package; cp -r /var/task/src /var/task/package/; cd /var/task/package && zip -qr /var/task/openscout-lambda.zip ."
docker run --rm -v "${BackendRoot}:/var/task" public.ecr.aws/sam/build-python3.12 /bin/bash -lc $buildCmd

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$zip = Join-Path $BackendRoot "openscout-lambda.zip"
$mb = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Host "Done: $zip ($mb MB)" -ForegroundColor Green
Write-Host "Upload this file in Lambda -> Code -> Upload from .zip file"
