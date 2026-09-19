"""
Auditors package for CloudCostGuard.
"""

from typing import Dict, Type

from cloudcostguard.auditors.base import BaseAuditor, WasteItem
from cloudcostguard.auditors.ebs_auditor import EBSAuditor
from cloudcostguard.auditors.ec2_auditor import EC2Auditor
from cloudcostguard.auditors.eip_auditor import EIPAuditor
from cloudcostguard.auditors.elb_auditor import ELBAuditor
from cloudcostguard.auditors.s3_auditor import S3Auditor
from cloudcostguard.auditors.snapshot_auditor import SnapshotAuditor

AUDITOR_REGISTRY: Dict[str, Type[BaseAuditor]] = {
    "ebs": EBSAuditor,
    "eip": EIPAuditor,
    "ec2": EC2Auditor,
    "snapshots": SnapshotAuditor,
    "elb": ELBAuditor,
    "s3": S3Auditor,
}

__all__ = [
    "BaseAuditor",
    "WasteItem",
    "EBSAuditor",
    "EIPAuditor",
    "EC2Auditor",
    "SnapshotAuditor",
    "ELBAuditor",
    "S3Auditor",
    "AUDITOR_REGISTRY",
]
