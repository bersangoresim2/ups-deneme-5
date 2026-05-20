import json
from pathlib import Path
from collections import Counter

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent.parent
DASHBOARD_HISTORY_PATH = BASE_DIR / "dashboard_history.json"


def load_dashboard_history():
    if not DASHBOARD_HISTORY_PATH.exists():
        return []

    with open(DASHBOARD_HISTORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_strategic_records(history):
    return [
        r for r in history
        if r.get("run_type") in ["strategic_optimization", "reoptimization"]
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


def render_strategic_dashboard():

    # =========================================================
    # STYLE
    # =========================================================
    st.markdown("""
    <style>

    .dashboard-title {
        font-size: 36px;
        font-weight: 900;
        color: #2f2118;
        margin-bottom: 6px;
    }

    .dashboard-subtitle {
        font-size: 15px;
        color: #7b6b5e;
        margin-bottom: 28px;
    }

    .section-title {
        font-size: 28px;
        font-weight: 850;
        color: #2f2118;
        margin-top: 38px;
        margin-bottom: 16px;
    }

    .section-subtitle {
        font-size: 14px;
        color: #7b6b5e;
        margin-bottom: 20px;
    }

    .kpi-card {
      height: 180px;
      width: 100%;
      border-radius: 20px;
      padding: 18px 18px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow: 0 10px 26px rgba(90,52,24,0.10);
      border: 1px solid rgba(120,80,40,0.08);
      transition: 0.2s ease;
    }

    .kpi-card:hover {
       transform: translateY(-3px);
    }

    .kpi-soft-1 {
      background: #F8EBDD;
    }

    .kpi-soft-2 {
      background: #F6E4C9;
    }

    .kpi-soft-3 {
      background: #F5EBCF;
    }

    .kpi-soft-4 {
      background: #EED8BF;
    }

    .kpi-soft-5 {
      background: #F7E7BE;
    }

    .kpi-title {
      font-size: 14px;
      font-weight: 700;
      color: #7A5A42;
      line-height: 1.4;
    }

    .kpi-value {
      font-size: 30px;
      font-weight: 850;
      color: #2f2118;
      line-height: 1;
    }

    .kpi-subtitle {
      font-size: 11px;
      color: #8B7765;
      line-height: 1.5;
    }

    .banner {
        background: linear-gradient(135deg, #2f2118 0%, #7a4a26 100%);
        color: white;
        border-radius: 22px;
        padding: 24px 28px;
        margin-bottom: 24px;
        box-shadow: 0 10px 28px rgba(47,33,24,0.22);
    }

    .banner-title {
        font-size: 24px;
        font-weight: 850;
        margin-bottom: 8px;
    }

    .banner-sub {
        font-size: 14px;
        opacity: 0.92;
    }

    </style>
    """, unsafe_allow_html=True)

    # =========================================================
    # LOAD DATA
    # =========================================================
    history = load_dashboard_history()
    strategic_records = get_strategic_records(history)

    if not strategic_records:
        st.warning("No strategic optimization history found.")
        return

    # =========================================================
    # HEADER
    # =========================================================
    st.markdown(
        '<div class="dashboard-title">Strategic Network Planning Dashboard</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="dashboard-subtitle">Long-term strategic insights into access point selection, cost behavior, customer distance optimization and assignment patterns.</div>',
        unsafe_allow_html=True
    )

    warm_discrete = ["#E8752A", "#F4B860", "#8B4A24", "#D8B08C", "#F7E7BE"]

    warm_component_map = {
      "AP Fixed Cost": "#8B4A24",
      "Routing Cost": "#E8752A",
      "Vehicle Fixed Cost": "#D8B08C",
      "Variable Load Cost": "#F4B860",
    }

    warm_demand_map = {
      "total_delivery": "#E8752A",
      "total_pickup": "#D8B08C",
    }

    # =========================================================
    # GLOBAL DATA
    # =========================================================
    all_opened_aps = []

    for record in strategic_records:
        all_opened_aps.extend(record.get("opened_aps", []))

    most_used_ap = "-"
    if all_opened_aps:
        most_used_ap = Counter(all_opened_aps).most_common(1)[0][0]

    valid_df = pd.DataFrame([
        {
            "Run ID": r.get("run_id"),
            "Run Type": r.get("run_type"),
            "Total Cost": r.get("total_cost"),
            "Dmax": r.get("dmax"),
            "AP Count": r.get("ap_count"),
            "Opened APs": ", ".join(r.get("opened_aps", []))
        }
        for r in strategic_records
        if r.get("total_cost") is not None and r.get("dmax") is not None
    ])

    # =========================================================
    # EXECUTIVE OVERVIEW
    # =========================================================
    st.markdown(
        """
        <div class="section-title">Optimization Insights</div>
        <div class="section-subtitle">
        Strategic performance overview across all optimization runs.
        </div>
        """,
        unsafe_allow_html=True
    )

    if not valid_df.empty:

        lowest_cost_row = valid_df.loc[valid_df["Total Cost"].idxmin()]
        lowest_dmax_row = valid_df.loc[valid_df["Dmax"].idxmin()]
        min_ap_row = valid_df.loc[valid_df["AP Count"].idxmin()]

        c1, c2, c3, c4, c5 = st.columns(5)

        with c1:
            kpi_card(
              "Minimum Operational Cost",
                lowest_cost_row["Total Cost"],
                f"Run: {lowest_cost_row['Run ID']}",
                "kpi-soft-1"
            )

        with c2:
            kpi_card(
                "Minimum Distance Between Customer and AP",
                lowest_dmax_row["Dmax"],
                f"Run: {lowest_dmax_row['Run ID']}",
                "kpi-soft-2"
            )

        with c3:
            kpi_card(
                "Minimum AP Count",
                min_ap_row["AP Count"],
                f"APs: {min_ap_row['Opened APs']}",
                "kpi-soft-3"
            )

        with c4:
            kpi_card(
                "Critical Access Points",
                most_used_ap,
                "Historical frequency",
                "kpi-soft-4"
            )

        with c5:
            kpi_card(
                "Strategic Runs",
                len(strategic_records),
                "Optimization history",
                "kpi-soft-5"
            )

    # =========================================================
    # HISTORICAL NETWORK INTELLIGENCE
    # =========================================================
    st.markdown(
        """
        <div class="section-title">Strategic Patterns & Trends</div>
        <div class="section-subtitle">
        Long-term trends in operational cost, access point decisions, customer assignments and routing behavior.
        </div>
        """,
        unsafe_allow_html=True
    )

    # -------------------------
    # COST VS DMAX
    # -------------------------
    left, right = st.columns([1, 1])

    with left:

        st.markdown("### Cost- Customer Satisfaction Trade-off")

        scatter_df = pd.DataFrame([
            {
                "Run ID": r.get("run_id"),
                "Run Type": r.get("run_type"),
                "Total Cost": r.get("total_cost"),
                "Dmax": r.get("dmax"),
                "AP Count": r.get("ap_count"),
                "Opened APs": ", ".join(r.get("opened_aps", []))
            }
            for r in strategic_records
            if r.get("total_cost") is not None and r.get("dmax") is not None
        ])

        if not scatter_df.empty:

            fig_scatter = px.scatter(
                scatter_df,
                x="Total Cost",
                y="Dmax",
                color="Run Type",
                size="AP Count",
                hover_data=["Run ID", "Opened APs"],
                color_discrete_map={
                  "strategic_optimization": "#E8752A",
                  "reoptimization": "#D8B08C"
                }
            )

            fig_scatter.update_traces(
                marker=dict(
                  size=16,
                  line=dict(color="white", width=2)
                )
            )

            fig_scatter.update_layout(
                height=360,
                paper_bgcolor="white",
                plot_bgcolor="white",
                font=dict(color="#2f2118"),
                legend_title_text="Run Type"
            )

            st.plotly_chart(fig_scatter, width="stretch")

    with right:

        st.markdown("### AP Count Trend")

        ap_trend_df = pd.DataFrame([
            {
                "Run ID": r.get("run_id"),
                "AP Count": r.get("ap_count"),
                "Run Type": r.get("run_type")
            }
            for r in strategic_records
            if r.get("ap_count") is not None
        ])

        if not ap_trend_df.empty:

            fig_ap_trend = px.line(
                ap_trend_df,
                x="Run ID",
                y="AP Count",
                color="Run Type",
                markers=True,
                color_discrete_map={
                   "strategic_optimization": "#8B4A24",
                   "reoptimization": "#E8B06A"
                }
            )

            fig_ap_trend.update_traces(
               line=dict(width=4),
               marker=dict(size=9)
            )

            fig_ap_trend.update_layout(
                height=360,
                paper_bgcolor="white",
                plot_bgcolor="white",
                font=dict(color="#2f2118")
            )

            st.plotly_chart(fig_ap_trend, width="stretch")

    # -------------------------
    # AP FREQUENCY + HEATMAP
    # -------------------------
    left2, right2 = st.columns([1, 1])

    with left2:

        st.markdown("### Access Point Utilization Frequency")

        ap_frequency = Counter(all_opened_aps)

        if ap_frequency:

            ap_freq_df = pd.DataFrame([
                {"Access Point": ap, "Frequency": count}
                for ap, count in ap_frequency.items()
            ]).sort_values("Frequency", ascending=False)

            fig_ap_freq = px.bar(
                ap_freq_df,
                x="Access Point",
                y="Frequency",
                text="Frequency",
                color="Frequency",
                color_continuous_scale=[
                   "#F7E7BE",
                   "#E8B06A",
                   "#C97A36",
                   "#8B4A24"
                ]
            )
            fig_ap_freq.update_traces(
               marker_line_color="white",
               marker_line_width=1.5
            )

            fig_ap_freq.update_layout(
                 height=360,
                 paper_bgcolor="white",
                 plot_bgcolor="white",
                 showlegend=False,
                 font=dict(color="#2f2118")
            )

            st.plotly_chart(fig_ap_freq, width="stretch")

    with right2:

        st.markdown("### Access Point Collaboration Heatmap")

        ap_sets = [
            r.get("opened_aps", [])
            for r in strategic_records
            if r.get("opened_aps")
        ]

        unique_aps = sorted(set(ap for aps in ap_sets for ap in aps))

        if unique_aps:

            matrix = pd.DataFrame(
                0,
                index=unique_aps,
                columns=unique_aps
            )

            for aps in ap_sets:
                for ap1 in aps:
                    for ap2 in aps:
                        matrix.loc[ap1, ap2] += 1

            heatmap_fig = px.imshow(
                matrix,
                text_auto=True,
                aspect="auto",
                color_continuous_scale=[
                  "#FFF4DE",
                  "#F4C27A",
                  "#C97A36",
                  "#6B3E1F"
                ]
            )

            heatmap_fig.update_layout(
                height=360,
                paper_bgcolor="white",
                font=dict(color="#2f2118")
            )

            st.plotly_chart(heatmap_fig, width="stretch")

    # -------------------------
    # COST COMPONENTS
    # -------------------------
    st.markdown("### Cost Component Comparison Across Runs")

    component_rows = []

    for r in strategic_records:

        breakdowns = r.get("cost_breakdown_by_scenario", {})

        for scenario, b in breakdowns.items():

            component_rows.extend([
                {
                    "Run ID": r.get("run_id"),
                    "Component": "AP Fixed Cost",
                    "Cost": b.get("ap_fixed_cost", 0)
                },
                {
                    "Run ID": r.get("run_id"),
                    "Component": "Routing Cost",
                    "Cost": b.get("routing_cost", 0)
                },
                {
                    "Run ID": r.get("run_id"),
                    "Component": "Vehicle Fixed Cost",
                    "Cost": b.get("vehicle_fixed_cost", 0)
                },
                {
                    "Run ID": r.get("run_id"),
                    "Component": "Variable Load Cost",
                    "Cost": b.get("variable_load_cost", 0)
                },
            ])

    component_df = pd.DataFrame(component_rows)

    if not component_df.empty:

        stacked_fig = px.bar(
            component_df,
            x="Run ID",
            y="Cost",
            color="Component",
            barmode="stack",
            color_discrete_map=warm_component_map
        )

        stacked_fig.update_layout(
            height=420,
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(color="#2f2118")
        )

        st.plotly_chart(stacked_fig, width="stretch")

    # -------------------------
    # ROUTES + ASSIGNMENTS
    # -------------------------
    route_rows = []
    assignment_history_rows = []

    for r in strategic_records:

        for arc in r.get("used_route_arcs", []):
            route_rows.append({
                "Route Arc": f"{arc.get('from')} → {arc.get('to')}",
                "Run ID": r.get("run_id")
            })

        for assignment in r.get("customer_assignments", []):
            assignment_history_rows.append({
                "Assignment":
                    f"{assignment.get('customer')} → {assignment.get('access_point')}"
            })

    h1, h2 = st.columns([1, 1])

    with h1:

        st.markdown("### Dominant Logistics Corridors")

        if route_rows:

            route_df = pd.DataFrame(route_rows)

            route_freq_df = (
                route_df.groupby("Route Arc")
                .size()
                .reset_index(name="Frequency")
                .sort_values("Frequency", ascending=False)
                .head(10)
            )

            fig_routes = px.bar(
                route_freq_df,
                x="Frequency",
                y="Route Arc",
                orientation="h",
                text="Frequency",
                color="Frequency",
                color_continuous_scale=["#F7E7BE", "#F4B860", "#E8752A", "#8B4A24"]
            )

            fig_routes.update_layout(
               height=340,
               margin=dict(l=10, r=10, t=30, b=10),
               paper_bgcolor="white",
               plot_bgcolor="white",
               showlegend=False,
               font=dict(color="#2f2118")
            )

            st.plotly_chart(fig_routes, width="stretch")

    with h2:

     st.markdown("### Most Frequent Customer Assignments")

     if assignment_history_rows:

        assignment_df = pd.DataFrame(assignment_history_rows)

        assignment_freq_df = (
            assignment_df.groupby("Assignment")
            .size()
            .reset_index(name="Frequency")
            .sort_values("Frequency", ascending=False)
            .head(10)
        )

        fig_assign = px.pie(
         assignment_freq_df,
         names="Assignment",
         values="Frequency",
         hole=0.68,
         color_discrete_sequence=warm_discrete,
        )

        fig_assign.update_traces(
          textinfo="none",
          marker=dict(line=dict(color="white", width=2))
        )

        fig_assign.update_layout(
          height=340,
          width=340,
          margin=dict(l=0, r=0, t=20, b=0),
          paper_bgcolor="white",
          font=dict(color="#2f2118"),
          showlegend=True,
          legend=dict(
             orientation="h",
             y=-0.15,
             x=0.5,
             xanchor="center"
          )
        )

        st.plotly_chart(
          fig_assign,
          use_container_width=False
        )
        
    
    # =========================================================
    # REOPTIMIZATION
    # =========================================================
    st.markdown(
        """
        <div class="section-title">Re-optimization Impact</div>
        <div class="section-subtitle">
        Cost impact after strategic re-optimization decisions.
        </div>
        """,
        unsafe_allow_html=True
    )

    reopt_records = [
        r for r in strategic_records
        if r.get("run_type") == "reoptimization"
    ]

    if reopt_records:

        selected_reopt = reopt_records[-1]

        waterfall_fig = go.Figure(go.Waterfall(
           name="Reoptimization",
           orientation="v",

           measure=["absolute", "relative", "total"],

           x=[
            "Previous Cost",
            "Cost Change",
            "Re-optimized Cost"
           ],

           y=[
            selected_reopt.get("previous_cost", 0),
            selected_reopt.get("cost_difference", 0),
            selected_reopt.get("new_cost", 0)
           ],

           increasing={
              "marker": {
                "color": "#E8752A"
               }
           },

           decreasing={
              "marker": {
                "color": "#8B4A24"
              }
           },

           totals={
              "marker": {
                "color": "#D8B08C"
              }
           },

           connector={
              "line": {
                "color": "#8B4A24",
                "width": 2
              }
           } 
        ))

        waterfall_fig.update_layout(
            height=400,
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(
              color="#2f2118",
              size=13
             ),

            waterfallgap=0.35
        )

        st.plotly_chart(waterfall_fig, width="stretch")

    # =========================================================
    # SELECTED SOLUTION DEEP DIVE
    # =========================================================
    st.markdown(
        """
        <div class="section-title">Selected Solution Deep Dive</div>
        <div class="section-subtitle">
        Detailed analysis for one selected strategic solution and scenario.
        </div>
        """,
        unsafe_allow_html=True
    )

    selected_run = st.selectbox(
        "Select strategic run",
        strategic_records,
        format_func=lambda r:
            f"{r.get('run_id')} | {r.get('run_type')} | Cost: {r.get('total_cost')} | Dmax: {r.get('dmax')}"
    )

    if "cost_breakdown_by_scenario" not in selected_run:
        st.warning("Selected run does not contain detailed breakdown data.")
        return

    scenario_names = list(
        selected_run.get("cost_breakdown_by_scenario", {}).keys()
    )

    if len(scenario_names) == 1:
        selected_scenario = scenario_names[0]
    else:
        selected_scenario = st.selectbox(
            "Select scenario",
            scenario_names
        )

    breakdown = selected_run["cost_breakdown_by_scenario"][selected_scenario]

    total_cost = selected_run.get("total_cost", 0)
    dmax = selected_run.get("dmax", 0)
    ap_count = selected_run.get("ap_count", 0)
    opened_aps = selected_run.get("opened_aps", [])

    st.markdown(
        f"""
        <div class="banner">
            <div class="banner-title">Selected Strategic Solution</div>
            <div class="banner-sub">
                Run Type: {selected_run.get("run_type")} •
                Scenario: {selected_scenario} •
                Opened APs: {", ".join(opened_aps)}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # =========================================================
    # KPI
    # =========================================================
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        kpi_card("Total Cost", total_cost, "", "kpi-soft-1")

    with c2:
        kpi_card("Max Customer-AP Distance", dmax, "", "kpi-soft-2")

    with c3:
        kpi_card("Opened AP Count", ap_count, "", "kpi-soft-3")

    with c4:
        kpi_card("Most Used AP", most_used_ap, "", "kpi-soft-4")

    c5, c6, c7, c8 = st.columns(4)

    with c5:
        kpi_card("AP Fixed Cost", breakdown.get("ap_fixed_cost", 0), "", "kpi-soft-5")

    with c6:
        kpi_card("Routing Cost", breakdown.get("routing_cost", 0), "", "kpi-soft-1")

    with c7:
        kpi_card("Vehicle Fixed Cost", breakdown.get("vehicle_fixed_cost", 0), "", "kpi-soft-2")

    with c8:
        kpi_card("Variable Load Cost", breakdown.get("variable_load_cost", 0), "", "kpi-soft-3")
    # =========================================================
    # COST BREAKDOWN + ASSIGNMENT
    # =========================================================
    left, right = st.columns([1, 1])

    with left:

        st.markdown("### Cost Breakdown")

        breakdown_df = pd.DataFrame([
            {
                "Cost Component": "AP Fixed Cost",
                "Cost": breakdown.get("ap_fixed_cost", 0)
            },
            {
                "Cost Component": "Routing Cost",
                "Cost": breakdown.get("routing_cost", 0)
            },
            {
                "Cost Component": "Vehicle Fixed Cost",
                "Cost": breakdown.get("vehicle_fixed_cost", 0)
            },
            {
                "Cost Component": "Variable Load Cost",
                "Cost": breakdown.get("variable_load_cost", 0)
            },
        ])

        fig_breakdown = px.pie(
            breakdown_df,
            names="Cost Component",
            values="Cost",
            hole=0.55,
            color="Cost Component",
            color_discrete_map=warm_component_map
        )

        fig_breakdown.update_traces(
            marker=dict(line=dict(color="white", width=2))
        )

        fig_breakdown.update_layout(
            height=360,
            paper_bgcolor="white",
            font=dict(color="#2f2118")
        )

        st.plotly_chart(fig_breakdown, width="stretch")

    with right:

        st.markdown("### Customer Assignment by AP")

        assignment_rows = selected_run.get("customer_assignments", [])

        if assignment_rows:

            assignment_df = pd.DataFrame(assignment_rows)

            assignment_count_df = (
                assignment_df.groupby("access_point")
                .size()
                .reset_index(name="Assigned Customers")
            )

            fig_assignment = px.pie(
                assignment_count_df,
                names="access_point",
                values="Assigned Customers",
                hole=0.55,
                color_discrete_sequence=["#E8752A", "#D8B08C", "#F4B860", "#8B4A24"]
            )

            fig_assignment.update_traces(
                marker=dict(line=dict(color="white", width=2))
            )

            fig_assignment.update_layout(
                height=360,
                paper_bgcolor="white",
                font=dict(color="#2f2118")
            )

            st.plotly_chart(fig_assignment, width="stretch")

    # =========================================================
    # DEMAND
    # =========================================================
    demand_rows = selected_run.get("customer_demand_summary", [])

    if demand_rows:

        demand_df = pd.DataFrame(demand_rows).sort_values(
            "total_demand",
            ascending=False
        )

        left3, right3 = st.columns([1, 1])

        with left3:

            st.markdown("### Top Demand Customers")

            top_demand_df = demand_df.head(7)

            fig_top_demand = px.bar(
                top_demand_df,
                x="customer",
                y="total_demand",
                color="total_demand",
                text="total_demand",
                color_continuous_scale=["#F7E7BE", "#F4B860", "#E8752A", "#8B4A24"]
            )

            fig_top_demand.update_layout(
                height=360,
                paper_bgcolor="white",
                plot_bgcolor="white",
                showlegend=False,
                font=dict(color="#2f2118")
            )

            st.plotly_chart(fig_top_demand, width="stretch")

        with right3:

            st.markdown("### Demand Mix by Customer")

            demand_mix_df = demand_df.head(7).melt(
                id_vars=["customer"],
                value_vars=["total_delivery", "total_pickup"],
                var_name="Demand Type",
                value_name="Demand"
            )

            fig_mix = px.bar(
                demand_mix_df,
                x="customer",
                y="Demand",
                color="Demand Type",
                barmode="stack",
                color_discrete_map=warm_demand_map
            )

            fig_mix.update_layout(
                height=360,
                paper_bgcolor="white",
                plot_bgcolor="white",
                font=dict(color="#2f2118")
            )

            st.plotly_chart(fig_mix, width="stretch")