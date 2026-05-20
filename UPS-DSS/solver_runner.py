import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

import pyomo.environ as pyo

from src.objective import build_cost_objective, build_dmax_objective
from src.data_loader import load_data
from src.model_builder import build_model

#11.04.2026-meryem


def solve_model(data, candidate_ap_count=10, user_ap_count=None, optimal_ap_count=None,cost_gap=0.0,dmax_gap=0.0):

    if user_ap_count is not None:
        user_ap_count = int(user_ap_count)

    if optimal_ap_count is not None:
        optimal_ap_count = int(optimal_ap_count)

    if user_ap_count is not None and optimal_ap_count is not None:
        if user_ap_count < optimal_ap_count:
            return {
                "state": "error",
                "message": f"The entered AP count ({user_ap_count}) cannot be less than the optimal value ({optimal_ap_count}).",
                "optimal_ap_count": optimal_ap_count,
                "user_ap_count": user_ap_count
            }

    print(">>> MODEL BUILDING")
    model = build_model(data, candidate_ap_count)
    print("CANDIDATE AP COUNT =", candidate_ap_count, flush=True)
    print("USER AP COUNT =", user_ap_count, flush=True)
    print("OPTIMAL AP COUNT =", optimal_ap_count, flush=True)
    print("A VARIABLES =", list(model.a), flush=True)
    if user_ap_count is not None:
       model.ap_constraint = pyo.Constraint(
         expr=sum(
              model.a[i]
              for i in model.I
              if i != "i0" and int(i[1:]) <= candidate_ap_count
         ) == user_ap_count
       )

    print(">>> SOLVER CREATED")
    solver = pyo.SolverFactory("highs")
    solver.options["mip_rel_gap"] = cost_gap
    solver.options["mip_abs_gap"] = 0

    print("USING COST GAP:", cost_gap, flush=True)
    print(">>> COST OBJECTIVE BUILDING")
    build_cost_objective(model)

    print(">>> COST SOLVE STARTED")
    result_cost = solver.solve(model, tee=True, load_solutions=False)

    cost_termination = str(result_cost.solver.termination_condition).lower()

    if cost_termination not in ["optimal", "feasible"]:
        return {
            "state": "error",
            "message": "Cost optimization could not find a feasible solution.",
            "solver_status": str(result_cost.solver.status),
            "termination": str(result_cost.solver.termination_condition),
            "best_cost": None,
            "dmax_val": None,
            "optimal_ap_count": optimal_ap_count,
            "user_ap_count": user_ap_count
        }

    model.solutions.load_from(result_cost)

    print(">>> COST SOLVE FINISHED")
    best_cost = pyo.value(model.z)
    print(">>> BEST COST:", best_cost)

    print(">>> DMAX OBJECTIVE BUILDING")

    # 🚀 YENİ: Arayüzden gelen % Gap değerine göre maliyeti (best_cost'u) esnetiyoruz.
    
    model.cost_cap = pyo.Constraint(expr=model.z <= best_cost + 1e-6)

    model.obj_cost.deactivate()
    build_dmax_objective(model)
    solver.options["mip_rel_gap"] = dmax_gap
    solver.options["mip_abs_gap"] = 0

    print("USING DMAX GAP:", dmax_gap, flush=True)

    print(">>> DMAX SOLVE STARTED")
    result_dmax = solver.solve(model, tee=True, load_solutions=False)

    dmax_termination = str(result_dmax.solver.termination_condition).lower()

    if dmax_termination not in ["optimal", "feasible"]:
        return {
            "state": "error",
            "message": "Dmax optimization could not find a feasible solution.",
            "solver_status": str(result_dmax.solver.status),
            "termination": str(result_dmax.solver.termination_condition),
            "best_cost": float(best_cost) if best_cost is not None else None,
            "dmax_val": None,
            "optimal_ap_count": optimal_ap_count,
            "user_ap_count": user_ap_count
        }

    model.solutions.load_from(result_dmax)

    print(">>> DMAX SOLVE FINISHED")
    
    opened_ap_list = []

    if hasattr(model, "a"):
      for i in model.a:
        val = pyo.value(model.a[i])
        if val is not None and val > 0.5:
            opened_ap_list.append(str(i))

    opened_ap_count = len(opened_ap_list)

    scenario_costs = {
      str(s): float(pyo.value(model.Cs[s]))
      for s in model.S
    }
    
    cost_breakdown_by_scenario = {}

    for s in model.S:
      ap_fixed_cost = sum(
         pyo.value(model.af[i]) * pyo.value(model.a[i])
         for i in model.I
         if i != "i0"
      )

      routing_cost = sum(
        pyo.value(model.c[i, j]) * pyo.value(model.x[i, j, k, s, o])
        for i in model.I
        for j in model.I
        for k in model.K
        for o in model.O
        if i != j
      )

      vehicle_fixed_cost = sum(
        pyo.value(model.tf[k]) * pyo.value(model.t[k, s])
        for k in model.K
      )

      variable_load_cost = sum(
        pyo.value(model.v[i]) * pyo.value(model.l[i, s])
        for i in model.I
        if i != "i0"
      )

      cost_breakdown_by_scenario[str(s)] = {
        "ap_fixed_cost": round(ap_fixed_cost, 2),
        "routing_cost": round(routing_cost, 2),
        "vehicle_fixed_cost": round(vehicle_fixed_cost, 2),
        "variable_load_cost": round(variable_load_cost, 2),
        "total_cost": round(
            ap_fixed_cost + routing_cost + vehicle_fixed_cost + variable_load_cost,
            2
        )
      }
    
    customer_demand_summary = []

    for j in model.I:
      try:
        node_num = int(str(j)[1:])
        is_customer = node_num >= candidate_ap_count + 1
      except:
        is_customer = False

      if not is_customer:
        continue

      total_delivery = sum(
        pyo.value(model.d[j, s])
        for s in model.S
        if (j, s) in model.d
      )

      total_pickup = sum(
        pyo.value(model.p[j, s])
        for s in model.S
        if (j, s) in model.p
      )
 
      total_demand = total_delivery + total_pickup

      customer_demand_summary.append({
        "customer": str(j),
        "total_delivery": round(total_delivery, 2),
        "total_pickup": round(total_pickup, 2),
        "total_demand": round(total_demand, 2)
      })

    customer_assignments = []

    for i in model.I:
        for j in model.I:
            if (i, j) in model.y:
               y_val = pyo.value(model.y[i, j])

               if y_val is not None and y_val > 0.5:
                  customer_assignments.append({
                     "access_point": str(i),
                     "customer": str(j)
                  })
    
    used_route_arcs = []

    for i in model.I:
        for j in model.I:
            for k in model.K:
                for s in model.S:
                    for o in model.O:
                        if (i, j, k, s, o) in model.x:
                            x_val = pyo.value(model.x[i, j, k, s, o])

                            if x_val is not None and x_val > 0.5:
                               used_route_arcs.append({
                                  "from": str(i),
                                  "to": str(j),
                                  "vehicle": str(k),
                                  "scenario": str(s),
                                  "order": str(o)
                                })
    run_type = "reoptimization" if user_ap_count is not None else "strategic_optimization"

    return {
     "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
     "date": datetime.now().strftime("%Y-%m-%d"),
     "run_type": run_type,

     "best_cost": float(pyo.value(model.z)) if pyo.value(model.z) is not None else None,
     "dmax_val": float(pyo.value(model.Dmax)) if pyo.value(model.Dmax) is not None else None,

     "solver_status": str(result_dmax.solver.status),
     "termination": str(result_dmax.solver.termination_condition),

     "opened_ap_count": opened_ap_count,
     "ap_count": opened_ap_count,

     "opened_ap_list": opened_ap_list,
     "opened_aps": opened_ap_list,
 
     "user_ap_count": user_ap_count,
     "candidate_ap_count": candidate_ap_count,

     "scenario_costs": scenario_costs,
     "cost_breakdown_by_scenario": cost_breakdown_by_scenario,
     "customer_demand_summary": customer_demand_summary,
     "customer_assignments": customer_assignments,
     "used_route_arcs": used_route_arcs
    }

def main():
    input_json = Path(sys.argv[1])

    with open(input_json, "r", encoding="utf-8") as f:
        config = json.load(f)

    excel_path = config["excel_path"]
    user_ap_count = config.get("user_ap_count")
    result_path = Path(config["result_path"])
    candidate_ap_count = config.get("candidate_ap_count", 10)

    try:
        print(">>> EXCEL PATH:", excel_path, flush=True)
        print(">>> FILE EXISTS:", Path(excel_path).exists(), flush=True)
        print(">>> DATA LOADING STARTED", flush=True)
        data = load_data(excel_path)
        print(">>> DATA LOADING FINISHED", flush=True)

        optimal_ap_count = config.get("optimal_ap_count")

        # 🚀 YENİ: JSON'dan gelen Gap değerini yakalıyoruz
        cost_gap = config.get("cost_gap", 0.0)
        dmax_gap = config.get("dmax_gap", 0.0)

        print("COST GAP FROM CONFIG:", cost_gap, flush=True)
        print("DMAX GAP FROM CONFIG:", dmax_gap, flush=True)

        print(">>> SOLVE MODEL FUNCTION STARTED")
        result = solve_model(data, candidate_ap_count, user_ap_count, optimal_ap_count, cost_gap, dmax_gap)
        print(">>> SOLVE MODEL FUNCTION FINISHED")

        # 🔥 ekstra güvenlik
        if result is None:
            output = {
                "state": "error",
                "message": "The model did not return any results."
            }

        elif result.get("state") == "error":
            output = result

        else:
            output = {
                "state": "success",
                **result
            }

    except Exception as e:
        output = {
            "state": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }

    # 🔥 JSON her durumda yazılsın
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()