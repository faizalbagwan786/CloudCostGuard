#!/usr/bin/env bash
# Run 1-click demo audit with CloudCostGuard
set -e

echo "=================================================="
echo "🛡️  Running CloudCostGuard Interactive Demo Scan"
echo "=================================================="

# Ensure PYTHONPATH is set
export PYTHONPATH="${PYTHONPATH}:./src"

mkdir -p reports

python -m cloudcostguard.cli scan \
  --demo \
  --regions us-east-1,ap-south-1,us-west-2 \
  --services all \
  --html reports/demo_audit_report.html \
  --json-output reports/demo_audit_findings.json

echo ""
echo "✅ Demo scan complete!"
echo "📄 HTML Report: reports/demo_audit_report.html"
echo "💾 JSON Output: reports/demo_audit_findings.json"
