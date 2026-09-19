"""
ELB Auditor: Identifies idle or orphaned Load Balancers with zero healthy targets.
"""

import logging
from typing import List

from botocore.exceptions import ClientError

from cloudcostguard.auditors.base import BaseAuditor, WasteItem
from cloudcostguard.pricing import calculate_elb_monthly_cost

logger = logging.getLogger(__name__)


class ELBAuditor(BaseAuditor):
    def audit(self, region: str) -> List[WasteItem]:
        items: List[WasteItem] = []
        if not self.session:
            return items

        elbv2 = self.session.client("elbv2", region_name=region)
        try:
            paginator = elbv2.get_paginator("describe_load_balancers")
            for page in paginator.paginate():
                for lb in page.get("LoadBalancers", []):
                    lb_arn = lb.get("LoadBalancerArn")
                    lb_name = lb.get("LoadBalancerName")
                    lb_type = lb.get("Type", "application")

                    # Check Target Groups for this LB
                    tgs = elbv2.describe_target_groups(LoadBalancerArn=lb_arn).get("TargetGroups", [])
                    total_healthy_targets = 0
                    total_registered_targets = 0

                    for tg in tgs:
                        tg_arn = tg.get("TargetGroupArn")
                        th = elbv2.describe_target_health(TargetGroupArn=tg_arn).get("TargetHealthDescriptions", [])
                        total_registered_targets += len(th)
                        total_healthy_targets += sum(
                            1 for target in th if target.get("TargetHealth", {}).get("State") == "healthy"
                        )

                    if not tgs or total_registered_targets == 0:
                        waste = calculate_elb_monthly_cost(lb_type)
                        items.append(
                            WasteItem(
                                resource_id=lb_name,
                                resource_type="Load Balancer",
                                region=region,
                                name=lb_name,
                                status="Empty / Zero Targets",
                                details=f"{lb_type.upper()} with 0 registered backend targets",
                                age_days=None,
                                estimated_monthly_waste=waste,
                                recommendation="Decommission load balancer or register active backend targets",
                                tags={},
                            )
                        )
                    elif total_healthy_targets == 0 and total_registered_targets > 0:
                        waste = calculate_elb_monthly_cost(lb_type)
                        items.append(
                            WasteItem(
                                resource_id=lb_name,
                                resource_type="Load Balancer",
                                region=region,
                                name=lb_name,
                                status="Unhealthy Targets (100%)",
                                details=(
                                    f"{lb_type.upper()} has {total_registered_targets} registered targets, "
                                    "all failing health checks"
                                ),
                                age_days=None,
                                estimated_monthly_waste=waste,
                                recommendation="Investigate failed targets or terminate abandoned load balancer",
                                tags={},
                            )
                        )
        except ClientError as ce:
            logger.warning(f"ELB describe_load_balancers failed in region {region}: {ce}")

        return items

    def mock_audit(self, region: str) -> List[WasteItem]:
        if region in ["us-east-1", "ap-south-1"]:
            return [
                WasteItem(
                    resource_id=f"alb-demo-abandoned-{region[:3]}",
                    resource_type="Load Balancer",
                    region=region,
                    name="staging-ingress-alb",
                    status="Empty / Zero Targets",
                    details="APPLICATION ALB with 0 registered backend targets",
                    age_days=28,
                    estimated_monthly_waste=calculate_elb_monthly_cost("application"),
                    recommendation="Decommission unused ALB after microservice retirement",
                    tags={"Environment": "staging", "Service": "legacy-web"},
                )
            ]
        return []
