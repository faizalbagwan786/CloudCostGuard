"""
EIP Auditor: Identifies unassociated Elastic IP addresses incurring hourly idle IPv4 charges.
"""

import logging
from typing import List

from botocore.exceptions import ClientError

from cloudcostguard.auditors.base import BaseAuditor, WasteItem
from cloudcostguard.pricing import calculate_eip_monthly_cost

logger = logging.getLogger(__name__)


class EIPAuditor(BaseAuditor):
    def audit(self, region: str) -> List[WasteItem]:
        items: List[WasteItem] = []
        if not self.session:
            return items

        ec2 = self.session.client("ec2", region_name=region)
        try:
            addresses = ec2.describe_addresses().get("Addresses", [])
            for addr in addresses:
                # If AssociationId or InstanceId is missing, it is unassociated
                if not addr.get("AssociationId") and not addr.get("InstanceId"):
                    alloc_id = addr.get("AllocationId", addr.get("PublicIp", "eip-unknown"))
                    public_ip = addr.get("PublicIp", "Unknown IP")
                    tags = {t["Key"]: t["Value"] for t in addr.get("Tags", [])}
                    name = tags.get("Name", "Unallocated EIP")

                    items.append(
                        WasteItem(
                            resource_id=alloc_id,
                            resource_type="Elastic IP",
                            region=region,
                            name=name,
                            status="Unassociated",
                            details=f"Public IPv4: {public_ip}",
                            age_days=None,
                            estimated_monthly_waste=calculate_eip_monthly_cost(),
                            recommendation="Release unassociated Elastic IP to avoid AWS idle IPv4 charge",
                            tags=tags,
                        )
                    )
        except ClientError as ce:
            logger.warning(f"EC2 describe_addresses failed in region {region}: {ce}")

        return items

    def mock_audit(self, region: str) -> List[WasteItem]:
        if region in ["us-east-1", "us-west-2", "ap-south-1"]:
            return [
                WasteItem(
                    resource_id=f"eipalloc-01ab9876{region[:3]}",
                    resource_type="Elastic IP",
                    region=region,
                    name="old-bastion-ip",
                    status="Unassociated",
                    details=f"Public IPv4: 54.210.{len(region)*7}.102",
                    age_days=18,
                    estimated_monthly_waste=calculate_eip_monthly_cost(),
                    recommendation="Release unassociated Elastic IP back to AWS pool",
                    tags={"Purpose": "bastion-migration", "ManagedBy": "terraform"},
                )
            ]
        return []
