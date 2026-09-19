"""
S3 Auditor: Identifies unmanaged S3 buckets lacking lifecycle rules and lingering incomplete multipart uploads.
"""

from datetime import datetime, timezone
import logging
from typing import List

from botocore.exceptions import ClientError

from cloudcostguard.auditors.base import BaseAuditor, WasteItem

logger = logging.getLogger(__name__)


class S3Auditor(BaseAuditor):
    def audit(self, region: str) -> List[WasteItem]:
        items: List[WasteItem] = []
        if not self.session:
            return items

        s3 = self.session.client("s3")
        try:
            buckets = s3.list_buckets().get("Buckets", [])
            for b in buckets:
                name = b.get("Name")
                try:
                    loc_resp = s3.get_bucket_location(Bucket=name)
                    bucket_region = loc_resp.get("LocationConstraint") or "us-east-1"
                    if bucket_region == "EU":
                        bucket_region = "eu-west-1"
                    if bucket_region != region:
                        continue
                except ClientError as ce:
                    logger.warning(f"Failed getting location for bucket {name}: {ce}")
                    continue

                # Check for lingering incomplete multipart uploads
                has_lingering_uploads = False
                upload_count = 0
                try:
                    mp_resp = s3.list_multipart_uploads(Bucket=name)
                    uploads = mp_resp.get("Uploads", [])
                    now_utc = datetime.now(timezone.utc)
                    stale_uploads = [
                        u for u in uploads
                        if u.get("Initiated") and (now_utc - u["Initiated"]).days > 7
                    ]
                    if stale_uploads:
                        has_lingering_uploads = True
                        upload_count = len(stale_uploads)
                except ClientError as ce:
                    logger.debug(f"Unable to list multipart uploads for bucket {name}: {ce}")

                has_lifecycle = True
                try:
                    s3.get_bucket_lifecycle_configuration(Bucket=name)
                except ClientError:
                    has_lifecycle = False

                if has_lingering_uploads:
                    items.append(
                        WasteItem(
                            resource_id=name,
                            resource_type="S3 Bucket",
                            region=region,
                            name=name,
                            status="Governance: Lingering Incomplete Multipart Uploads",
                            details=(
                                f"{upload_count} abandoned upload(s) >7d (governance cleanup finding; "
                                "cost unquantified without byte-level storage metrics)"
                            ),
                            age_days=None,
                            estimated_monthly_waste=0.0,
                            recommendation="Configure S3 lifecycle rule: AbortIncompleteMultipartUpload after 7 days",
                            tags={},
                        )
                    )
                elif not has_lifecycle:
                    items.append(
                        WasteItem(
                            resource_id=name,
                            resource_type="S3 Bucket",
                            region=region,
                            name=name,
                            status="Missing Lifecycle Configuration",
                            details="No automated expiration or transition to Glacier/IA storage classes",
                            age_days=None,
                            estimated_monthly_waste=0.0,
                            recommendation="Audit bucket objects and apply S3 lifecycle transition/expiration rules",
                            tags={},
                        )
                    )
        except ClientError as ce:
            logger.warning(f"S3 list_buckets query failed in region {region}: {ce}")

        return items

    def mock_audit(self, region: str) -> List[WasteItem]:
        if region in ["us-east-1"]:
            return [
                WasteItem(
                    resource_id="corp-app-temp-artifacts-bucket",
                    resource_type="S3 Bucket",
                    region=region,
                    name="corp-app-temp-artifacts-bucket",
                    status="Governance: Lingering Incomplete Multipart Uploads",
                    details=(
                        "12 abandoned multipart uploads >7d (governance cleanup finding; "
                        "cost unquantified without byte-level storage metrics)"
                    ),
                    age_days=110,
                    estimated_monthly_waste=0.0,
                    recommendation="Enable 7-day AbortIncompleteMultipartUpload and 30-day artifact expiry",
                    tags={"Environment": "shared", "Team": "DevOps"},
                )
            ]
        return []
