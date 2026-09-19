"""
Snapshot Auditor: Identifies obsolete and unreferenced EBS Snapshots.
"""

from datetime import datetime, timezone
import logging
from typing import List, Set

from botocore.exceptions import ClientError

from cloudcostguard.auditors.base import BaseAuditor, WasteItem
from cloudcostguard.pricing import calculate_snapshot_monthly_cost

logger = logging.getLogger(__name__)


class SnapshotAuditor(BaseAuditor):
    def audit(self, region: str) -> List[WasteItem]:
        items: List[WasteItem] = []
        if not self.session:
            return items

        ec2 = self.session.client("ec2", region_name=region)
        try:
            # Get active AMIs owned by self to ensure we don't flag snapshot backing an active AMI
            images = ec2.describe_images(Owners=["self"]).get("Images", [])
            ami_snapshot_ids: Set[str] = set()
            for img in images:
                for bdm in img.get("BlockDeviceMappings", []):
                    if "Ebs" in bdm and "SnapshotId" in bdm["Ebs"]:
                        ami_snapshot_ids.add(bdm["Ebs"]["SnapshotId"])

            # Describe snapshots owned by self
            snapshots = ec2.describe_snapshots(OwnerIds=["self"]).get("Snapshots", [])
            now = datetime.now(timezone.utc)
            threshold_days = self.config.snapshot_age_days_threshold if self.config else 30

            for snap in snapshots:
                snap_id = snap.get("SnapshotId")
                size_gb = snap.get("VolumeSize", 0)
                start_time = snap.get("StartTime")
                description = (snap.get("Description") or "").lower()
                tags = {t["Key"]: t["Value"] for t in snap.get("Tags", [])}
                tags_lower = {k.lower(): v.lower() for k, v in tags.items()}
                name = tags.get("Name", snap_id)

                age_days = (now - start_time).days if start_time else None

                # Safeguard: Protect snapshots with explicit retention/archive keys
                protection_keys = ["retain", "archive", "compliance", "donotdelete"]
                is_retained = False
                for pkey in protection_keys:
                    if pkey in tags_lower:
                        val = tags_lower[pkey]
                        if val not in ["false", "no", "0"]:
                            is_retained = True
                            break

                if not is_retained:
                    if "compliance" in description or "permanent" in description:
                        is_retained = True

                if is_retained:
                    continue

                # If snapshot is older than threshold and not backing an active AMI
                if snap_id not in ami_snapshot_ids and age_days is not None and age_days >= threshold_days:
                    waste = calculate_snapshot_monthly_cost(size_gb)
                    items.append(
                        WasteItem(
                            resource_id=snap_id,
                            resource_type="Snapshot",
                            region=region,
                            name=name,
                            status="Unreferenced / Aged Snapshot",
                            details=f"{size_gb} GiB | Age: {age_days}d | Not bound to active AMI",
                            age_days=age_days,
                            estimated_monthly_waste=waste,
                            recommendation=(
                                f"Review retention policy or remove unreferenced snapshot (>{threshold_days}d)"
                            ),
                            tags=tags,
                        )
                    )
        except ClientError as ce:
            logger.warning(f"EC2 describe_snapshots failed in region {region}: {ce}")

        return items

    def mock_audit(self, region: str) -> List[WasteItem]:
        if region in ["us-east-1", "us-east-2", "ap-south-1"]:
            return [
                WasteItem(
                    resource_id=f"snap-05a9c84e12{region[:3]}",
                    resource_type="Snapshot",
                    region=region,
                    name="pre-upgrade-db-backup-2023",
                    status="Unreferenced / Aged Snapshot",
                    details="250 GiB | Age: 184d | Not bound to active AMI",
                    age_days=184,
                    estimated_monthly_waste=calculate_snapshot_monthly_cost(250),
                    recommendation="Review retention policy or remove legacy manual backup snapshot",
                    tags={"CreatedBy": "db-migration-script", "Retain": "false"},
                ),
                WasteItem(
                    resource_id=f"snap-07e12f34b9{region[:3]}",
                    resource_type="Snapshot",
                    region=region,
                    name="temp-test-image-root",
                    status="Unreferenced / Aged Snapshot",
                    details="80 GiB | Age: 95d | Deregistered AMI leftover",
                    age_days=95,
                    estimated_monthly_waste=calculate_snapshot_monthly_cost(80),
                    recommendation="Clean up orphaned root snapshot after AMI deregistration",
                    tags={"Environment": "test"},
                ),
            ]
        return []
