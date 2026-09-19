"""
FinOps Cost Estimation Engine.
Calculates estimated monthly dollar waste across AWS resource types.
"""

from typing import Dict

# Approximate standard AWS monthly pricing benchmarks (US East / Global baseline)
EBS_PRICE_PER_GB_MONTH: Dict[str, float] = {
    "gp3": 0.08,
    "gp2": 0.10,
    "io1": 0.125,
    "io2": 0.125,
    "st1": 0.045,
    "sc1": 0.015,
    "standard": 0.05,
}

# $0.005 per hour for idle unassociated IPv4 address * 730 hours
EIP_MONTHLY_COST: float = 0.005 * 730.0  # $3.65 / month

# EBS Snapshot standard storage rate per GB-month
SNAPSHOT_PRICE_PER_GB_MONTH: float = 0.05

# Idle Load Balancer minimum hourly rate ($0.0225/hr * 730)
ALB_NLB_MONTHLY_BASE_COST: float = 0.0225 * 730.0  # ~$16.43 / month
CLB_MONTHLY_BASE_COST: float = 0.025 * 730.0       # ~$18.25 / month

# Standard EC2 on-demand monthly costs (hourly rate * 730 hours)
EC2_ESTIMATED_MONTHLY_COSTS: Dict[str, float] = {
    "t2.nano": 0.0058 * 730,     # $4.23
    "t2.micro": 0.0116 * 730,    # $8.47
    "t2.small": 0.023 * 730,     # $16.79
    "t2.medium": 0.0464 * 730,   # $33.87
    "t2.large": 0.0928 * 730,    # $67.74
    "t3.nano": 0.0052 * 730,     # $3.80
    "t3.micro": 0.0104 * 730,    # $7.59
    "t3.small": 0.0208 * 730,    # $15.18
    "t3.medium": 0.0416 * 730,   # $30.37
    "t3.large": 0.0832 * 730,    # $60.74
    "t3.xlarge": 0.1664 * 730,   # $121.47
    "t3.2xlarge": 0.3328 * 730,  # $242.94
    "m5.large": 0.096 * 730,     # $70.08
    "m5.xlarge": 0.192 * 730,    # $140.16
    "c5.large": 0.085 * 730,     # $62.05
    "c5.xlarge": 0.17 * 730,     # $124.10
    "r5.large": 0.126 * 730,     # $91.98
}

DEFAULT_EC2_FALLBACK_MONTHLY: float = 45.00


def calculate_ebs_monthly_cost(volume_type: str, size_gb: int) -> float:
    """Calculate monthly wasted spend for an unattached EBS volume."""
    unit_price = EBS_PRICE_PER_GB_MONTH.get(volume_type.lower(), 0.08)
    return round(unit_price * size_gb, 2)


def calculate_eip_monthly_cost() -> float:
    """Calculate monthly wasted spend for an unassociated Elastic IP."""
    return round(EIP_MONTHLY_COST, 2)


def calculate_snapshot_monthly_cost(size_gb: int) -> float:
    """Calculate monthly wasted spend for an obsolete EBS snapshot."""
    return round(SNAPSHOT_PRICE_PER_GB_MONTH * size_gb, 2)


def calculate_elb_monthly_cost(elb_type: str = "application") -> float:
    """Calculate monthly base cost for an idle Load Balancer."""
    if elb_type.lower() == "classic":
        return round(CLB_MONTHLY_BASE_COST, 2)
    return round(ALB_NLB_MONTHLY_BASE_COST, 2)


def calculate_ec2_monthly_cost(instance_type: str) -> float:
    """Calculate monthly wasted cost for an idle or zombie EC2 instance."""
    return round(EC2_ESTIMATED_MONTHLY_COSTS.get(instance_type.lower(), DEFAULT_EC2_FALLBACK_MONTHLY), 2)
