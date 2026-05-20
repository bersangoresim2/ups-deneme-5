import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent.parent
DASHBOARD_HISTORY_PATH = BASE_DIR / "dashboard_history.json"


def load_dashboard_history():
    if not DASHBOARD_HISTORY_PATH.exists():
        return []

    with open(DASHBOARD_HISTORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_daily_records(history):
    return [
        record for record in history
        if record.get("run_type") == "daily_routing"
    ]


def kpi_card(title, value, subtitle="", card_class="kpi-soft-1"):
    st.markdown(
        f"""
        <div class="kpi-card {card_class}">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def make_gauge(title, value, max_value, suffix=""):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": suffix, "font": {"size": 28}},
        title={
          "text": f"<b>{title}</b>",
          "font": {"size": 20, "color": "#2f2118"}
        },
        gauge={
            "axis": {"range": [0, max_value]},
            "bar": {"color": "#E8752A"},
            "bgcolor": "white",
            "borderwidth": 1,
            "bordercolor": "#E6D8CA",
            "steps": [
                {"range": [0, max_value * 0.5], "color": "#F7EFE7"},
                {"range": [max_value * 0.5, max_value], "color": "#E7D3C0"},
            ],
        }
    ))

    fig.update_layout(
        height=260,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="white",
        font=dict(color="#2f2118")
    )
    return fig


def render_daily_operating_dashboard():
    st.markdown("""
    <style>
    .dashboard-title {
        font-size: 34px;
        font-weight: 850;
        color: #2f2118;
        margin-bottom: 4px;
    }

    .dashboard-subtitle {
        font-size: 15px;
        color: #7b6b5e;
        margin-bottom: 22px;
    }

    .kpi-card {
        border-radius: 18px;
        padding: 18px 18px;
        height: 190px;
        width: 100%;
    
        display: flex;
        flex-direction: column;
        justify-content: space-between;

        box-shadow: 0 10px 26px rgba(90,52,24,0.12);
        margin-bottom: 14px;
        border: 1px solid rgba(120, 80, 40, 0.10);
    }
    
    .kpi-soft-1 { background: #FFF4DE; }
    .kpi-soft-2 { background: #FCE8D5; }
    .kpi-soft-3 { background: #F7E6C4; }
    .kpi-soft-4 { background: #FFE9B8; }
    .kpi-soft-5 { background: #F3D8BD; }
    .kpi-soft-6 { background: #EFD5B8; }
    .kpi-soft-7 { background: #FFF1C9; }

    .kpi-title {
        font-size: 14px;
        font-weight: 700;
        color: #6E533D;
        min-height: 42px;
    }

    .kpi-value {
        font-size: 30px;
        font-weight: 850;
        color: #2f2118;
        line-height: 1;
    }

    .kpi-subtitle {
        font-size: 12px;
        color: #8a7a6c;
        min-height: 36px;
        line-height: 1.4;
    }

    .status-banner {
        background: linear-gradient(135deg, #2f2118 0%, #7a4a26 100%);
        color: white;
        border-radius: 20px;
        padding: 22px 26px;
        box-shadow: 0 10px 28px rgba(47,33,24,0.22);
        margin-bottom: 20px;
    }

    .status-main {
        font-size: 23px;
        font-weight: 850;
        margin-bottom: 8px;
    }

    .status-sub {
        font-size: 14px;
        opacity: 0.92;
    }

    .section-title {
        font-size: 22px;
        font-weight: 800;
        color: #2f2118;
        margin-top: 18px;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="dashboard-title">Daily Operating Dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="dashboard-subtitle">Logistics dashboard with access point, fleet and delivery status.</div>',
        unsafe_allow_html=True
    )

    history = load_dashboard_history()
    daily_records = get_daily_records(history)

    if not daily_records:
        st.warning("No daily routing record found yet.")
        return

    dates = sorted(
        list(set(record.get("date") for record in daily_records if record.get("date"))),
        reverse=True
    )

    f1, f2 = st.columns(2)

    with f1:
        selected_date = st.selectbox(
            "Select operation date",
            dates,
            key="daily_dashboard_date"
        )

    records_for_date = [
        record for record in daily_records
        if record.get("date") == selected_date
    ]

    run_options = [
        f"{record.get('run_id')} | Cost: {record.get('daily_routing_cost')}"
        for record in records_for_date
    ]

    with f2:
        selected_run_label = st.selectbox(
            "Select daily routing run",
            run_options,
            key="daily_dashboard_run"
        )

    record = records_for_date[run_options.index(selected_run_label)]

    active_aps = record.get("active_aps_today", [])
    selected_vehicles = record.get("selected_vehicles", [])
    ap_loads = record.get("ap_loads", {})

    total_delivery = record.get("total_delivery_demand", 0)
    total_pickup = record.get("total_pickup_demand", 0)
    routing_cost = record.get("daily_routing_cost", 0)

    customer_count = record.get("customer_count_today", 0)

    peak_ap = "-"
    peak_delivery_load = 0

    if ap_loads:
      peak_ap, peak_values = max(
        ap_loads.items(),
        key=lambda item: item[1].get("delivery_load", 0)
      )
      peak_delivery_load = peak_values.get("delivery_load", 0)

    st.markdown(
        f"""
        <div class="status-banner">
            <div class="status-main">🟢 Daily Operation Completed Successfully</div>
            <div class="status-sub">
                {record.get("active_ap_count_today", 0)} AP active •
                {record.get("used_vehicle_count", 0)} vehicle used •
                {record.get("customer_count_today", 0)} customers assigned •
                Solver: {record.get("termination", "-")}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)

    with c1:
       kpi_card("Active APs", record.get("active_ap_count_today", 0), ", ".join(active_aps), "kpi-soft-1")

    with c2:
       kpi_card("Used Vehicles", record.get("used_vehicle_count", 0), ", ".join(selected_vehicles), "kpi-soft-2")
 
    with c3:
       kpi_card("Routing Distance", routing_cost, "Daily route distance", "kpi-soft-3")

    with c4:
       kpi_card("Delivery Demand", total_delivery, "Total delivery", "kpi-soft-4")

    with c5:
       kpi_card("Pickup Demand", total_pickup, "Total pickup", "kpi-soft-5")

    with c6:
       kpi_card("Peak AP", peak_ap, f"{peak_delivery_load} delivery load", "kpi-soft-6")

    with c7:
       kpi_card(
         "Max Assignment Distance",
         record.get("farthest_customer_distance", 0),
         "Farthest customer distance",
         "kpi-soft-7"
        )

    

    if ap_loads:
        ap_rows = []
        for ap, values in ap_loads.items():
            ap_rows.append({
                "Access Point": ap,
                "Delivery Demand": values.get("delivery_load", 0),
                "Pickup Demand": values.get("pickup_load", 0),
                "Assigned Customers": values.get("customer_count", 0),
            })

        ap_df = pd.DataFrame(ap_rows)

        used_vehicle = record.get("used_vehicle_count", 0)
        selected_vehicle = record.get("selected_vehicle_count", 0)
        vehicle_rate = round((used_vehicle / selected_vehicle) * 100, 1) if selected_vehicle else 0

        chart_colors = ["#E8752A", "#F4B860", "#8B4A24", "#D99A5B"]

        st.markdown("""
        <style>
        .chart-box {
          background: white;
          border-radius: 18px;
          padding: 18px 18px 10px 18px;
          box-shadow: 0 8px 22px rgba(90,52,24,0.08);
          border: 1px solid #EFE3D7;
          margin-bottom: 22px;
        }

        .chart-title {
          font-size: 22px;
          font-weight: 800;
          color: #2f2118;
          margin-bottom: 6px;
          line-height: 1.2;
        }

        .chart-subtitle {
          font-size: 13px;
          color: #8a7a6c;
          margin-bottom: 8px;
        }
        </style>
        """, unsafe_allow_html=True)

        g1, g2, g3 = st.columns(3, gap="medium")

        with g1:
            st.plotly_chart(
                make_gauge("Vehicle Usage", vehicle_rate, 100, "%"),
                width="stretch"
            )


        with g2:
            fig_load = px.pie(
                ap_df,
                names="Access Point",
                values="Delivery Demand",
                hole=0.55,
                color_discrete_sequence=["#D8B08C", "#F4E1C8"]
            )

            fig_load.update_traces(
                textinfo="percent",
                textfont_size=13,
                marker=dict(line=dict(color="white", width=2))
            )

            fig_load.update_layout(
                title={
                  "text": "<b>AP Load Distribution</b>",
                  "font": {"size": 20, "color": "#2f2118"}
                },
                height=260,
                margin=dict(l=10, r=10, t=60, b=0),
                paper_bgcolor="white",
                plot_bgcolor="white",
                legend=dict(
                    orientation="h",
                    y=-0.08,
                    x=0.5,
                    xanchor="center"
                )
            )

            st.plotly_chart(fig_load, width="stretch")


        with g3:
            fig_customer = px.pie(
                ap_df,
                names="Access Point",
                values="Assigned Customers",
                hole=0.55,
                color_discrete_sequence=chart_colors
            )

            fig_customer.update_traces(
                textinfo="percent",
                textfont_size=13,
                marker=dict(line=dict(color="white", width=2))
            )

            fig_customer.update_layout(
                title={
                   "text": "<b>Customer Distribution</b>",
                   "font": {"size": 20, "color": "#2f2118"}
                },
                height=260,
                margin=dict(l=10, r=10, t=60, b=0),
                paper_bgcolor="white",
                plot_bgcolor="white",
                legend=dict(
                    orientation="h",
                    y=-0.08,
                    x=0.5,
                    xanchor="center"
                )
            )

            st.plotly_chart(fig_customer, width="stretch")

        b1, b2 = st.columns([1.2, 1])

        with b1:
            st.markdown('<div class="section-title">Delivery & Pickup by AP</div>', unsafe_allow_html=True)
            fig_bar = go.Figure()

            fig_bar.add_trace(go.Bar(
                x=ap_df["Access Point"],
                y=ap_df["Delivery Demand"],
                name="Delivery Demand",
                marker_color="#E8752A"
            ))

            fig_bar.add_trace(go.Bar(
                x=ap_df["Access Point"],
                y=ap_df["Pickup Demand"],
                name="Pickup Demand",
                marker_color="#D8B08C"
            ))

            fig_bar.update_layout(
                barmode="group",
                height=330,
                margin=dict(l=20, r=20, t=20, b=20),
                paper_bgcolor="white",
                plot_bgcolor="white",
                legend=dict(orientation="h", y=-0.2)
            )

            st.plotly_chart(fig_bar, width="stretch")

        with b2:
            st.markdown('<div class="section-title">Routing Cost Trend</div>', unsafe_allow_html=True)

            trend_records = sorted(
                daily_records,
                key=lambda r: r.get("run_id", "")
            )

            trend_df = pd.DataFrame([
                {
                    "Run": r.get("run_id"),
                    "Cost": r.get("daily_routing_cost"),
                    "Date": r.get("date")
                }
                for r in trend_records
                if r.get("daily_routing_cost") is not None
            ])

            if not trend_df.empty:
                fig_trend = px.line(
                    trend_df,
                    x="Run",
                    y="Cost",
                    markers=True,
                    color_discrete_sequence=["#8B4A24"]
                )
                fig_trend.update_traces(
                    line=dict(width=4),
                    marker=dict(size=8, color="#E8752A")
                )

                fig_trend.update_layout(
                    height=330,
                    margin=dict(l=20, r=20, t=20, b=20),
                    paper_bgcolor="white",
                    plot_bgcolor="white",
                    xaxis_title="",
                    yaxis_title="Cost"
                )

                st.plotly_chart(fig_trend, width="stretch")
            else:
                st.info("No cost trend data found.")

    else:
        st.info("No AP load data found for this daily run.")