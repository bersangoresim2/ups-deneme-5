import pyomo.environ as pyo


def build_fast_model(data):
    model = pyo.ConcreteModel()

    depot = "i0"

    active_points = [str(i) for i in data["active_points"]]
    customers = [str(i) for i in data["customers"]]
    nodes = [depot] + active_points + customers

    vehicles = data["K"]["Vehicle"].astype(str).tolist()

    model.nodes = pyo.Set(initialize=nodes)
    model.active_points = pyo.Set(initialize=active_points)
    model.customers = pyo.Set(initialize=customers)
    model.K = pyo.Set(initialize=vehicles)

    c_dict = {
        (str(row["i"]), str(row["j"])): float(row["distance"])
        for _, row in data["c"].iterrows()
    }

    model.c = pyo.Param(
        model.nodes,
        model.nodes,
        initialize=c_dict,
        default=999999
    )

    q_dict = {
        str(row["vehicle"]): float(row["capacity"])
        for _, row in data["q"].iterrows()
    }

    model.q = pyo.Param(
        model.K,
        initialize=q_dict,
        default=0
    )

    first_scenario = data["S"]["Scenario"].iloc[0]

    d_dict = {
        str(row["customer"]): float(row["demand"])
        for _, row in data["d"].iterrows()
        if row["scenario"] == first_scenario
    }

    model.d = pyo.Param(
        model.customers,
        initialize=d_dict,
        default=0
    )

    total_demand = sum(d_dict.get(j, 0) for j in customers)
    max_capacity = max(q_dict.values()) if q_dict else 1
    model.M = pyo.Param(initialize=max(total_demand, max_capacity, 1))

    model.x = pyo.Var(model.nodes, model.nodes, model.K, domain=pyo.Binary)
    model.y = pyo.Var(model.active_points, model.customers, domain=pyo.Binary)
    model.ap_has_customer = pyo.Var(model.active_points, domain=pyo.Binary)
    model.u = pyo.Var(model.nodes, model.K, domain=pyo.NonNegativeReals)
    model.use_vehicle = pyo.Var(model.K, domain=pyo.Binary)

    def obj_rule(model):
        routing_cost = sum(
            model.c[i, j] * model.x[i, j, k]
            for i in model.nodes
            for j in model.nodes
            for k in model.K
            if i != j
        )

        assignment_cost = sum(
            model.c[p, j] * model.y[p, j]
            for p in model.active_points
            for j in model.customers
        )

        return routing_cost

    model.obj = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

    def no_self_loop_rule(model, i, k):
        return model.x[i, i, k] == 0

    model.no_self_loop = pyo.Constraint(model.nodes, model.K, rule=no_self_loop_rule)

    def assign_customer_rule(model, j):
        return sum(model.y[p, j] for p in model.active_points) == 1

    model.assign_customer = pyo.Constraint(model.customers, rule=assign_customer_rule)

    nearest_ap = {}

    for j in customers:
        best_p = None
        best_dist = float("inf")

        for p in active_points:
            dist = c_dict.get((p, j), 999999)

            if dist < best_dist:
                best_dist = dist
                best_p = p

        nearest_ap[j] = best_p


    def force_nearest_ap_assignment_rule(model, p, j):
        if nearest_ap[j] == p:
            return model.y[p, j] == 1
        else:
            return model.y[p, j] == 0

    model.force_nearest_ap_assignment = pyo.Constraint(
        model.active_points,
        model.customers,
        rule=force_nearest_ap_assignment_rule
    )

    def ap_has_customer_upper_rule(model, p):
      return sum(model.y[p, j] for j in model.customers) <= len(model.customers) * model.ap_has_customer[p]

    model.ap_has_customer_upper = pyo.Constraint(
      model.active_points,
      rule=ap_has_customer_upper_rule
    )


    def ap_has_customer_lower_rule(model, p, j):
       return model.ap_has_customer[p] >= model.y[p, j]

    model.ap_has_customer_lower = pyo.Constraint(
      model.active_points,
      model.customers,
      rule=ap_has_customer_lower_rule
    )


    def visit_assigned_active_point_rule(model, p):
      return sum(
        model.x[i, p, k]
        for i in model.nodes
        for k in model.K
        if i != p
      ) >= model.ap_has_customer[p]

    model.visit_assigned_active_point = pyo.Constraint(
      model.active_points,
      rule=visit_assigned_active_point_rule
    )


    def leave_assigned_active_point_rule(model, p):
      return sum(
        model.x[p, j, k]
        for j in model.nodes
        for k in model.K
        if j != p
      ) >= model.ap_has_customer[p]

    model.leave_assigned_active_point = pyo.Constraint(
      model.active_points,
      rule=leave_assigned_active_point_rule
    )


    def visit_customer_once_rule(model, j):
        return sum(
            model.x[i, j, k]
            for i in model.nodes
            for k in model.K
            if i != j
        ) == 1

    model.visit_customer_once = pyo.Constraint(model.customers, rule=visit_customer_once_rule)

    def leave_customer_once_rule(model, j):
        return sum(
            model.x[j, i, k]
            for i in model.nodes
            for k in model.K
            if i != j
        ) == 1

    model.leave_customer_once = pyo.Constraint(model.customers, rule=leave_customer_once_rule)

    def flow_rule(model, h, k):
        return sum(
            model.x[i, h, k]
            for i in model.nodes
            if i != h
        ) == sum(
            model.x[h, j, k]
            for j in model.nodes
            if j != h
        )

    model.flow = pyo.Constraint(model.nodes, model.K, rule=flow_rule)

    def depot_depart_rule(model, k):
        return sum(
            model.x[depot, j, k]
            for j in model.nodes
            if j != depot
        ) == model.use_vehicle[k]

    model.depot_depart = pyo.Constraint(model.K, rule=depot_depart_rule)

    def depot_return_rule(model, k):
        return sum(
            model.x[i, depot, k]
            for i in model.nodes
            if i != depot
        ) == model.use_vehicle[k]

    model.depot_return = pyo.Constraint(model.K, rule=depot_return_rule)

    def capacity_rule(model, k):
        return sum(
            model.d[j] *
            sum(model.x[i, j, k] for i in model.nodes if i != j)
            for j in model.customers
        ) <= model.q[k]

    model.capacity = pyo.Constraint(model.K, rule=capacity_rule)

    def load_depot_rule(model, k):
        return model.u[depot, k] == 0

    model.load_depot = pyo.Constraint(model.K, rule=load_depot_rule)

    def load_propagation_rule(model, i, j, k):
        if i == j or j == depot:
            return pyo.Constraint.Skip

        demand_j = model.d[j] if j in model.customers else 0

        return model.u[j, k] >= model.u[i, k] + demand_j - model.M * (1 - model.x[i, j, k])

    model.load_propagation = pyo.Constraint(model.nodes, model.nodes, model.K, rule=load_propagation_rule)

    def load_capacity_rule(model, i, k):
        return model.u[i, k] <= model.q[k]

    model.load_capacity = pyo.Constraint(model.nodes, model.K, rule=load_capacity_rule)

    return model


def solve_fast_model(data):
    print(">>> FAST DAILY ROUTING MODEL STARTED", flush=True)
    print("nodes rows:", len(data["I"]), flush=True)
    print("vehicles rows:", len(data["K"]), flush=True)
    print("cost rows:", len(data["c"]), flush=True)
    print("demand rows:", len(data["d"]), flush=True)
    print("active points:", data["active_points"], flush=True)
    print("customers:", data["customers"], flush=True)

    model = build_fast_model(data)

    solver = pyo.SolverFactory("highs")
    result = solver.solve(model, tee=True)

    routes = []

    for k in model.K:
        for i in model.nodes:
            for j in model.nodes:
                if i != j:
                    val = model.x[i, j, k].value

                    if val is not None and val > 0.5:
                        routes.append({
                            "Vehicle": k,
                            "From": i,
                            "To": j
                        })

    assignments = []

    for p in model.active_points:
     for j in model.customers:
        val = model.y[p, j].value

        if val is not None and val > 0.5:
            assignments.append({
                "Active Point": p,
                "Customer": j,
                "Distance": pyo.value(model.c[p, j])
            })

    return model, result, routes, assignments