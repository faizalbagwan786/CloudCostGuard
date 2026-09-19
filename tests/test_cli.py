"""
Unit tests for CLI interface commands.
"""

from click.testing import CliRunner
from cloudcostguard.cli import main, scan


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "CloudCostGuard" in result.output


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "CloudCostGuard" in result.output
    assert "Faizal Bagwan" in result.output


def test_cli_scan_demo(tmp_path):
    html_file = tmp_path / "test_report.html"
    json_file = tmp_path / "test_report.json"

    runner = CliRunner()
    result = runner.invoke(
        scan,
        [
            "--demo",
            "--regions",
            "us-east-1",
            "--services",
            "ebs,eip",
            "--html",
            str(html_file),
            "--json-output",
            str(json_file),
        ],
    )

    assert result.exit_code == 0
    assert html_file.exists()
    assert json_file.exists()
    assert html_file.stat().st_size > 0
    assert json_file.stat().st_size > 0


def test_cli_scan_no_credentials():
    runner = CliRunner()
    result = runner.invoke(scan, ["--regions", "us-east-1"])
    # Should cleanly exit with code 1 and informative error message
    assert result.exit_code != 0
    assert "AWS Authentication Error" in result.output or "credentials" in result.output.lower()


def test_lambda_handler_mock_mode():
    from cloudcostguard.lambda_handler import lambda_handler

    event = {
        "mock_mode": True,
        "regions": "us-east-1,ap-south-1",
        "dry_run": True,
    }
    resp = lambda_handler(event, None)
    assert resp["statusCode"] == 200
    assert "body" in resp
    assert resp["body"]["waste_count"] > 0
    assert resp["body"]["estimated_monthly_waste_usd"] > 0
    assert resp["body"]["dry_run"] is True


def test_cli_stop_ec2_requires_safety_opt_in():
    runner = CliRunner()
    result = runner.invoke(scan, ["--demo", "--stop-idle-ec2"])
    assert result.exit_code != 0
    assert "safety opt-in" in result.output.lower() or "--safety-opt-in" in result.output


def test_lambda_standalone_without_cli_dependencies(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "click", None)
    monkeypatch.setitem(sys.modules, "rich", None)
    from cloudcostguard.lambda_handler import lambda_handler

    resp = lambda_handler({"mock_mode": True}, None)
    assert resp["statusCode"] == 200
    assert resp["body"]["waste_count"] > 0
