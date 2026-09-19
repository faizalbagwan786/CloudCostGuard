"""
Standalone AWS Lambda Handler for CloudCostGuard.
Has ZERO third-party CLI dependencies (no Click, no Rich), allowing direct
deployment on vanilla AWS Lambda Python 3.12 runtime with only boto3.
"""

import logging
import os
from typing import Any, Dict, List

import boto3

from cloudcostguard.auditors import AUDITOR_REGISTRY, WasteItem
from cloudcostguard.config import ScanConfig
from cloudcostguard.remediator import CloudCostRemediator
from cloudcostguard.reporters.slack_reporter import send_slack_notification

logger = logging.getLogger("cloudcostguard.lambda")
logger.setLevel(logging.INFO)


def run_lambda_audit(config: ScanConfig) -> List[WasteItem]:
    all_items: List[WasteItem] = []
    session = boto3.Session()

    for service_name in config.services:
        auditor_cls = AUDITOR_REGISTRY.get(service_name)
        if not auditor_cls:
            continue

        auditor = auditor_cls(session=session, config=config)

        if service_name == "s3":
            if config.mock_mode:
                all_items.extend(auditor.mock_audit("us-east-1"))
            else:
                all_items.extend(auditor.audit("us-east-1"))
            continue

        for region in config.regions:
            if config.mock_mode:
                items = auditor.mock_audit(region)
            else:
                items = auditor.audit(region)
            all_items.extend(items)

    remediator = CloudCostRemediator(session=session, config=config)
    processed_items = remediator.remediate(all_items)
    return processed_items


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda entry point for scheduled EventBridge or manual invocation.
    """
    logger.info("Starting CloudCostGuard FinOps audit execution")

    # Read from Lambda event overrides or fallback to environment variables
    regions_str = (
        event.get("regions")
        if isinstance(event, dict) and event.get("regions")
        else os.getenv("AWS_SCAN_REGIONS", "us-east-1,ap-south-1")
    )
    slack_webhook = (
        event.get("slack_webhook_url")
        if isinstance(event, dict) and event.get("slack_webhook_url")
        else os.getenv("SLACK_WEBHOOK_URL")
    )
    dry_run_val = (
        event.get("dry_run")
        if isinstance(event, dict) and "dry_run" in event
        else os.getenv("DRY_RUN", "true")
    )
    dry_run = str(dry_run_val).lower() in ("true", "1", "yes")

    apply_tags_val = (
        event.get("apply_tags")
        if isinstance(event, dict) and "apply_tags" in event
        else os.getenv("APPLY_TAGS", "false")
    )
    apply_tags = str(apply_tags_val).lower() in ("true", "1", "yes")

    stop_idle_ec2_val = (
        event.get("stop_idle_ec2")
        if isinstance(event, dict) and "stop_idle_ec2" in event
        else os.getenv("STOP_IDLE_EC2", "false")
    )
    stop_idle_ec2 = str(stop_idle_ec2_val).lower() in ("true", "1", "yes")

    safety_opt_in_val = (
        event.get("safety_opt_in")
        if isinstance(event, dict) and "safety_opt_in" in event
        else os.getenv("SAFETY_OPT_IN", "false")
    )
    safety_opt_in = str(safety_opt_in_val).lower() in ("true", "1", "yes")

    mock_mode_val = event.get("mock_mode", False) if isinstance(event, dict) else False

    region_list = [r.strip() for r in regions_str.split(",") if r.strip()]

    config = ScanConfig(
        regions=region_list,
        services=list(AUDITOR_REGISTRY.keys()),
        dry_run=dry_run,
        apply_tags=apply_tags,
        stop_idle_ec2=stop_idle_ec2,
        safety_opt_in=safety_opt_in,
        mock_mode=bool(mock_mode_val),
        slack_webhook_url=slack_webhook,
    )

    items = run_lambda_audit(config)
    total_monthly = sum(i.estimated_monthly_waste for i in items)

    logger.info(
        f"Audit completed: {len(items)} waste items identified, "
        f"${total_monthly:,.2f} projected monthly waste."
    )

    if slack_webhook:
        dispatched = send_slack_notification(items, slack_webhook, dry_run=dry_run)
        logger.info(f"Slack notification dispatched: {dispatched}")

    return {
        "statusCode": 200,
        "body": {
            "waste_count": len(items),
            "estimated_monthly_waste_usd": round(total_monthly, 2),
            "projected_annual_waste_usd": round(total_monthly * 12.0, 2),
            "dry_run": dry_run,
            "regions_scanned": region_list,
        },
    }
