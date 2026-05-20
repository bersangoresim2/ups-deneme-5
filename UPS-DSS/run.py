import pyomo.environ as pyo
from src.objective import build_cost_objective, build_dmax_objective
from src.data_loader import load_data
from src.model_builder import build_model


def print_nonzero_var(var_component, title, tol=1e-6):
    print(f"\n---- {title}")
    for idx in var_component:
        val = var_component[idx].value
        if val is not None and abs(val) > tol:
            print(f"{idx} = {val}")


def print_nonzero_param(param_component, title, tol=1e-6):
    print(f"\n---- {title}")
    for idx in param_component:
        val = pyo.value(param_component[idx])
        if val is not None and abs(val) > tol:
            print(f"{idx} = {val}")


def print_startloadss(model):
    print("\n---- PARAMETER startloadss")
    for k in model.K:
        for s in model.S:
            val = model.lambdatotalload[k, s, "o1"].value
            if val is not None:
                print(f"({k}, {s}) = {val}")


def print_routes(model):
    print("\n===== ROUTES =====")

    for k in model.K:
        for s in model.S:
            for o in model.O:
                arcs = []

                for i in model.I:
                    for j in model.I:
                        if (i, j, k, s, o) in model.x:
                            val = model.x[i, j, k, s, o].value
                            if val is not None and val > 0.5:
                                arcs.append((i, j))

                if arcs:
                    print(f"\nVehicle {k} | Scenario {s} | Order {o}")
                    for i, j in arcs:
                        print(f"{i} -> {j}")

#11.04.2026 eklendi -meryem                       
def solve_with_ap_option(data, user_ap_count):
    model = build_model(data, user_ap_count)

    solver = pyo.SolverFactory("highs")
    solver.options["mip_rel_gap"] = 0
    solver.options["mip_abs_gap"] = 0

    # 🔹 önce cost çöz
    build_cost_objective(model)
    solver.solve(model)

    print("\n--- SCENARIO COSTS ---", flush=True)

    for s in model.S:
        print(f"{s} -> {pyo.value(model.Cs[s])}", flush=True)

    print("\nTOTAL COST:", pyo.value(model.z), flush=True)

    optimal_ap_count = sum(round(pyo.value(model.y[i])) for i in model.I if i != "i0")

    optimal_cost = pyo.value(model.z)
    optimal_dmax = pyo.value(model.Dmax)

    # 🔴 KONTROL
    if user_ap_count < optimal_ap_count:
        return {
            "accepted": False,
            "message": f"Cannot enter an AP count less than: {optimal_ap_count}'",
            "optimal_ap_count": optimal_ap_count
        }

    # 🔹 eşitse tekrar çözme
    if user_ap_count == optimal_ap_count:
        return {
            "accepted": True,
            "message": "Optimal solution was used.",
            "optimal_ap_count": optimal_ap_count,
            "user_ap_count": user_ap_count,
            "user_cost": optimal_cost,
            "user_dmax": optimal_dmax
        }

    # 🔹 büyükse constraint ekle
    model.ap_constraint = pyo.Constraint(
    expr=sum(model.a[i] for i in model.I if i != "i0") == user_ap_count
)

    solver.solve(model)

    return {
        "accepted": True,
        "message": "Model was re-solved.",
        "optimal_ap_count": optimal_ap_count,
        "user_ap_count": user_ap_count,
        "user_cost": pyo.value(model.z),
        "user_dmax": pyo.value(model.Dmax)
    }
#

def main():

    print(">>> DATA LOADING")
    data = load_data()

    w = int(input("Enter the candidate AP count: "))
    model = build_model(data, w)

    print("\n>>> BUILDING MODEL")
    
    print("\n>>> MODEL BUILT SUCCESSFULLY")

    solver = pyo.SolverFactory("highs")

    # GAMS'e en yakın HiGHS ayarları
    #solver.options["time_limit"] = 8000
    solver.options["mip_rel_gap"] = 0
    solver.options["mip_abs_gap"] = 0

    print("\n>>> SOLVING MODEL - MIN COST")
    build_cost_objective(model)
    result = solver.solve(model, tee=True)


    print("\n===== MIN COST SOLUTION =====")
    print("Cost (z):", pyo.value(model.z))
    print("Dmax:", pyo.value(model.Dmax))

    print("\n--- SCENARIO COSTS ---")
    for s in model.S:
        print(f"{s}: {pyo.value(model.Cs[s])}")
    
    print("\n--- CHECK AVG ---")
    values = [pyo.value(model.Cs[s]) for s in model.S]
    print("Average (manual):", sum(values)/len(values))
    
    #11.04.2026 eklendi - meryem
    optimal_ap_count = sum(
    round(pyo.value(model.a[i])) 
    for i in model.I if i != "i0"
)
    print("\nOptimal AP Count:", optimal_ap_count)
    #

    print("\n>>> SOLVING MODEL - MIN DMAX")

    # 🔴 EKLE: AP sayısını sabitle
    model.ap_constraint = pyo.Constraint(
    expr=sum(model.a[i] for i in model.I if i != "i0") == optimal_ap_count
)

    model.obj_cost.deactivate()
    build_dmax_objective(model)

    result = solver.solve(model, tee=True)
    print("\n===== MIN DMAX SOLUTION =====")
    print("Dmax:", pyo.value(model.Dmax))
    print("Cost (z):", pyo.value(model.z))

    print("\n===== SOLVER STATUS =====")
    print("Status:", result.solver.status)
    print("Termination:", result.solver.termination_condition)

    print("\n---- VARIABLE z.L")
    print("z =", model.z.value)

    print_nonzero_var(model.a, "VARIABLE a.L")
    print_nonzero_var(model.y, "VARIABLE y.L")
    print_nonzero_var(model.t, "VARIABLE t.L")
    print_nonzero_var(model.l, "VARIABLE l.L")
    print_nonzero_var(model.pi, "VARIABLE pi.L")
    print_nonzero_var(model.b, "VARIABLE b.L")
    print_nonzero_var(model.lambdatotalload, "VARIABLE lambdatotalload.L")

    print_startloadss(model)

    print("\n---- VARIABLE cust_distance_to_access.L")
    for i in model.I:
        if i != "i0" and int(i[1:]) >= w + 1:
            val = model.cust_distance_to_access[i].value
            if val is not None and abs(val) > 1e-6:
                print(f"{i} = {val}")

    print_nonzero_param(model.mi, "PARAMETER mi")

    print("\n---- VARIABLE mi_ap.L")
    for i in model.I:
        if i != "i0" and int(i[1:]) < w + 1:
            for s in model.S:
                val = model.mi_ap[i, s].value
                if val is not None and abs(val) > 1e-6:
                    print(f"({i}, {s}) = {val}")

    print_routes(model)


if __name__ == "__main__":
    main()