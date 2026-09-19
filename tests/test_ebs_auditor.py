"""
Unit tests for EBS Auditor.
"""

from cloudcostguard.auditors.ebs_auditor import EBSAuditor
from cloudcostguard.config import ScanConfig


def test_ebs_mock_audit():
    config = ScanConfig()
    auditor = EBSAuditor(config=config)

    items = auditor.mock_audit("us-east-1")
    assert len(items) == 2
    assert all(item.resource_type == "EBS Volume" for item in items)
    assert all(item.estimated_monthly_waste > 0 for item in items)

    # In regions with no mock findings
    items_empty = auditor.mock_audit("eu-central-1")
    assert len(items_empty) == 0
