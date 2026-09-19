"""
Unit tests for FinOps pricing calculations.
"""

from cloudcostguard.pricing import (
    calculate_ebs_monthly_cost,
    calculate_ec2_monthly_cost,
    calculate_eip_monthly_cost,
    calculate_elb_monthly_cost,
    calculate_snapshot_monthly_cost,
)


def test_ebs_monthly_cost():
    # gp3 is $0.08 / GB
    cost_gp3 = calculate_ebs_monthly_cost("gp3", 100)
    assert cost_gp3 == 8.00

    # gp2 is $0.10 / GB
    cost_gp2 = calculate_ebs_monthly_cost("gp2", 200)
    assert cost_gp2 == 20.00


def test_eip_monthly_cost():
    # Unassociated EIP rate ~$3.65/mo
    cost_eip = calculate_eip_monthly_cost()
    assert cost_eip == 3.65


def test_snapshot_monthly_cost():
    # Snapshot is $0.05 / GB
    cost_snap = calculate_snapshot_monthly_cost(50)
    assert cost_snap == 2.50


def test_elb_monthly_cost():
    cost_alb = calculate_elb_monthly_cost("application")
    assert cost_alb == 16.43

    cost_clb = calculate_elb_monthly_cost("classic")
    assert cost_clb == 18.25


def test_ec2_monthly_cost():
    cost_m5 = calculate_ec2_monthly_cost("m5.large")
    assert cost_m5 == 70.08

    # Fallback default
    cost_unknown = calculate_ec2_monthly_cost("custom.family")
    assert cost_unknown == 45.00
