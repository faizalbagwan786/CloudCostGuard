"""
EC2 Auditor: Identifies idle development compute instances and candidates with low CPU utilization.
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import List

from botocore.exceptions import ClientError

from cloudcostguard.auditors.base import BaseAuditor, WasteItem
from cloudcostguard.pricing import calculate_ec2_monthly_cost

logger = logging.getLogger(__name__)


class EC2Auditor(BaseAuditor):
    def audit(self, region: str) -> List[WasteItem]:
        items: List[WasteItem] = []
        if not self.session:
            return items

        ec2 = self.session.client("ec2", region_name=region)
        cw = self.session.client("cloudwatch", region_name=region)
        now = datetime.now(timezone.utc)
        eval_days = self.config.ec2_idle_days_threshold if self.config else 7
        start_time = now - timedelta(days=eval_days)

        try:
            reservations = ec2.describe_instances(
                Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
            ).get("Reservations", [])

            for res in reservations:
                for inst in res.get("Instances", []):
                    inst_id = inst.get("InstanceId")
                    inst_type = inst.get("InstanceType", "t3.medium")
                    launch_time = inst.get("LaunchTime")
                    tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
                    name = tags.get("Name", inst_id)
                    env = tags.get("Environment", "").lower()

                    # Query CloudWatch CPU Utilization
                    avg_cpu = None
                    try:
                        metric_resp = cw.get_metric_data(
                            MetricDataQueries=[
                                {
                                    "Id": "m1",
                                    "MetricStat": {
                                        "Metric": {
                                            "Namespace": "AWS/EC2",
                                            "MetricName": "CPUUtilization",
                                            "Dimensions": [{"Name": "InstanceId", "Value": inst_id}],
                                        },
                                        "Period": 86400,
                                        "Stat": "Average",
                                    },
                                }
                            ],
                            StartTime=start_time,
                            EndTime=now,
                        )
                        values = metric_resp.get("MetricDataResults", [{}])[0].get("Values", [])
                        if values:
                            avg_cpu = round(sum(values) / len(values), 2)
                    except ClientError as ce:
                        logger.warning(
                            f"CloudWatch metric query failed for instance {inst_id} in {region}: {ce}. "
                            "Skipping idle classification for safety."
                        )
                        continue

                    threshold = self.config.ec2_cpu_utilization_threshold if self.config else 5.0
                    is_low_cpu = (avg_cpu is not None and avg_cpu < threshold)
                    is_unscheduled_dev = (env in ["dev", "development", "test"] and "Schedule" not in tags)

                    if is_low_cpu or is_unscheduled_dev:
                        reason = []
                        if is_low_cpu:
                            reason.append(f"Avg CPU {avg_cpu}% (<{threshold}%) over {eval_days}d")
                        if is_unscheduled_dev:
                            reason.append("Dev instance running 24/7 without shutdown schedule")

                        status_label = (
                            "Candidate: Low CPU Utilization" if is_low_cpu
                            else "Candidate: Unscheduled Dev Instance"
                        )
                        waste = calculate_ec2_monthly_cost(inst_type)
                        items.append(
                            WasteItem(
                                resource_id=inst_id,
                                resource_type="EC2 Instance",
                                region=region,
                                name=name,
                                status=status_label,
                                details=f"{inst_type} | " + " & ".join(reason),
                                age_days=(now - launch_time).days if launch_time else None,
                                estimated_monthly_waste=waste,
                                recommendation="Review workload metrics, consider rightsizing or off-hours schedule",
                                tags=tags,
                            )
                        )
        except ClientError as ce:
            logger.warning(f"EC2 describe_instances failed in region {region}: {ce}")

        return items

    def mock_audit(self, region: str) -> List[WasteItem]:
        if region in ["us-east-1", "eu-west-1"]:
            return [
                WasteItem(
                    resource_id=f"i-079abcd12345{region[:3]}",
                    resource_type="EC2 Instance",
                    region=region,
                    name="dev-analytics-worker",
                    status="Candidate: Low CPU Utilization",
                    details="m5.large | Avg CPU 1.8% (<5.0%) over 7d & running 24/7",
                    age_days=35,
                    estimated_monthly_waste=calculate_ec2_monthly_cost("m5.large"),
                    recommendation="Review workload metrics, downsize to t3.medium, or apply off-hours schedule",
                    tags={"Environment": "dev", "Team": "DataEng", "AutoStop": "false"},
                ),
                WasteItem(
                    resource_id=f"i-0487ef987654{region[:3]}",
                    resource_type="EC2 Instance",
                    region=region,
                    name="qa-selenium-runner",
                    status="Candidate: Low CPU Utilization",
                    details="c5.xlarge | Avg CPU 2.4% (<5.0%) over 7d",
                    age_days=19,
                    estimated_monthly_waste=calculate_ec2_monthly_cost("c5.xlarge"),
                    recommendation="Review instance usage; stop when test suites complete or convert to Spot",
                    tags={"Environment": "qa", "Purpose": "e2e-testing"},
                ),
            ]
        return []
