"""
Unit tests for EIP Auditor.
"""

from cloudcostguard.auditors.eip_auditor import EIPAuditor
from cloudcostguard.config import ScanConfig


def test_eip_mock_audit():
    config = ScanConfig()
    auditor = EIPAuditor(config=config)

    items = auditor.mock_audit("us-east-1")
    assert len(items) == 1
    assert items[0].resource_type == "Elastic IP"
    assert items[0].estimated_monthly_waste == 3.65
    assert "Public IPv4" in items[0].details
