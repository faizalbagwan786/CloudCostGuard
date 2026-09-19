"""
HTML Report Generator: Produces an executive-ready, responsive HTML dashboard for FinOps audits.
"""

import os
from datetime import datetime, timezone
from typing import List

from cloudcostguard.auditors.base import WasteItem


def generate_html_report(
    items: List[WasteItem],
    output_path: str,
    dry_run: bool = True,
    is_demo: bool = False,
) -> str:
    total_monthly = sum(i.estimated_monthly_waste for i in items)
    total_annual = total_monthly * 12.0
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Group by resource type
    by_type = {}
    for i in items:
        by_type[i.resource_type] = by_type.get(i.resource_type, 0.0) + i.estimated_monthly_waste

    table_rows = []
    for item in items:
        if item.age_days is not None:
            age_badge = f'<span class="badge badge-age">{item.age_days}d</span>'
        else:
            age_badge = '<span class="badge badge-na">N/A</span>'
        table_rows.append(f"""
        <tr>
            <td class="res-id">
                <strong>{item.resource_id}</strong>
                <div class="res-name">{item.name}</div>
            </td>
            <td><span class="badge badge-type">{item.resource_type}</span></td>
            <td><code>{item.region}</code></td>
            <td><span class="badge badge-status">{item.status}</span></td>
            <td class="details-cell">{item.details}</td>
            <td>{age_badge}</td>
            <td class="cost-cell">${item.estimated_monthly_waste:,.2f}</td>
            <td class="rec-cell">{item.recommendation}</td>
        </tr>
        """)

    category_cards = []
    for r_type, amt in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
        category_cards.append(f"""
        <div class="category-card">
            <div class="category-name">{r_type}</div>
            <div class="category-amount">${amt:,.2f}/mo</div>
        </div>
        """)

    font_url = (
        "https://fonts.googleapis.com/css2?"
        "family=Inter:wght@300;400;500;600;700&"
        "family=JetBrains+Mono:wght@400;500&display=swap"
    )

    if is_demo:
        banner_html = (
            '<div class="dataset-banner demo">\n'
            '    <span class="banner-badge">DEMO BENCHMARK</span>\n'
            '    <span>Synthetic multi-region benchmark dataset &bull; '
            'Non-production simulation &bull; No live AWS assets scanned</span>\n'
            '</div>'
        )
        mode_badge = '<span class="badge-mode badge-demo">DEMO BENCHMARK</span>'
    else:
        mode_text = "DRY-RUN / AUDIT" if dry_run else "REMEDIATION ENABLED"
        mode_badge = f'<span class="badge-mode">{mode_text}</span>'
        banner_html = (
            '<div class="dataset-banner live">\n'
            '    <span class="banner-badge">LIVE AWS AUDIT</span>\n'
            '    <span>Infrastructure findings queried from authenticated AWS account &bull; '
            'Baseline pricing models</span>\n'
            '</div>'
        )

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CloudCostGuard - AWS FinOps Cost Audit Report</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="{font_url}" rel="stylesheet">
    <style>
        :root {{
            --bg: #0b0f19;
            --surface: #131b2e;
            --surface-border: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-blue: #38bdf8;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-amber: #f59e0b;
            --accent-purple: #a855f7;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: var(--bg);
            color: var(--text-primary);
            font-family: 'Inter', sans-serif;
            padding: 32px 24px;
            line-height: 1.5;
        }}
        .container {{ max-width: 1300px; margin: 0 auto; }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--surface-border);
            padding-bottom: 24px;
            margin-bottom: 24px;
        }}
        .brand h1 {{
            font-size: 26px;
            font-weight: 700;
            background: linear-gradient(135deg, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .brand p {{ color: var(--text-secondary); font-size: 14px; margin-top: 4px; }}
        .header-meta {{ text-align: right; font-size: 13px; color: var(--text-secondary); }}
        .badge-mode {{
            background: rgba(56, 189, 248, 0.15);
            color: var(--accent-blue);
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
            display: inline-block;
            margin-bottom: 4px;
        }}
        .badge-mode.badge-demo {{
            background: rgba(245, 158, 11, 0.15);
            color: var(--accent-amber);
            border: 1px solid rgba(245, 158, 11, 0.3);
        }}

        /* Dataset Banner */
        .dataset-banner {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 18px;
            border-radius: 10px;
            font-size: 13px;
            margin-bottom: 28px;
            border: 1px solid var(--surface-border);
        }}
        .dataset-banner.demo {{
            background: rgba(56, 189, 248, 0.08);
            border-color: rgba(56, 189, 248, 0.25);
            color: #bae6fd;
        }}
        .dataset-banner.live {{
            background: rgba(16, 185, 129, 0.08);
            border-color: rgba(16, 185, 129, 0.25);
            color: #a7f3d0;
        }}
        .banner-badge {{
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.05em;
            padding: 3px 8px;
            border-radius: 6px;
            text-transform: uppercase;
            white-space: nowrap;
        }}
        .dataset-banner.demo .banner-badge {{
            background: rgba(56, 189, 248, 0.2);
            color: var(--accent-blue);
        }}
        .dataset-banner.live .banner-badge {{
            background: rgba(16, 185, 129, 0.2);
            color: var(--accent-green);
        }}

        /* KPI Grid */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 20px;
            margin-bottom: 32px;
        }}
        .kpi-card {{
            background: var(--surface);
            border: 1px solid var(--surface-border);
            border-radius: 14px;
            padding: 24px;
            position: relative;
            overflow: hidden;
        }}
        .kpi-card::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 3px;
        }}
        .kpi-card.red::before {{ background: var(--accent-red); }}
        .kpi-card.magenta::before {{ background: var(--accent-purple); }}
        .kpi-card.green::before {{ background: var(--accent-green); }}
        .kpi-card.amber::before {{ background: var(--accent-amber); }}
        .kpi-label {{
            font-size: 13px; font-weight: 500; color: var(--text-secondary);
            text-transform: uppercase; letter-spacing: 0.05em;
        }}
        .kpi-value {{ font-size: 32px; font-weight: 700; margin-top: 8px; }}
        .kpi-subtext {{ font-size: 12px; color: var(--text-secondary); margin-top: 4px; }}

        /* Category Breakdown */
        .section-title {{
            font-size: 18px; font-weight: 600; margin-bottom: 16px;
            display: flex; align-items: center; gap: 8px;
        }}
        .category-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 32px;
        }}
        .category-card {{
            background: var(--surface);
            border: 1px solid var(--surface-border);
            padding: 12px 18px;
            border-radius: 10px;
            flex: 1 1 180px;
        }}
        .category-name {{ font-size: 13px; color: var(--text-secondary); }}
        .category-amount {{ font-size: 18px; font-weight: 600; color: var(--accent-blue); margin-top: 4px; }}

        /* Findings Table Container */
        .table-header-wrap {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        .table-hint {{
            font-size: 12px;
            color: var(--text-secondary);
        }}
        .table-container {{
            background: var(--surface);
            border: 1px solid var(--surface-border);
            border-radius: 14px;
            overflow-x: auto;
            margin-bottom: 32px;
            -webkit-overflow-scrolling: touch;
        }}
        .table-container::-webkit-scrollbar {{
            height: 8px;
        }}
        .table-container::-webkit-scrollbar-track {{
            background: var(--surface);
            border-radius: 8px;
        }}
        .table-container::-webkit-scrollbar-thumb {{
            background: var(--surface-border);
            border-radius: 8px;
        }}
        .table-container::-webkit-scrollbar-thumb:hover {{
            background: #334155;
        }}
        table {{
            width: 100%;
            min-width: 1060px;
            border-collapse: collapse;
            text-align: left;
            font-size: 13px;
        }}
        th {{
            background: rgba(15, 23, 42, 0.7);
            color: var(--text-secondary);
            font-weight: 600;
            padding: 14px 16px;
            border-bottom: 1px solid var(--surface-border);
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.05em;
            white-space: nowrap;
        }}
        td {{
            padding: 14px 16px;
            border-bottom: 1px solid var(--surface-border);
            vertical-align: middle;
        }}
        tr:last-child td {{ border-bottom: none; }}
        tr:hover td {{ background: rgba(255, 255, 255, 0.02); }}
        .res-id strong {{ font-family: 'JetBrains Mono', monospace; font-size: 13px; color: var(--text-primary); }}
        .res-name {{ color: var(--text-secondary); font-size: 12px; margin-top: 2px; }}
        .badge {{
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            display: inline-block;
            white-space: nowrap;
        }}
        .badge-type {{ background: rgba(56, 189, 248, 0.12); color: var(--accent-blue); }}
        .badge-status {{ background: rgba(245, 158, 11, 0.12); color: var(--accent-amber); }}
        .badge-age {{ background: rgba(168, 85, 247, 0.12); color: var(--accent-purple); }}
        .badge-na {{ background: rgba(148, 163, 184, 0.1); color: var(--text-secondary); }}
        code {{ font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--accent-blue); }}
        .details-cell {{ color: var(--text-secondary); max-width: 260px; line-height: 1.4; }}
        .cost-cell {{ font-weight: 700; color: var(--accent-red); font-size: 14px; white-space: nowrap; }}
        .rec-cell {{ color: #cbd5e1; font-size: 12px; min-width: 220px; max-width: 320px; line-height: 1.4; }}

        footer {{
            text-align: center;
            font-size: 13px;
            color: var(--text-secondary);
            border-top: 1px solid var(--surface-border);
            padding-top: 24px;
        }}
        footer a {{ color: var(--accent-blue); text-decoration: none; }}

        @media (max-width: 768px) {{
            body {{ padding: 20px 14px; }}
            header {{ flex-direction: column; align-items: flex-start; gap: 14px; }}
            .header-meta {{ text-align: left; }}
            .kpi-grid {{ grid-template-columns: 1fr; }}
            .dataset-banner {{ flex-direction: column; align-items: flex-start; gap: 8px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="brand">
                <h1>🛡️ CloudCostGuard</h1>
                <p>AWS Cloud FinOps & Automated Waste Elimination Engine</p>
            </div>
            <div class="header-meta">
                {mode_badge}
                <div>Audit Generated: <strong>{now_str}</strong></div>
            </div>
        </header>

        {banner_html}

        <div class="kpi-grid">
            <div class="kpi-card amber">
                <div class="kpi-label">Optimization Findings</div>
                <div class="kpi-value" style="color: var(--accent-amber);">{len(items)}</div>
                <div class="kpi-subtext">Across scanned AWS regions</div>
            </div>
            <div class="kpi-card red">
                <div class="kpi-label">Estimated Monthly Waste</div>
                <div class="kpi-value" style="color: var(--accent-red);">${total_monthly:,.2f}</div>
                <div class="kpi-subtext">Unattached or idle capacity</div>
            </div>
            <div class="kpi-card magenta">
                <div class="kpi-label">Projected Annual Cost</div>
                <div class="kpi-value" style="color: var(--accent-purple);">${total_annual:,.2f}</div>
                <div class="kpi-subtext">Cumulative annualized burn</div>
            </div>
            <div class="kpi-card green">
                <div class="kpi-label">Optimization Opportunity</div>
                <div class="kpi-value" style="color: var(--accent-green);">${total_monthly:,.2f}</div>
                <div class="kpi-subtext">Based on detected optimization candidates</div>
            </div>
        </div>

        <div class="section-title">📊 Waste Distribution by Service</div>
        <div class="category-row">
            {"".join(category_cards)}
        </div>

        <div class="table-header-wrap">
            <div class="section-title" style="margin-bottom: 0;">🔍 Resource Optimization Findings</div>
            <div class="table-hint">👉 Scroll horizontally for full details</div>
        </div>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Resource / Identifier</th>
                        <th>Service</th>
                        <th>Region</th>
                        <th>Condition</th>
                        <th>Configuration Details</th>
                        <th>Age</th>
                        <th>Monthly Waste</th>
                        <th>FinOps Recommendation</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(table_rows)}
                </tbody>
            </table>
        </div>

        <footer>
            <p>CloudCostGuard &bull; Created by <strong>Faizal Bagwan</strong> &bull;
               <a href="https://github.com/faizalbagwan786" target="_blank">GitHub Portfolio</a></p>
        </footer>
    </div>
</body>
</html>
"""
    parent_dir = os.path.dirname(output_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return output_path
