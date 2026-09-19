"""
Remediator: Executes safe tagging and automated remediation policies on identified waste items.
"""

from datetime import datetime, timezone
from typing import List, Tuple

from cloudcostguard.auditors.base import WasteItem
from cloudcostguard.config import ScanConfig


class CloudCostRemediator:
    def __init__(self, session=None, config: ScanConfig = None):
        self.session = session
        self.config = config or ScanConfig()

    def can_stop_ec2(self, item: WasteItem) -> Tuple[bool, str]:
        """
        Evaluates whether an EC2 instance can be safely stopped according to strict guardrails:
        1. Safety opt-in must be explicitly granted (--safety-opt-in).
        2. Instance must not be untagged.
        3. Instance must have an explicit allowlist tag (e.g. CloudCostGuard:AutoStop=true).
        4. Instance must NOT be production or live.
        5. Instance must NOT have protection tags (DoNotStop, Protected, Critical, Compliance).
        6. Instance must be in a verified non-production environment.
        """
        if item.resource_type != "EC2 Instance":
            return False, "Not an EC2 instance"

        if not self.config.stop_idle_ec2:
            return False, "EC2 auto-stop not enabled"

        if not self.config.safety_opt_in:
            return False, "Safety opt-in not granted (requires explicit --safety-opt-in)"

        if not item.tags:
            return False, "Untagged instance (missing explicit allowlist tag 'CloudCostGuard:AutoStop=true')"

        tags_lower = {str(k).strip().lower(): str(v).strip().lower() for k, v in item.tags.items()}

        # 1. Explicit allowlist check
        target_key = self.config.autostop_tag_key.lower()
        target_val = self.config.autostop_tag_value.lower()
        if tags_lower.get(target_key) != target_val:
            return False, (
                f"Non-allowlisted instance (requires tag "
                f"'{self.config.autostop_tag_key}={self.config.autostop_tag_value}')"
            )

        # 2. Production protection check
        env_val = tags_lower.get("environment", "") or tags_lower.get("env", "")
        if any(p in env_val for p in ["prod", "production", "live"]):
            return False, "Production instance protected from automated stopping"

        # 3. Protected / critical tags check
        for prot_key in ["donotstop", "protected", "critical", "compliance", "retain"]:
            if prot_key in tags_lower:
                val = tags_lower[prot_key]
                if val not in ("false", "0", "no"):
                    return False, f"Protected instance guardrail active (tag '{prot_key}' detected)"

        # 4. Verified non-production environment
        non_prod_envs = [
            "dev", "development", "test", "testing", "staging",
            "stage", "sandbox", "nonprod", "non-prod", "demo", "lab"
        ]
        if env_val not in non_prod_envs:
            return False, "Ambiguous environment (requires explicit non-prod Environment tag, e.g. 'dev' or 'staging')"

        return True, "Authorized for auto-stop"

    def remediate(self, items: List[WasteItem]) -> List[WasteItem]:
        """
        Execute configured remediation actions on items.
        If dry_run is True, updates item.action_taken with what WOULD happen.
        """
        for item in items:
            # 1. Apply Tagging policy
            if self.config.apply_tags:
                if self.config.dry_run:
                    item.action_taken = f"[DryRun] Would tag with {self.config.tag_key}"
                elif self.config.mock_mode:
                    item.action_taken = f"Tagged: {self.config.tag_key}={self.config.tag_value}"
                elif not self.session:
                    item.action_taken = "Skipped (No active AWS session)"
                else:
                    try:
                        ec2 = self.session.client("ec2", region_name=item.region)
                        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                        tags_to_apply = [
                            {"Key": self.config.tag_key, "Value": self.config.tag_value},
                            {"Key": "CloudCostGuard:IdentifiedDate", "Value": today_str},
                            {"Key": "CloudCostGuard:EstMonthlyWaste", "Value": str(item.estimated_monthly_waste)},
                        ]
                        if item.resource_type in ["EBS Volume", "EC2 Instance", "Snapshot"]:
                            ec2.create_tags(Resources=[item.resource_id], Tags=tags_to_apply)
                            item.action_taken = f"Tagged: {self.config.tag_key}"
                        else:
                            item.action_taken = "Tagging not supported for type"
                    except Exception as e:
                        item.action_taken = f"Failed: {str(e)[:30]}..."

            # 2. Stop idle EC2 instances (with strict safety opt-in and allowlist guardrails)
            elif self.config.stop_idle_ec2 and item.resource_type == "EC2 Instance":
                can_stop, reason = self.can_stop_ec2(item)
                if not can_stop:
                    prefix = "[DryRun] " if self.config.dry_run else ""
                    item.action_taken = f"{prefix}Skipped ({reason})"
                elif self.config.dry_run:
                    item.action_taken = "[DryRun] Would stop idle EC2 instance (allowlist verified)"
                elif self.config.mock_mode:
                    item.action_taken = "Stopped Instance (Mock)"
                elif not self.session:
                    item.action_taken = "Skipped (No active AWS session)"
                else:
                    try:
                        ec2 = self.session.client("ec2", region_name=item.region)
                        ec2.stop_instances(InstanceIds=[item.resource_id])
                        item.action_taken = "Stopped Non-Prod Instance"
                    except Exception as e:
                        item.action_taken = f"Failed: {str(e)[:30]}..."

            else:
                if self.config.dry_run:
                    item.action_taken = "Audit Only (Dry Run)"
                else:
                    item.action_taken = "Audit Recorded"

        return items
