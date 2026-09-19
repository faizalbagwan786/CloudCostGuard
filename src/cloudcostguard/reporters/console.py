"""
Console Reporter: Outputs high-impact, beautifully styled terminal tables and KPI cards using Rich.
"""

import sys
from typing import List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from cloudcostguard.auditors.base import WasteItem

# Fix Windows console encoding for Unicode/Emojis
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def print_console_report(items: List[WasteItem], dry_run: bool = True, mock_mode: bool = False) -> None:
    console = Console(highlight=True, safe_box=True)

    total_monthly = sum(item.estimated_monthly_waste for item in items)
    total_annual = total_monthly * 12.0
    item_count = len(items)

    if mock_mode:
        mode_tag = "[MOCK SIMULATION] "
    else:
        mode_tag = ""

    # Title Banner
    banner_text = Text()
    banner_text.append("CloudCostGuard - AWS FinOps Cost Optimizer\n", style="bold cyan")
    banner_text.append("Execution Mode: ", style="white")
    if dry_run:
        banner_text.append("DRY-RUN (AUDIT ONLY)", style="bold cyan")
    else:
        banner_text.append("LIVE REMEDIATION ACTIVE", style="bold red")
    banner_text.append(f" | Status: {mode_tag}Complete\n", style="white")
    banner_text.append("Engineered by Faizal Bagwan | FinOps Automation & Resource Governance", style="dim italic")

    console.print(Panel(banner_text, border_style="cyan", padding=(1, 2)))

    # Summary KPI Panels
    kpi_table = Table.grid(padding=(0, 2))
    kpi_table.add_column(justify="center")
    kpi_table.add_column(justify="center")
    kpi_table.add_column(justify="center")
    kpi_table.add_column(justify="center")

    kpi_table.add_row(
        Panel(f"[bold yellow]{item_count}[/bold yellow]\nWasted Resources", border_style="yellow", width=22),
        Panel(
            f"[bold magenta]${total_annual:,.2f}[/bold magenta]\nProjected Annual Waste",
            border_style="magenta",
            width=26,
        ),
        Panel(f"[bold green]${total_monthly:,.2f}[/bold green]\nTarget Savings", border_style="green", width=22),
    )
    console.print(kpi_table)
    console.print()

    if not items:
        console.print(
            "[bold green]✅ Excellent! No orphaned or idle resources detected across scanned regions.[/bold green]\n"
        )
        return

    # Detailed Waste Findings Table
    table = Table(
        title="🔍 Detailed Cloud Waste Findings & Optimization Opportunities",
        border_style="blue",
        header_style="bold cyan",
        show_lines=True,
    )

    table.add_column("Resource ID / Name", style="bold white", no_wrap=True)
    table.add_column("Type", style="cyan")
    table.add_column("Region", style="blue")
    table.add_column("Status / Findings", style="yellow")
    table.add_column("Details", style="dim")
    table.add_column("Age", justify="right", style="magenta")
    table.add_column("Est. Monthly Waste", justify="right", style="bold red")
    table.add_column("Action / Status", style="green")

    for item in items:
        name_display = f"{item.resource_id}\n[dim]({item.name})[/dim]" if item.name != "N/A" else item.resource_id
        age_str = f"{item.age_days}d" if item.age_days is not None else "N/A"
        cost_str = f"${item.estimated_monthly_waste:,.2f}"

        table.add_row(
            name_display,
            item.resource_type,
            item.region,
            item.status,
            item.details,
            age_str,
            cost_str,
            item.action_taken,
        )

    console.print(table)
    console.print()

    # Recommendations & Next Steps Panel
    rec_text = Text()
    rec_text.append("💡 FinOps Immediate Recommendations:\n", style="bold yellow")
    rec_text.append("1. Create final snapshots and delete all unattached EBS volumes older than 14 days.\n")
    rec_text.append("2. Release unallocated Elastic IPs to stop AWS idle IPv4 charges ($0.005/hr each).\n")
    rec_text.append(
        "3. Schedule non-production dev/staging instances to stop during off-hours (saving up to 65% on EC2).\n"
    )
    rec_text.append("4. Decommission empty load balancers with 0 healthy target instances.\n")
    console.print(Panel(rec_text, border_style="yellow", padding=(0, 2)))
    console.print()
