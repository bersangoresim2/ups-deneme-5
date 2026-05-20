import streamlit as st
import pyomo.environ as pyo
import pandas as pd
import time
import subprocess
import sys
import json
import matplotlib.pyplot as plt
from pathlib import Path
import os
import json
from datetime import datetime
from pathlib import Path
import base64
import altair as alt

DASHBOARD_HISTORY_PATH = Path("dashboard_history.json")


def save_dashboard_history(result):
    if DASHBOARD_HISTORY_PATH.exists():
        with open(DASHBOARD_HISTORY_PATH, "r", encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = []

    dashboard_record = {
        "run_id": result.get("run_id"),
        "date": result.get("date"),
        "run_type": result.get("run_type"),

        "total_cost": result.get("best_cost"),
        "dmax": result.get("dmax_val"),

        "ap_count": result.get("ap_count"),
        "opened_aps": result.get("opened_aps"),

        "used_vehicle_count": result.get("used_vehicle_count"),

        "optimal_ap_count": result.get("optimal_ap_count"),
        "user_ap_count": result.get("user_ap_count"),

        "solver_status": result.get("solver_status"),
        "termination": result.get("termination"),
        "scenario_costs": result.get("scenario_costs"),
        "cost_breakdown_by_scenario": result.get("cost_breakdown_by_scenario"),
        "customer_demand_summary": result.get("customer_demand_summary"),
        "customer_assignments": result.get("customer_assignments"),
        "used_route_arcs": result.get("used_route_arcs")
    }

    history.append(dashboard_record)

    with open(DASHBOARD_HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

#aşağıya history file bloğunu ekledi. -asu
BASE_DIR = Path(__file__).resolve().parent
HISTORY_FILE = BASE_DIR / "optimization_history.json"
COST_HISTORY_FILE = BASE_DIR / "cost_history.json"

def load_cost_history():
    if COST_HISTORY_FILE.exists():
        try:
            with open(COST_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_cost_history(history):
    with open(COST_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=4)


def add_to_cost_history(file_name, total_cost, scenario_costs):
    history = load_cost_history()

    new_record = {
        "run_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "file_name": file_name,
        "total_cost": total_cost,
        "scenario_costs": scenario_costs
    }

    history.append(new_record)
    save_cost_history(history)

def load_history():
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=4)


def add_to_history(uploaded_file, file_name, min_cost, max_distance, opened_ap_count, opened_ap_list, candidate_ap_count):
    history = load_history()

    uploaded_file.seek(0)
    file_bytes = uploaded_file.read()
    file_base64 = base64.b64encode(file_bytes).decode("utf-8")

    new_record = {
        "run_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "file_name": file_name,
        "file_data_base64": file_base64,
        "best_cost": min_cost,
        "dmax_val": max_distance,
        "opened_ap_count": opened_ap_count,
        "opened_ap_list": opened_ap_list,
        "candidate_ap_count": candidate_ap_count,
        "cost_gap": st.session_state.get("cost_gap_input", 0.0),
        "dmax_gap": st.session_state.get("dmax_gap_input", 0.0),
        "is_reoptimization": False
    }

    history.append(new_record)
    save_history(history)

PROCESS_KEY = "solver_process"

DATA_LABELS = {
    "S": "Demand Scenario Set",
    "K": "Vehicle Set",
    "I": "All Stops Set (Depot, Access Point, Customer)",
    "O": "Visit Order Set",
    "d": "Delivery Demand Parameter",
    "dh": "Hand-to-Hand Delivery Demand Parameter",
    "p": "Pickup Demand Parameter",
    "ph": "Hand-to-Hand Pickup Demand Parameter",
    "c": "Travel Cost Between Locations",
    "q": "Vehicle Capacitiy Parameter",
    "tf": "Vehicle Fixed Cost Parameter",
    "af": "Access Point Fixed Cost Parameter",
    "v": "Variable Load Cost Parameter",
    "apc": "Access Point Capacities Parameter"
}


def format_sheet_name(sheet_name):
    return DATA_LABELS.get(sheet_name, sheet_name)


from src.objective import build_cost_objective, build_dmax_objective
from src.data_loader import load_data
from src.model_builder import build_model
from src.fast_routing_model import solve_fast_model


def get_nonzero_var_rows(var_component, tol=1e-6):
    rows = []
    for idx in var_component:
        val = var_component[idx].value
        if val is not None and abs(val) > tol:
            rows.append({"Index": str(idx), "Value": val})
    return pd.DataFrame(rows)


def get_nonzero_param_rows(param_component, tol=1e-6):
    rows = []
    for idx in param_component:
        val = pyo.value(param_component[idx])
        if val is not None and abs(val) > tol:
            rows.append({"Index": str(idx), "Value": val})
    return pd.DataFrame(rows)


def get_startloadss_rows(model):
    rows = []
    for k in model.K:
        for s in model.S:
            val = model.lambdatotalload[k, s, "o1"].value
            if val is not None:
                rows.append({"k": k, "s": s, "Value": val})
    return pd.DataFrame(rows)


def get_routes_rows(model):
    rows = []
    for k in model.K:
        for s in model.S:
            for o in model.O:
                for i in model.I:
                    for j in model.I:
                        if (i, j, k, s, o) in model.x:
                            val = model.x[i, j, k, s, o].value
                            if val is not None and val > 0.5:
                                rows.append({
                                    "Vehicle": k,
                                    "Scenario": s,
                                    "Order": o,
                                    "From": i,
                                    "To": j,
                                    "Value": val
                                })
    return pd.DataFrame(rows)


def get_cust_distance_rows(model, tol=1e-6):
    rows = []
    for i in model.I:
        w = st.session_state.get("user_ap_count", 0)

        if i != "i0" and int(i[1:]) >= w + 1:
            val = model.cust_distance_to_access[i].value
            if val is not None and abs(val) > tol:
                rows.append({"Customer": i, "Value": val})
    return pd.DataFrame(rows)


def get_mi_ap_rows(model, tol=1e-6):
    rows = []
    for i in model.I:
        w = st.session_state.get("user_ap_count", 0)
        if i != "i0" and int(i[1:]) < w + 1:
            for s in model.S:
                val = model.mi_ap[i, s].value
                if val is not None and abs(val) > tol:
                    rows.append({"i": i, "s": s, "Value": val})
    return pd.DataFrame(rows)


def solve_model(data):
    model = build_model(data, st.session_state.get("user_ap_count", 1))

    solver = pyo.SolverFactory("highs")
    solver.options["mip_rel_gap"] = 0
    solver.options["mip_abs_gap"] = 0

    build_cost_objective(model)
    result_cost = solver.solve(model, tee=True)

    best_cost = pyo.value(model.z)
    cost_dmax = pyo.value(model.Dmax)

    model.cost_cap = pyo.Constraint(expr=model.z <= best_cost + 1e-6)
    model.obj_cost.deactivate()
    build_dmax_objective(model)
    result_dmax = solver.solve(model, tee=True)

    dmax_val = pyo.value(model.Dmax)
    z_val_after_dmax = pyo.value(model.z)

    result_bundle = {
        "model": model,
        "best_cost": best_cost,
        "cost_dmax": cost_dmax,
        "dmax_val": dmax_val,
        "z_val_after_dmax": z_val_after_dmax,
        "solver_status": str(result_dmax.solver.status),
        "termination": str(result_dmax.solver.termination_condition),
        "routes": get_routes_rows(model),
    }

    return result_bundle


def start_solver(uploaded_file):
    base_dir = Path(__file__).resolve().parent

    temp_excel = base_dir / "temp.xlsx"
    input_json = base_dir / "solver_input.json"
    result_json = base_dir / "solver_result.json"
    runner = base_dir / "solver_runner.py"
    if result_json.exists():
        result_json.unlink()

    uploaded_file.seek(0)
    with open(temp_excel, "wb") as f:
        f.write(uploaded_file.read())

    # 🚀 YENİ: Arayüzden alınan % Gap değerini JSON'a gönderiyoruz (Örn: 30.0 -> 0.30)
    cost_gap = st.session_state.get("cost_gap_input", 0.0) / 100.0
    dmax_gap = st.session_state.get("dmax_gap_input", 0.0) / 100.0
    
    config = {
        "excel_path": str(temp_excel),
        "result_path": str(result_json),
        "candidate_ap_count": st.session_state.get("candidate_ap_count", 10),
        "user_ap_count": None,
        "optimal_ap_count": None,
        "is_reoptimization": False,
        "cost_gap": cost_gap,
        "dmax_gap": dmax_gap
    }
    with open(input_json, "w") as f:
        json.dump(config, f)
    
    process = subprocess.Popen(
        [sys.executable, str(runner), str(input_json)]
    )
    
    st.session_state["solver_process"] = process
    st.session_state["solver_running"] = True

def stop_solver():
    base_dir = Path(__file__).resolve().parent
    result_json = base_dir / "solver_result.json"

    process = st.session_state.get("solver_process")

    if process and process.poll() is None:
        process.terminate()

    if result_json.exists():
        result_json.unlink()

    st.session_state["solver_running"] = False
    st.session_state["solver_process"] = None
    st.session_state["solver_stopped_by_user"] = True
    st.session_state["solution"] = None

def read_solver_result():
    base_dir = Path(__file__).resolve().parent
    result_json_path = base_dir / "solver_result.json"

    if result_json_path.exists():
        with open(result_json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    return None


def render_optimization_panel():
    #bu alttaki kısımlar eklendi. -asu
    if "history_saved" not in st.session_state:
        st.session_state["history_saved"] = False
    if "cost_history_saved" not in st.session_state:
        st.session_state["cost_history_saved"] = False
    if "dashboard_history_saved" not in st.session_state:
        st.session_state["dashboard_history_saved"] = False
    if "solver_stopped_by_user" not in st.session_state:
        st.session_state["solver_stopped_by_user"] = False

    if "solution" not in st.session_state:
        st.session_state["solution"] = None

    if "solver_running" not in st.session_state:
        st.session_state["solver_running"] = False

    if "solver_process" not in st.session_state:
        st.session_state["solver_process"] = None

    st.subheader("Optimization Panel")
    st.write("Upload an Excel file, preview its contents, and run the optimization model.")

    uploaded_file = st.file_uploader(
        "Upload Excel File",
        type=["xlsx"],
        key="manager_uploaded_file"
    )

    if uploaded_file is None:
        st.info("Please upload an Excel file to continue.")
    else:

        st.success(f"Uploaded file: {uploaded_file.name}")

        st.markdown("### Data Preview")

        uploaded_file.seek(0)
        xls = pd.ExcelFile(uploaded_file, engine="openpyxl")
        sheet_names = xls.sheet_names

        selected_sheet = st.selectbox(
            "Select data",
            sheet_names,
            format_func=format_sheet_name
        )

        uploaded_file.seek(0)
        preview_df = pd.read_excel(uploaded_file, sheet_name=selected_sheet)

        st.write(f"Showing: {format_sheet_name(selected_sheet)}")
        st.dataframe(preview_df)

        #11.04.2026 eklendi- meryem
        st.subheader("🎯 Candidate AP Count")


        candidate_ap = st.number_input(
            "Max allowable APs:",
            min_value=1,
            value=10,
            step=1
        )
        st.session_state["candidate_ap_count"] = candidate_ap
        st.write("Candidate AP sent to model:", st.session_state["candidate_ap_count"])

        # 🚀 YENİ: Gap (Esneklik) Ayarı Buraya Eklendi
        st.subheader("⚙️ Optimization Gap Settings")
        cost_gap_input = st.number_input(
            "Cost Minimization Gap (%)",
            min_value=0.0,
            value=0.0,
            step=0.5,
            format="%.1f",
            key="cost_gap_input",
            help="Defines the acceptable optimality gap for the cost minimization phase."
        )

        dmax_gap_input = st.number_input(
            "Maximum Distance Minimization Gap (%)",
            min_value=0.0,
            value=0.0,
            format="%.1f",
            key="dmax_gap_input",
            help="Defines the acceptable optimality gap for the service quality optimization phase."
        )
        cost_gap = st.session_state.get("cost_gap_input", 0.0) / 100.0
        dmax_gap = st.session_state.get("dmax_gap_input", 0.0) / 100.0

        # -----------------------------
        # Full optimization
        # -----------------------------
        process = st.session_state.get(PROCESS_KEY)
        is_solver_active = process is not None and process.poll() is None
        st.session_state["solver_running"] = is_solver_active

        col1, col2 = st.columns(2)

        with col1:
            run_clicked = st.button(
                "Run Optimization",
                key="full_run_optimization_button",
                disabled=is_solver_active
            )

        with col2:
            stop_clicked = st.button(
                "Stop Solver",
                key="stop_solver_button",
                disabled=not is_solver_active
            )

        if run_clicked:
            try:
                st.session_state["history_saved"] = False
                st.session_state["cost_history_saved"] = False
                st.session_state["dashboard_history_saved"] = False
                st.session_state["solver_stopped_by_user"] = False
                st.session_state["solution"] = None
                start_solver(uploaded_file)
                st.rerun()
            except Exception as e:
                st.error(f"Could not start solver: {e}")

        if stop_clicked:
            #st.session_state["solver_stopped_by_user"] = True
            #st.session_state["solution"] = None
            stop_solver()
            st.warning("Solver stopped by user.")
            st.stop()

        process = st.session_state.get(PROCESS_KEY)

        if process is not None and not st.session_state.get("solver_stopped_by_user", False):
            if process.poll() is None:
                st.progress(60)
                st.info("Solving optimization model... please wait.")
                time.sleep(1)
                st.rerun()

            else:
                st.session_state["solver_running"] = False
                result = read_solver_result()

                if result is None:
                    if st.session_state["solver_stopped_by_user"]:
                        st.warning("Optimization was stopped by the user. This run was not saved to history.")
                    else:
                        st.error("Solver finished but no result file was found.")

                elif st.session_state["solver_stopped_by_user"]:
                    st.warning("Optimization was stopped by the user. Results are not displayed.")
                    st.session_state["solution"] = None

                elif result.get("state") == "success":
                    data_dir = Path(__file__).resolve().parent / "data"
                    data_dir.mkdir(exist_ok=True)
                    save_path = data_dir / uploaded_file.name
                    with open(save_path, "wb") as f:
                        uploaded_file.seek(0)
                        f.write(uploaded_file.read())
                    st.session_state["solution"] = result
                    if not st.session_state.get("dashboard_history_saved", False):
                       save_dashboard_history(result)
                       st.session_state["dashboard_history_saved"] = True
                    optimal_ap = result.get("optimal_ap_count")

                    if optimal_ap is not None:
                        st.session_state["optimal_ap_count"] = optimal_ap

                    st.progress(100)
                    st.success("✅ OPTIMIZATION IS DONE")
                    st.info("You can now review the optimization results below.")
                
                    col1, col2 = st.columns(2)
                    col1.metric("Cost", result.get("best_cost"))
                
                    # 🔹 Scenario costları al
                    scenario_costs = result.get("scenario_costs", {})

                    if scenario_costs:
                        st.markdown("### 📊 Scenario-based Costs")

                        scenario_df = pd.DataFrame(
                         list(scenario_costs.items()),
                         columns=["Scenario", "Cost"]
                    )

                    st.dataframe(scenario_df, width="stretch")
                    if not st.session_state["cost_history_saved"]:
                        add_to_cost_history(
                          file_name=uploaded_file.name,
                          total_cost=result.get("best_cost"),
                          scenario_costs=scenario_costs
                        )
                        st.session_state["cost_history_saved"] = True

                    if (
                        not st.session_state["history_saved"]
                        and not st.session_state["solver_stopped_by_user"]
                    ):
                        add_to_history(
                            uploaded_file=uploaded_file,
                            file_name=uploaded_file.name,
                            min_cost=result.get("best_cost"),
                            max_distance=result.get("dmax_val"),
                            opened_ap_count=result.get("optimal_ap_count"),
                            opened_ap_list=result.get("opened_ap_list", []),
                            candidate_ap_count=st.session_state.get("candidate_ap_count", 10)
                        )
                        st.session_state["history_saved"] = True

                    st.metric("Optimal AP Count", result.get("optimal_ap_count"))
                    opened_ap_list = result.get("opened_ap_list")

                    if opened_ap_list:
                        st.write("Opened APs:", opened_ap_list)
                    else:
                        st.warning("No opened AP list found.")
                    st.write(f"Status: {result.get('solver_status')}")
                    st.write(f"Termination: {result.get('termination')}")

                else:
                    st.error("Optimization failed.")
                    st.code(result.get("error", "Unknown error"))
                    if result.get("traceback"):
                        with st.expander("Show traceback"):
                            st.code(result["traceback"])

                st.session_state[PROCESS_KEY] = None

        st.markdown("---")

    # -----------------------------
    # COST HISTORY GRAPH
    # -----------------------------
    st.markdown("---")
    st.subheader("Cost History")

    cost_history = load_cost_history()

    if len(cost_history) == 0:
      st.info("No cost history available yet.")
    else:
      cost_rows = []

      for run_no, item in enumerate(cost_history, start=1):
        cost_rows.append({
            "Run": run_no,
            "File": item.get("file_name"),
            "Scenario": "Total",
            "Cost": item.get("total_cost")
        })

        for scenario, cost in item.get("scenario_costs", {}).items():
            cost_rows.append({
                "Run": run_no,
                "File": item.get("file_name"),
                "Scenario": scenario,
                "Cost": cost
            })

      cost_df = pd.DataFrame(cost_rows)

      st.dataframe(cost_df, width="stretch")

      scenario_only_df = cost_df[cost_df["Scenario"] != "Total"]

      scenario_only_df["Run_Scenario"] = (
         "Run "
         + scenario_only_df["Run"].astype(str)
         + " - "
         + scenario_only_df["Scenario"].astype(str)
      )

      chart = alt.Chart(scenario_only_df).mark_circle(size=120).encode(
        x=alt.X("Run_Scenario:N", title="Run - Scenario"),
        y=alt.Y("Cost:Q", title="Cost"),
        tooltip=[
          alt.Tooltip("Run:N", title="Run"),
          alt.Tooltip("File:N", title="File"),
          alt.Tooltip("Scenario:N", title="Scenario"),
          alt.Tooltip("Cost:Q", title="Cost")
        ]
      ).properties(
        height=350
      )

      st.altair_chart(chart, width="stretch")

    # -----------------------------
    # Download results
    # -----------------------------
    solution = st.session_state.get("solution")

    if solution is not None and "routes" in solution:
        st.markdown("---")
        st.subheader("Download Results")

        routes_df = solution["routes"]

        if routes_df is not None and not routes_df.empty:
            csv = routes_df.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="Download Routes as CSV",
                data=csv,
                file_name="routes.csv",
                mime="text/csv"
            )

    st.markdown("---")
