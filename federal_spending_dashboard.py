import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import webbrowser
import os

BASE_URL = "https://api.usaspending.gov/api/v2"

def fetch_top_agencies(fiscal_year=2024, limit=15):
    payload = {
        "category": "awarding_agency",
        "filters": {
            "time_period": [
                {"start_date": f"{fiscal_year-1}-10-01", "end_date": f"{fiscal_year}-09-30"}
            ],
        },
        "limit": limit,
        "page": 1,
    }
    resp = requests.post(
        f"{BASE_URL}/search/spending_by_category/awarding_agency/",
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    df = pd.DataFrame(results)
    if not df.empty:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df = df.sort_values("amount", ascending=True)
    return df

def fetch_yearly_totals():
    rows = []
    for year in range(2019, 2025):
        payload = {
            "category": "awarding_agency",
            "filters": {
                "time_period": [
                    {"start_date": f"{year-1}-10-01", "end_date": f"{year}-09-30"}
                ],
            },
            "limit": 100,
            "page": 1,
        }
        r = requests.post(
            f"{BASE_URL}/search/spending_by_category/awarding_agency/",
            json=payload,
            timeout=30,
        )
        if r.ok:
            results = r.json().get("results", [])
            total = sum(float(x.get("amount", 0) or 0) for x in results)
            rows.append({"fiscal_year": year, "total": total})
    return pd.DataFrame(rows)

def fetch_spending_by_type(fiscal_year=2024):
    type_groups = {
        "Contracts": ["A", "B", "C", "D"],
        "Grants": ["02", "03", "04", "05"],
        "Direct Payments": ["06", "07", "08", "09"],
        "Loans": ["10", "11"],
        "Other Financial": ["12", "13"],
    }
    rows = []
    for label, codes in type_groups.items():
        payload = {
            "category": "award_type",
            "filters": {
                "time_period": [
                    {"start_date": f"{fiscal_year-1}-10-01", "end_date": f"{fiscal_year}-09-30"}
                ],
                "award_type_codes": codes,
            },
            "limit": 1,
            "page": 1,
        }
        r = requests.post(
            f"{BASE_URL}/search/spending_by_category/awarding_agency/",
            json=payload,
            timeout=30,
        )
        if r.ok:
            results = r.json().get("results", [])
            total = sum(float(x.get("amount", 0) or 0) for x in results)
            rows.append({"type": label, "amount": total})
    return pd.DataFrame(rows)

def fetch_top_recipients(fiscal_year=2024, limit=10):
    payload = {
        "category": "recipient",
        "filters": {
            "time_period": [
                {"start_date": f"{fiscal_year-1}-10-01", "end_date": f"{fiscal_year}-09-30"}
            ],
        },
        "limit": limit,
        "page": 1,
    }
    resp = requests.post(
        f"{BASE_URL}/search/spending_by_category/recipient/",
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    df = pd.DataFrame(results)
    if not df.empty:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df = df.sort_values("amount", ascending=True)
    return df

def build_dashboard():
    print("Fetching federal spending data from USASpending.gov...")

    print("  → Top 15 agencies by spending (FY2024)...")
    df_agencies = fetch_top_agencies(fiscal_year=2024, limit=15)

    print("  → Yearly spending totals (FY2019–2024)...")
    df_yearly = fetch_yearly_totals()

    print("  → Spending by award type (FY2024)...")
    df_types = fetch_spending_by_type(fiscal_year=2024)

    print("  → Top 10 recipients (FY2024)...")
    df_recipients = fetch_top_recipients(fiscal_year=2024, limit=10)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Top 15 Agencies by Obligations — FY2024",
            "Total Federal Spending by Year (FY2019–2024)",
            "Spending by Award Type — FY2024",
            "Top 10 Recipients by Spending — FY2024",
        ),
        specs=[
            [{"type": "bar"}, {"type": "scatter"}],
            [{"type": "domain"}, {"type": "bar"}],
        ],
        vertical_spacing=0.18,
        horizontal_spacing=0.1,
    )

    # Chart 1: Top agencies horizontal bar
    if not df_agencies.empty:
        fig.add_trace(
            go.Bar(
                x=df_agencies["amount"] / 1e9,
                y=df_agencies["name"],
                orientation="h",
                marker_color="#1f77b4",
                hovertemplate="%{y}<br><b>$%{x:.1f}B</b><extra></extra>",
            ),
            row=1, col=1,
        )
        fig.update_xaxes(title_text="Obligations ($ Billions)", row=1, col=1)

    # Chart 2: Yearly totals line chart
    if not df_yearly.empty:
        fig.add_trace(
            go.Scatter(
                x=df_yearly["fiscal_year"],
                y=df_yearly["total"] / 1e12,
                mode="lines+markers+text",
                text=[f"${v:.1f}T" for v in df_yearly["total"] / 1e12],
                textposition="top center",
                line=dict(color="#ff7f0e", width=3),
                marker=dict(size=9),
                hovertemplate="FY%{x}<br><b>$%{y:.2f}T</b><extra></extra>",
            ),
            row=1, col=2,
        )
        fig.update_xaxes(title_text="Fiscal Year", row=1, col=2, dtick=1)
        fig.update_yaxes(title_text="Spending ($ Trillions)", row=1, col=2)

    # Chart 3: Pie chart by award type
    if not df_types.empty:
        df_types_filtered = df_types[df_types["amount"] > 0]
        fig.add_trace(
            go.Pie(
                labels=df_types_filtered["type"],
                values=df_types_filtered["amount"],
                hole=0.35,
                hovertemplate="%{label}<br><b>$%{value:.2e}</b><br>%{percent}<extra></extra>",
                textinfo="label+percent",
            ),
            row=2, col=1,
        )

    # Chart 4: Top recipients bar
    if not df_recipients.empty:
        fig.add_trace(
            go.Bar(
                x=df_recipients["amount"] / 1e9,
                y=df_recipients["name"],
                orientation="h",
                marker_color="#2ca02c",
                hovertemplate="%{y}<br><b>$%{x:.1f}B</b><extra></extra>",
            ),
            row=2, col=2,
        )
        fig.update_xaxes(title_text="Amount ($ Billions)", row=2, col=2)

    fig.update_layout(
        title=dict(
            text="U.S. Federal Spending Dashboard",
            font=dict(size=26, color="#333"),
            x=0.5,
        ),
        height=950,
        showlegend=False,
        template="plotly_white",
        margin=dict(t=100, b=40, l=40, r=40),
    )

    output = "federal_spending_dashboard.html"
    fig.write_html(output)
    print(f"\nDashboard saved → {output}")
    webbrowser.open(f"file://{os.path.abspath(output)}")
    print("Opening in browser...")

if __name__ == "__main__":
    build_dashboard()
