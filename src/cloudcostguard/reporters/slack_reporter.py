"""
Slack Reporter: Sends rich Slack Block Kit notifications for CloudCostGuard audit alerts.
"""

import json
import urllib.request
from typing import Any, Dict, List

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from cloudcostguard.auditors.base import WasteItem


def send_slack_notification(items: List[WasteItem], webhook_url: str, dry_run: bool = True) -> bool:
    if not webhook_url:
        return False

    total_monthly = sum(i.estimated_monthly_waste for i in items)
    total_annual = total_monthly * 12.0
    item_count = len(items)

    status_tag = "🔍 [DRY RUN] AUDIT COMPLETED" if dry_run else "⚡ [ENFORCEMENT] REMEDIATION APPLIED"

    blocks: List[Dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🛡️ CloudCostGuard: AWS FinOps Waste Alert",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Status:*\n{status_tag}"},
                {"type": "mrkdwn", "text": f"*Resources Flagged:*\n`{item_count} items`"},
                {"type": "mrkdwn", "text": f"*Monthly Waste:*\n*${total_monthly:,.2f}*"},
                {"type": "mrkdwn", "text": f"*Projected Annual Waste:*\n*${total_annual:,.2f}*"},
            ],
        },
        {"type": "divider"},
    ]

    # Top waste items (up to 5 in slack notification to prevent message truncation)
    top_items = sorted(items, key=lambda x: x.estimated_monthly_waste, reverse=True)[:5]
    for item in top_items:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"• *{item.resource_type}* `{item.resource_id}` in `{item.region}`\n"
                        f"  _Condition:_ {item.status} ({item.details})\n"
                        f"  _Monthly Waste:_ *${item.estimated_monthly_waste:,.2f}* | _Action:_ {item.action_taken}"
                    ),
                },
            }
        )

    if len(items) > 5:
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"ℹ️ ...and {len(items) - 5} more resources. "
                            "View full HTML or CLI report for complete details."
                        ),
                    }
                ],
            }
        )

    payload = {"blocks": blocks}
    try:
        if HAS_REQUESTS:
            resp = requests.post(webhook_url, json=payload, timeout=10)
            return resp.status_code == 200
        else:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
    except Exception:
        return False
