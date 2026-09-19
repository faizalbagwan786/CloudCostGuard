"""
CLI Interface and AWS Lambda Entry Point for CloudCostGuard.
"""

import json
import os
import sys
from typing import List

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import boto3
import click
from rich.console import Console

from cloudcostguard.auditors import AUDITOR_REGISTRY, WasteItem
from cloudcostguard.config import ScanConfig
from cloudcostguard.lambda_handler import lambda_handler
from cloudcostguard.remediator import CloudCostRemediator
from cloudcostguard.reporters import generate_html_report, print_console_report, send_slack_notification

__all__ = ["main", "scan", "run_audit", "lambda_handler"]


def run_audit(config: ScanConfig) -> List[WasteItem]:
    all_items: List[WasteItem] = []

    session = boto3.Session() if not config.mock_mode else None

    for service_name in config.services:
        auditor_cls = AUDITOR_REGISTRY.get(service_name)
        if not auditor_cls:
            continue

        auditor = auditor_cls(session=session, config=config)

        # S3 is global
        if service_name == "s3":
            if config.mock_mode:
                all_items.extend(auditor.mock_audit("us-east-1"))
            else:
                all_items.extend(auditor.audit("us-east-1"))
            continue

        # Regional services
        for region in config.regions:
            if config.mock_mode:
                items = auditor.mock_audit(region)
            else:
                items = auditor.audit(region)
            all_items.extend(items)

    # Remediation step
    remediator = CloudCostRemediator(session=session, config=config)
    processed_items = remediator.remediate(all_items)

    return processed_items


@click.group()
@click.version_option(version="1.0.0", message="CloudCostGuard v%(version)s - by Faizal Bagwan")
def main():
    """🛡️ CloudCostGuard: AWS FinOps Cloud Cost Optimizer & Waste Elimination Suite"""
    pass


@main.command(name="scan")
@click.option(
    "--regions",
    default="us-east-1,ap-south-1,us-west-2",
    help="Comma-separated AWS regions to scan (e.g. us-east-1,ap-south-1).",
)
@click.option(
    "--services",
    default="ebs,eip,ec2,snapshots,elb,s3",
    help="Comma-separated services to audit: ebs,eip,ec2,snapshots,elb,s3 (or 'all').",
)
@click.option(
    "--demo",
    "--mock",
    "mock_mode",
    is_flag=True,
    default=False,
    help="Run in interactive simulation mode with synthetic data (no AWS credentials required).",
)
@click.option(
    "--dry-run/--no-dry-run",
    default=True,
    help="Run audit without performing state changes (Default: True).",
)
@click.option(
    "--apply-tags",
    is_flag=True,
    default=False,
    help="Apply CloudCostGuard cleanup tags to identified waste resources.",
)
@click.option(
    "--stop-idle-ec2",
    is_flag=True,
    default=False,
    help="Stop underutilized EC2 instances meeting idle criteria.",
)
@click.option(
    "--safety-opt-in",
    "--confirm-stop-ec2",
    "safety_opt_in",
    is_flag=True,
    default=False,
    help="Explicit safety confirmation required before stopping EC2 instances.",
)
@click.option(
    "--html",
    "html_path",
    type=click.Path(),
    default=None,
    help="Export executive HTML dashboard report to specified path.",
)
@click.option(
    "--json-output",
    "json_path",
    type=click.Path(),
    default=None,
    help="Export audit findings to JSON file.",
)
@click.option(
    "--slack-webhook",
    default=None,
    help="Slack incoming webhook URL for waste alert dispatch.",
)
def scan(
    regions: str,
    services: str,
    mock_mode: bool,
    dry_run: bool,
    apply_tags: bool,
    stop_idle_ec2: bool,
    safety_opt_in: bool,
    html_path: str,
    json_path: str,
    slack_webhook: str,
):
    """Audit AWS infrastructure for wasted spend and generate FinOps reports."""
    if stop_idle_ec2 and not safety_opt_in:
        raise click.UsageError(
            "--stop-idle-ec2 requires an explicit safety opt-in. "
            "Please provide '--safety-opt-in' (or '--confirm-stop-ec2') to authorize EC2 stopping."
        )

    region_list = [r.strip() for r in regions.split(",") if r.strip()]
    if services.lower() == "all":
        service_list = list(AUDITOR_REGISTRY.keys())
    else:
        service_list = [s.strip() for s in services.split(",") if s.strip() in AUDITOR_REGISTRY]

    config = ScanConfig(
        regions=region_list,
        services=service_list,
        dry_run=dry_run,
        apply_tags=apply_tags,
        stop_idle_ec2=stop_idle_ec2,
        safety_opt_in=safety_opt_in,
        mock_mode=mock_mode,
        html_report_path=html_path,
        json_report_path=json_path,
        slack_webhook_url=slack_webhook or os.getenv("SLACK_WEBHOOK_URL"),
    )

    console = Console()

    if not mock_mode:
        try:
            test_session = boto3.Session()
            sts = test_session.client("sts")
            caller = sts.get_caller_identity()
            account_id = caller.get("Account", "Unknown")
            arn = caller.get("Arn", "Unknown")
            console.print(f"[bold green]✓ Authenticated with AWS Account:[/] [cyan]{account_id}[/] ([dim]{arn}[/])\n")
        except Exception as err:
            console.print(f"\n[bold red]❌ AWS Authentication Error:[/] {err}\n")
            console.print(
                "[yellow]Could not authenticate with AWS. Please verify credentials via 'aws configure' "
                "or set AWS_ACCESS_KEY_ID & AWS_SECRET_ACCESS_KEY.[/yellow]"
            )
            console.print("[dim]To run without live AWS credentials, run in simulated demo mode:[/dim]")
            console.print("  [bold cyan]cloudcostguard scan --demo[/bold cyan]\n")
            sys.exit(1)

    with console.status("[bold cyan]Scanning AWS infrastructure for FinOps optimization opportunities...[/bold cyan]"):
        items = run_audit(config)

    # 1. Terminal Output
    print_console_report(items, dry_run=config.dry_run, mock_mode=config.mock_mode)

    # 2. HTML Export
    if html_path:
        out = generate_html_report(items, html_path, dry_run=config.dry_run, is_demo=config.mock_mode)
        console.print(f"[bold green]📊 Executive HTML Report saved to: [underline]{out}[/underline][/bold green]")

    # 3. JSON Export
    if json_path:
        parent_json_dir = os.path.dirname(json_path)
        if parent_json_dir:
            os.makedirs(parent_json_dir, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump([i.to_dict() for i in items], f, indent=2)
        console.print(f"[bold green]💾 JSON Audit Findings saved to: [underline]{json_path}[/underline][/bold green]")

    # 4. Slack Notification
    if config.slack_webhook_url:
        success = send_slack_notification(items, config.slack_webhook_url, dry_run=config.dry_run)
        if success:
            console.print("[bold green]💬 Slack Waste Alert dispatched successfully.[/bold green]")
        else:
            console.print("[bold yellow]⚠️ Failed to send Slack alert (check webhook URL).[/bold yellow]")


if __name__ == "__main__":
    main()
