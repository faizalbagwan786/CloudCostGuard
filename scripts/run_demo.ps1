$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " CloudCostGuard Interactive Demo Scan" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$env:PYTHONPATH = "$PSScriptRoot/../src;$env:PYTHONPATH"

New-Item -ItemType Directory -Force -Path "$PSScriptRoot/../reports" | Out-Null

python -m cloudcostguard.cli scan `
  --demo `
  --regions us-east-1,ap-south-1,us-west-2 `
  --services all `
  --html "$PSScriptRoot/../reports/demo_audit_report.html" `
  --json-output "$PSScriptRoot/../reports/demo_audit_findings.json"

Write-Host ""
Write-Host "[OK] Demo scan complete!" -ForegroundColor Green
Write-Host "  -> HTML Report: reports/demo_audit_report.html" -ForegroundColor Yellow
Write-Host "  -> JSON Output: reports/demo_audit_findings.json" -ForegroundColor Yellow
