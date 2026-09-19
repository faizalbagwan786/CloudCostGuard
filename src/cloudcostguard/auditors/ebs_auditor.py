"""
EBS Auditor: Identifies unattached (orphaned) Elastic Block Store volumes.
"""

from datetime import datetime, timezone
import logging
from typing import List

from botocore.exceptions import ClientError

from cloudcostguard.auditors.base import BaseAuditor, WasteItem
from cloudcostguard.pricing import calculate_ebs_monthly_cost

logger = logging.getLogger(__name__)


class EBSAuditor(BaseAuditor):
    def audit(self, region: str) -> List[WasteItem]:
        items: List[WasteItem] = []
        if not self.session:
            return items

        ec2 = self.session.client("ec2", region_name=region)
        try:
            paginator = ec2.get_paginator("describe_volumes")
            page_iterator = paginator.paginate(
                Filters=[{"Name": "status", "Values": ["available"]}]
            )

            now = datetime.now(timezone.utc)
            for page in page_iterator:
                for vol in page.get("Volumes", []):
                    vol_id = vol.get("VolumeId")
                    vol_type = vol.get("VolumeType", "gp3")
                    size_gb = vol.get("Size", 0)
                    create_time = vol.get("CreateTime")

                    age_days = (now - create_time).days if create_time else None
                    tags = {t["Key"]: t["Value"] for t in vol.get("Tags", [])}
                    name = tags.get("Name", "Unnamed Volume")

                    monthly_waste = calculate_ebs_monthly_cost(vol_type, size_gb)

                    threshold = self.config.ebs_unattached_days_threshold if self.config else 7
                    if age_days is not None and age_days < threshold:
                        continue

                    items.append(
                        WasteItem(
                            resource_id=vol_id,
                            resource_type="EBS Volume",
                            region=region,
                            name=name,
                            status="Unattached (Available)",
                            details=f"{size_gb} GiB ({vol_type})",
                            age_days=age_days,
                            estimated_monthly_waste=monthly_waste,
                            recommendation="Snapshot and delete orphaned volume or attach to instance",
                            tags=tags,
                        )
                    )
        except ClientError as ce:
            logger.warning(f"EBS describe_volumes failed in region {region}: {ce}")

        return items

    def mock_audit(self, region: str) -> List[WasteItem]:
        """Realistic mock data for demonstration."""
        if region in ["us-east-1", "ap-south-1"]:
            return [
                WasteItem(
                    resource_id=f"vol-09a8bc72{region[:3]}1",
                    resource_type="EBS Volume",
                    region=region,
                    name="staging-api-data-old",
                    status="Unattached (Available)",
                    details="150 GiB (gp3)",
                    age_days=24,
                    estimated_monthly_waste=calculate_ebs_monthly_cost("gp3", 150),
                    recommendation="Create final snapshot and terminate unattached volume",
                    tags={"Environment": "staging", "Project": "CoreAPI"},
                ),
                WasteItem(
                    resource_id=f"vol-0123fe54{region[:3]}2",
                    resource_type="EBS Volume",
                    region=region,
                    name="temp-db-scratch",
                    status="Unattached (Available)",
                    details="300 GiB (gp2)",
                    age_days=42,
                    estimated_monthly_waste=calculate_ebs_monthly_cost("gp2", 300),
                    recommendation="Delete obsolete unattached database scratch disk",
                    tags={"Environment": "dev", "Owner": "qa-team"},
                ),
            ]
        return []
