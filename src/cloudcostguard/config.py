"""
Configuration settings and default thresholds for CloudCostGuard.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ScanConfig:
    regions: List[str] = field(default_factory=lambda: [
        "us-east-1", "us-east-2", "us-west-2", "ap-south-1", "eu-west-1"
    ])
    services: List[str] = field(default_factory=lambda: [
        "ebs", "eip", "ec2", "snapshots", "elb", "s3"
    ])
    # Thresholds
    ebs_unattached_days_threshold: int = 7
    snapshot_age_days_threshold: int = 30
    ec2_cpu_utilization_threshold: float = 5.0
    ec2_evaluation_days: int = 7
    s3_incomplete_mpu_days_threshold: int = 7

    # Remediation
    dry_run: bool = True
    apply_tags: bool = False
    stop_idle_ec2: bool = False
    safety_opt_in: bool = False
    tag_key: str = "CloudCostGuard:Action"
    tag_value: str = "MarkedForCleanup"
    autostop_tag_key: str = "CloudCostGuard:AutoStop"
    autostop_tag_value: str = "true"

    # Reporting
    slack_webhook_url: Optional[str] = field(default_factory=lambda: os.getenv("SLACK_WEBHOOK_URL"))
    html_report_path: Optional[str] = None
    json_report_path: Optional[str] = None

    # Simulation / Mock mode
    mock_mode: bool = False
