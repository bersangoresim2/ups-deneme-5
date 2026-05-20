import streamlit as st
import pandas as pd
import json
import base64
import tempfile
import subprocess
import sys
import time
import plotly.express as px
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DASHBOARD_HISTORY_PATH = BASE_DIR / "dashboard_history.json"
HISTORY_PATH = BASE_DIR / "optimization_history.json"
SOLVER_INPUT_PATH = BASE_DIR / "solver_input.json"
SOLVER_RESULT_PATH = BASE_DIR / "solver_result.json"
SOLVER_RUNNER_PATH = BASE_DIR / "solver_runner.py"


def load_history():
    if HISTORY_PATH.exists():
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history(history):
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def save_dashboard_history(record):
    if DASHBOARD_HISTORY_PATH.exists():
        with open(DASHBOARD_HISTORY_PATH, "r", encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = []

    history.append(record)

    with open(DASHBOARD_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def decode_history_file_to_excel(record):
    file_base64 = record.get("file_data_base64")

    if not file_base64:
        st.error("This history record does not contain the Excel file itself.")
        return None

    file_bytes = base64.b64decode(file_base64)

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    temp_file.write(file_bytes)
    temp_file.close()

    return temp_file.name


def start_reoptimization(record, new_ap_count, selected_display_index):
    if SOLVER_RESULT_PATH.exists():
        SOLVER_RESULT_PATH.unlink()

    excel_path = decode_history_file_to_excel(record)

    if excel_path is None:
        return
    
    cost_gap = st.session_state.get("reopt_cost_gap_input", 0.0) / 100.0
    dmax_gap = st.session_state.get("reopt_dmax_gap_input", 0.0) / 100.0

    config = {
        "excel_path": excel_path,
        "result_path": str(SOLVER_RESULT_PATH),
        "candidate_ap_count": 10,
        "user_ap_count": int(new_ap_count),
        "optimal_ap_count": int(record.get("opened_ap_count")),
        "is_reoptimization": True,
        "cost_gap": cost_gap,
        "dmax_gap": dmax_gap
    }

    with open(SOLVER_INPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

    process = subprocess.Popen(
        [sys.executable, str(SOLVER_RUNNER_PATH), str(SOLVER_INPUT_PATH)]
    )

    st.session_state["reopt_process"] = process
    st.session_state["reopt_running"] = True
    st.session_state["reopt_selected_record"] = record
    st.session_state["reopt_new_ap_count"] = int(new_ap_count)
    st.session_state["reopt_base_solution"] = int(selected_display_index)
    st.session_state["reopt_result_saved"] = False


def stop_reoptimization():
    process = st.session_state.get("reopt_process")

    if process and process.poll() is None:
        process.terminate()

    st.session_state["reopt_running"] = False
    st.session_state["reopt_process"] = None
    st.warning("Re-optimization stopped by user.")


def read_solver_result():
    if SOLVER_RESULT_PATH.exists():
        with open(SOLVER_RESULT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_reoptimization_to_history(old_record, result, new_ap_count):
    history = load_history()

    opened_ap = result.get("opened_ap_count", result.get("optimal_ap_count"))
    opened_ap_list = result.get("opened_ap_list", [])

    new_record = {
        "run_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

        "file_name": old_record.get("file_name"),
        "file_data_base64": old_record.get("file_data_base64"),

        "best_cost": result.get("best_cost"),
        "dmax_val": result.get("dmax_val"),
        "opened_ap_count": opened_ap,
        "opened_ap_list": opened_ap_list,

        "cost_gap": st.session_state.get("reopt_cost_gap_input", 0.0),
        "dmax_gap": st.session_state.get("reopt_dmax_gap_input", 0.0),

        "solver_status": result.get("solver_status"),
        "termination": result.get("termination"),
        "state": result.get("state"),

        "is_reoptimization": True,
        "run_type": "Reoptimized",
        "base_solution": st.session_state.get("reopt_base_solution"),
        "reoptimized_from": old_record.get("run_date"),
        "previous_ap_count": old_record.get("opened_ap_count"),
        "new_user_ap_count": int(new_ap_count)
    }

    history.append(new_record)
    save_history(history)


def show_reoptimization_result(result):
    st.success("Re-optimization completed.")

    opened_ap_count = result.get("opened_ap_count", result.get("optimal_ap_count"))
    opened_ap_list = result.get("opened_ap_list", [])

    col1, col2, col3 = st.columns(3)

    col1.metric("New Cost", result.get("best_cost"))
    col2.metric("New Dmax", result.get("dmax_val"))
    col3.metric("Opened AP Count", opened_ap_count)

    if opened_ap_list:
        st.subheader("Opened Access Points")
        st.dataframe(
            pd.DataFrame({"Opened AP": opened_ap_list}),
            width="stretch"
        )
    else:
        st.warning("Opened AP list could not be found in the result.")


def show_improve_solution_page():
    st.title("Re-optimization Panel")

    if "reopt_process" not in st.session_state:
        st.session_state["reopt_process"] = None

    if "reopt_running" not in st.session_state:
        st.session_state["reopt_running"] = False

    if "reopt_result_saved" not in st.session_state:
        st.session_state["reopt_result_saved"] = False

    history = load_history()

    if not history:
        st.info("There is no saved optimization history yet.")
        return

    valid_history = [
        h for h in history
        if h.get("file_data_base64") is not None
    ]

    if not valid_history:
        st.warning("No re-optimizable record found. The Excel file itself is missing in older history records.")
        return

    history_df = pd.DataFrame([
        {
            "Display Index": idx + 1,
            "Run Type": h.get("run_type", "Reoptimized" if h.get("is_reoptimization", False)
            else "Initial"
            ),
           
            "Run Date": h.get("run_date"),
            "File Name": h.get("file_name"),
            "Cost": h.get("best_cost"),
            "Dmax": h.get("dmax_val"),
            "Cost Gap (%)": h.get("cost_gap", "-"),
            "Dmax Gap (%)": h.get("dmax_gap", "-"),
            "Opened AP Count": h.get("opened_ap_count"),
            "Opened AP List": ", ".join(h.get("opened_ap_list", [])) if h.get("opened_ap_list") else "-",
        }
        for idx, h in enumerate(valid_history)
    ])
    col1, col2 = st.columns([6, 1])
    with col1:
       st.subheader("Optimization History")
    with col2:
       st.markdown(
        """
        <style>
        div[data-testid="stButton"] button[kind="secondary"] {
            border: none !important;
            background: transparent !important;
            box-shadow: none !important;
            padding: 0 !important;
            font-size: 24px !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    if st.button("↻", key="refresh_history_icon", help="Refresh history"):
        st.rerun()

    history_df_with_select = history_df.copy()
    history_df_with_select.insert(0, "Select", False)
    
    edited_history_df = st.data_editor(
        history_df_with_select,
        width="stretch",
        hide_index=True,
        disabled=[
            "Display Index",
            "Run Type",
            "Run Date",
            "File Name",
            "Cost",
            "Dmax",
            "Cost Gap (%)",
            "Dmax Gap (%)",
            "Opened AP Count",
            "Opened AP List"
        ],
        column_config={
          "Select": st.column_config.CheckboxColumn(
             "Select",
             help="Select the solutions you want to display on the Pareto graph."
           )
        },
        key="pareto_history_selector"
    )
    selected_pareto_df = edited_history_df[edited_history_df["Select"] == True].copy()
    if not selected_pareto_df.empty:
        selected_pareto_df = selected_pareto_df.dropna(subset=["Cost", "Dmax"])
        st.subheader("Pareto Graph")
        fig = px.scatter(
           selected_pareto_df,
           x="Cost",
           y="Dmax",
           color="Run Type",
           symbol="Run Type",
           hover_data=[
                "Display Index",
                "Run Type",
                "Base Solution",
                "Opened AP Count",
                "Opened AP List"
            ],
            title="Pareto Graph: Cost vs Dmax"
        )
        fig.update_traces(marker=dict(size=12))
        fig.update_layout(
               xaxis_title="Total Cost",
               yaxis_title="Maximum Distance / Dmax"
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("Select at least one row from the history table to display the Pareto graph.")

    selected_display_index = st.selectbox(
        "Select the record you want to re-optimize.",
        history_df["Display Index"],
        disabled=st.session_state["reopt_running"]
    )

    selected_record = valid_history[int(selected_display_index) - 1]

    old_ap_count = selected_record.get("opened_ap_count")
    if old_ap_count is None:
       old_ap_count = selected_record.get("optimal_ap_count")

    if old_ap_count is None:
       st.warning("This record does not contain an AP count. Re-optimization cannot be performed with this record.")
       return

    st.info(f"Previous AP count of selected solution: {old_ap_count}")
    default_ap_count = int(old_ap_count)

    new_ap_count = st.number_input(
        "New AP Count",
        min_value=int(old_ap_count),
        value=default_ap_count,
        step=1,
        disabled=st.session_state["reopt_running"]
    )
    
    st.subheader("⚙️ Re-Optimization Gap Settings")

    reopt_cost_gap_input = st.number_input(
      "Re-Optimization Cost Gap (%)",
       min_value=0.0,
       value=0.0,
       step=0.5,
       format="%.1f",
       key="reopt_cost_gap_input",
       disabled=st.session_state["reopt_running"]
    )

    reopt_dmax_gap_input = st.number_input(
       "Re-Optimization Dmax Gap (%)",
       min_value=0.0,
       value=0.0,
       step=0.5,
       format="%.1f",
       key="reopt_dmax_gap_input",
       disabled=st.session_state["reopt_running"]
    )

    col_run, col_stop = st.columns(2)

    with col_run:
        if st.button(
            "Re-optimize Selected Solution",
            disabled=st.session_state["reopt_running"]
        ):
            start_reoptimization(selected_record, new_ap_count, selected_display_index)
            st.info("Re-optimization started...")
            st.rerun()

    with col_stop:
        if st.button(
            "Stop Re-optimization",
            disabled=not st.session_state["reopt_running"]
        ):
            stop_reoptimization()
            st.rerun()

    process = st.session_state.get("reopt_process")

    if process is not None:
       result = read_solver_result()

       # Eğer sonuç dosyası oluştuysa process'e bakmadan sonucu işle
       if result is not None:
         st.session_state["reopt_running"] = False
 
         if result.get("state") == "success":
            show_reoptimization_result(result)
            dashboard_record = {
              "run_id": result.get("run_id"),
              "date": result.get("date"),
              "run_type": "reoptimization",

              "total_cost": result.get("best_cost"),
              "dmax": result.get("dmax_val"),

              "ap_count": result.get("opened_ap_count", result.get("optimal_ap_count")),
              "opened_aps": result.get("opened_ap_list", []),

              "scenario_costs": result.get("scenario_costs", {}),
              "cost_breakdown_by_scenario": result.get("cost_breakdown_by_scenario", {}),

              "previous_cost": st.session_state["reopt_selected_record"].get("best_cost"),
              "new_cost": result.get("best_cost"),

              "previous_ap_count": st.session_state["reopt_selected_record"].get("opened_ap_count"),
              "new_ap_count": result.get("opened_ap_count", result.get("optimal_ap_count")),

              "cost_difference": (
                 result.get("best_cost", 0)
                 - st.session_state["reopt_selected_record"].get("best_cost", 0)
              )
            }

            save_dashboard_history(dashboard_record)

            save_reoptimization_to_history(
                old_record=st.session_state["reopt_selected_record"],
                result=result,
                new_ap_count=st.session_state["reopt_new_ap_count"]
            )

            st.success("New re-optimization result has been saved to history.")
            st.session_state["reopt_process"] = None

         else:
            st.error("Re-optimization failed or became infeasible.")
            st.json(result)
            st.session_state["reopt_process"] = None

       elif process.poll() is None:
         st.progress(60)
         time.sleep(2)
         st.rerun()

    else:
        st.session_state["reopt_running"] = False

def render_improve_solution():
    show_improve_solution_page()