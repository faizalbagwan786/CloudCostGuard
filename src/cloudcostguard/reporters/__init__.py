"""
Reporters package for CloudCostGuard.
"""

from cloudcostguard.reporters.html_report import generate_html_report
from cloudcostguard.reporters.slack_reporter import send_slack_notification

try:
    from cloudcostguard.reporters.console import print_console_report
except ImportError:
    print_console_report = None  # Graceful fallback in environments without Rich (e.g. Lambda)

__all__ = [
    "print_console_report",
    "generate_html_report",
    "send_slack_notification",
]
