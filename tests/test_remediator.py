"""
Unit tests for Remediator policy execution.
"""

from cloudcostguard.auditors.base import WasteItem
from cloudcostguard.config import ScanConfig
from cloudcostguard.remediator import CloudCostRemediator


def test_remediator_dry_run():
    config = ScanConfig(dry_run=True, apply_tags=True)
    remediator = CloudCostRemediator(config=config)

    item = WasteItem(
        resource_id="vol-12345678",
        resource_type="EBS Volume",
        region="us-east-1",
    )

    result = remediator.remediate([item])
    assert "[DryRun] Would tag" in result[0].action_taken


def test_remediator_mock_tagging():
    config = ScanConfig(dry_run=False, mock_mode=True, apply_tags=True)
    remediator = CloudCostRemediator(config=config)

    item = WasteItem(
        resource_id="vol-12345678",
        resource_type="EBS Volume",
        region="us-east-1",
    )

    result = remediator.remediate([item])
    assert "Tagged:" in result[0].action_taken


def test_cannot_stop_without_safety_opt_in():
    # Even if allowlisted and in dev, missing --safety-opt-in must prevent stopping
    config = ScanConfig(dry_run=False, mock_mode=True, stop_idle_ec2=True, safety_opt_in=False)
    remediator = CloudCostRemediator(config=config)

    item = WasteItem(
        resource_id="i-allowlisted-dev",
        resource_type="EC2 Instance",
        region="us-east-1",
        tags={"CloudCostGuard:AutoStop": "true", "Environment": "dev"},
    )

    can_stop, reason = remediator.can_stop_ec2(item)
    assert can_stop is False
    assert "safety opt-in" in reason.lower()

    result = remediator.remediate([item])
    assert "Skipped" in result[0].action_taken
    assert "safety opt-in" in result[0].action_taken.lower()


def test_cannot_stop_untagged_instance():
    # Untagged instance lacks allowlist tag, must be protected
    config = ScanConfig(dry_run=False, mock_mode=True, stop_idle_ec2=True, safety_opt_in=True)
    remediator = CloudCostRemediator(config=config)

    item = WasteItem(
        resource_id="i-untagged-instance",
        resource_type="EC2 Instance",
        region="us-east-1",
        tags={},
    )

    can_stop, reason = remediator.can_stop_ec2(item)
    assert can_stop is False
    assert "untagged" in reason.lower()

    result = remediator.remediate([item])
    assert "Skipped" in result[0].action_taken
    assert "untagged" in result[0].action_taken.lower()


def test_cannot_stop_non_allowlisted_instance():
    # Instance in dev without CloudCostGuard:AutoStop=true must NOT be stopped
    config = ScanConfig(dry_run=False, mock_mode=True, stop_idle_ec2=True, safety_opt_in=True)
    remediator = CloudCostRemediator(config=config)

    item = WasteItem(
        resource_id="i-dev-no-allowlist",
        resource_type="EC2 Instance",
        region="us-east-1",
        tags={"Environment": "dev", "Name": "developer-sandbox"},
    )

    can_stop, reason = remediator.can_stop_ec2(item)
    assert can_stop is False
    assert "non-allowlisted" in reason.lower()

    result = remediator.remediate([item])
    assert "Skipped" in result[0].action_taken
    assert "non-allowlisted" in result[0].action_taken.lower()


def test_cannot_stop_production_instance():
    # Even if mistakenly allowlisted, production instances must NEVER be stopped
    config = ScanConfig(dry_run=False, mock_mode=True, stop_idle_ec2=True, safety_opt_in=True)
    remediator = CloudCostRemediator(config=config)

    item = WasteItem(
        resource_id="i-prod-critical-db",
        resource_type="EC2 Instance",
        region="us-east-1",
        tags={"CloudCostGuard:AutoStop": "true", "Environment": "production"},
    )

    can_stop, reason = remediator.can_stop_ec2(item)
    assert can_stop is False
    assert "production" in reason.lower()

    result = remediator.remediate([item])
    assert "Skipped" in result[0].action_taken
    assert "production" in result[0].action_taken.lower()


def test_cannot_stop_protected_instance():
    # Instances with explicit protection tags (e.g. DoNotStop, Protected) must NEVER be stopped
    config = ScanConfig(dry_run=False, mock_mode=True, stop_idle_ec2=True, safety_opt_in=True)
    remediator = CloudCostRemediator(config=config)

    item = WasteItem(
        resource_id="i-protected-staging",
        resource_type="EC2 Instance",
        region="us-east-1",
        tags={"CloudCostGuard:AutoStop": "true", "Environment": "staging", "DoNotStop": "true"},
    )

    can_stop, reason = remediator.can_stop_ec2(item)
    assert can_stop is False
    assert "protected" in reason.lower()

    result = remediator.remediate([item])
    assert "Skipped" in result[0].action_taken
    assert "protected" in result[0].action_taken.lower()


def test_can_stop_allowlisted_dev_instance():
    # Allowlisted non-production instance with safety opt-in is authorized
    config = ScanConfig(dry_run=False, mock_mode=True, stop_idle_ec2=True, safety_opt_in=True)
    remediator = CloudCostRemediator(config=config)

    item = WasteItem(
        resource_id="i-allowlisted-qa",
        resource_type="EC2 Instance",
        region="us-east-1",
        tags={"CloudCostGuard:AutoStop": "true", "Environment": "dev"},
    )

    can_stop, reason = remediator.can_stop_ec2(item)
    assert can_stop is True

    result = remediator.remediate([item])
    assert result[0].action_taken == "Stopped Instance (Mock)"


def test_dry_run_allowlisted_dev_instance():
    # In dry-run mode, allowlisted dev instance is marked as would stop
    config = ScanConfig(dry_run=True, stop_idle_ec2=True, safety_opt_in=True)
    remediator = CloudCostRemediator(config=config)

    item = WasteItem(
        resource_id="i-allowlisted-qa",
        resource_type="EC2 Instance",
        region="us-east-1",
        tags={"CloudCostGuard:AutoStop": "true", "Environment": "test"},
    )

    result = remediator.remediate([item])
    assert "[DryRun] Would stop idle EC2 instance" in result[0].action_taken
