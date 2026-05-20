import pyomo.environ as pyo


def build_constraints(model, w):
    
    def vehicle_depot_departure_rule(model, k, s):
        return sum(
            model.x['i0', j, k, s, o]
            for j in model.I if j != 'i0'
            for o in model.O
        ) <= 1

    model.vehicle_depot_departure = pyo.Constraint(
        model.K,
        model.S,
        rule=vehicle_depot_departure_rule
    )

    def vehicle_depot_return_rule(model, k, s):
        return sum(
            model.x[j, 'i0', k, s, o]
            for j in model.I if j != 'i0'
            for o in model.O
        ) <= 1

    model.vehicle_depot_return = pyo.Constraint(
        model.K,
        model.S,
        rule=vehicle_depot_return_rule
    )

    def vehicle_flow_conservation_rule(model, j, k, s):
        return sum(
            model.x[i, j, k, s, o]
            for i in model.I
            for o in model.O
            if i != j
        ) == sum(
            model.x[j, i, k, s, o]
            for i in model.I
            for o in model.O
            if i != j
        )

    model.vehicle_flow_conservation = pyo.Constraint(
        model.I,
        model.K,
        model.S,
        rule=vehicle_flow_conservation_rule
    )

    def two_vehicle_rule(model, s):
        return sum(
            model.t[k, s]
            for k in model.K
        ) >= 2

    model.two_vehicle = pyo.Constraint(
        model.S,
        rule=two_vehicle_rule
    )

    def vehicle_usage_indicator_rule(model, k, s, o):
        return sum(
            model.x[i, j, k, s, o]
            for i in model.I
            for j in model.I
        ) <= 1

    model.vehicle_usage_indicator = pyo.Constraint(
          model.K,
          model.S,
          model.O,
          rule=vehicle_usage_indicator_rule
    )

    def force_to_two_vehicle_rule(model, s, k):
        return sum(
            model.x['i0', j, k, s, o]
            for o in model.O
            for j in model.I
        ) == model.t[k, s]

    model.force_to_two_vehicle = pyo.Constraint(
        model.S,
        model.K,
        rule=force_to_two_vehicle_rule
    )

    def is_customer_node(i):
        try:
            num = int(i[1:])
            return num >= w +1 
        except:
            return False

    def customer_arrival_rule(model, i, s):
        if not is_customer_node(i):
            return pyo.Constraint.Skip
        return sum(
            model.x[j, i, k, s, o]
            for k in model.K
            for j in model.I
            for o in model.O
            if j != i
        ) <= 1

    model.customer_arrival = pyo.Constraint(
        model.I,
        model.S,
        rule=customer_arrival_rule
    )

    def customer_departure_rule(model, i, s):
        if not is_customer_node(i):
            return pyo.Constraint.Skip
        return sum(
            model.x[i, j, k, s, o]
            for k in model.K
            for j in model.I
            for o in model.O
            if j != i
        ) <= 1

    model.customer_departure = pyo.Constraint(
        model.I,
        model.S,
        rule=customer_departure_rule
    )

    def customer_location_constraint_rule(model):
        return sum(
            model.a[j]
            for j in model.I
            if is_customer_node(j)
        ) == 0

    model.customer_location_constraint = pyo.Constraint(
        rule=customer_location_constraint_rule
    )

    def deneme3handtohanddemandzero_rule(model, j, s):
        return sum(
            model.x[i, j, k, s, o]
            for k in model.K
            for o in model.O
            for i in model.I
        ) * model.M >= model.dh[j, s] + model.ph[j, s]

    model.deneme3handtohanddemandzero = pyo.Constraint(
        model.I,
        model.S,
        rule=deneme3handtohanddemandzero_rule
    )

    def is_access_point_node(i):
        try:
            num = int(i[1:])
            return 1 <= num <= w
        except:
            return False

    def access_point_arrival_rule(model, i, s):
        if not is_access_point_node(i):
            return pyo.Constraint.Skip
        return sum(
            model.x[j, i, k, s, o]
            for k in model.K
            for j in model.I
            for o in model.O
            if j != i
        ) <= 1

    model.access_point_arrival = pyo.Constraint(
        model.I,
        model.S,
        rule=access_point_arrival_rule
    )

    def access_point_departure_rule(model, i, s):
        if not is_access_point_node(i):
            return pyo.Constraint.Skip
        return sum(
            model.x[i, j, k, s, o]
            for k in model.K
            for j in model.I
            for o in model.O
            if j != i
        ) <= 1

    model.access_point_departure = pyo.Constraint(
        model.I,
        model.S,
        rule=access_point_departure_rule
    )

    def access_point_activation_rule(model, i, s):
        if not is_access_point_node(i):
            return pyo.Constraint.Skip
        return (
            sum(
                model.x[i, j, k, s, o]
                for k in model.K
                for j in model.I
                for o in model.O
            )
            +
            sum(
                model.x[j, i, k, s, o]
                for k in model.K
                for j in model.I
                for o in model.O
            )
        ) <= model.M * model.a[i]

    model.access_point_activation = pyo.Constraint(
        model.I,
        model.S,
        rule=access_point_activation_rule
    )

    def access_point_service_limit_rule(model, i):
        return sum(
            model.y[i, j]
            for j in model.I
        ) <= model.a[i] * model.M

    model.access_point_service_limit = pyo.Constraint(
        model.I,
        rule=access_point_service_limit_rule
    )


    def access_point_demand_load_rule(model, i, s):
        if not is_access_point_node(i):
            return pyo.Constraint.Skip
        return sum(
            model.y[i, j] * model.d[j, s]
            for j in model.I
            if is_customer_node(j)
        ) == model.l[i, s]

    model.access_point_demand_load = pyo.Constraint(
        model.I,
        model.S,
        rule=access_point_demand_load_rule
    )

    def access_point_capacity_rule(model, i, s):
        return model.l[i, s] <= model.apc[i]

    model.access_point_capacity = pyo.Constraint(
        model.I,
        model.S,
        rule=access_point_capacity_rule
    )

    def prevent_self_loops_rule(model):
        return sum(
            model.x[i, j, k, s, o]
            for i in model.I
            for j in model.I
            for k in model.K
            for s in model.S
            for o in model.O
            if j == i
        ) == 0

    model.prevent_self_loops = pyo.Constraint(
        rule=prevent_self_loops_rule
    )

    def flow_conservation_rule(model, i, s):
        if i == 'i0':
            return pyo.Constraint.Skip
        return (
            sum(
                model.f[i, j, k, s]
                for j in model.I
                for k in model.K
            )
            - sum(
                model.f[j, i, k, s]
                for j in model.I
                for k in model.K
            )
            == 0.01 * sum(
                model.x[j, i, k, s, o]
                for j in model.I
                for k in model.K
                for o in model.O
            )
        )

    model.flow_conservation = pyo.Constraint(
        model.I,
        model.S,
        rule=flow_conservation_rule
    )

    def flow_capacity_rule(model, k, j, jj, s):
        return model.f[j, jj, k, s] <= sum(
            model.x[j, jj, k, s, o]
            for o in model.O
        )

    model.flow_capacity = pyo.Constraint(
        model.K,
        model.I,
        model.I,
        model.S,
        rule=flow_capacity_rule
    )


    def vehicle_capacity_limit2_rule(model, i, k, s):
        return sum(
            model.pi[i, k, s, o]
            for o in model.O
        ) <= model.M * sum(
            model.b[i, k, s, o]
            for o in model.O
        )

    model.vehicle_capacity_limit2 = pyo.Constraint(
        model.I,
        model.K,
        model.S,
        rule=vehicle_capacity_limit2_rule
    )

    def is_depot_or_customer(j):
        if j == 'i0':
            return True
        return is_customer_node(j)


    def vehicle_visit_indicator_rule(model, i, k, s):
        if not is_access_point_node(i):
            return pyo.Constraint.Skip
        return sum(
            model.x[i, j, k, s, o]
            for j in model.I
            for o in model.O
            if is_depot_or_customer(j)
        ) == sum(
            model.b[i, k, s, o]
            for o in model.O
        )

    model.vehicle_visit_indicator = pyo.Constraint(
        model.I,
        model.K,
        model.S,
        rule=vehicle_visit_indicator_rule
    )

    def load_balance_min_rule(model, i, s):
        if not is_access_point_node(i):
            return pyo.Constraint.Skip
        return sum(
            model.pi[i, k, s, o]
            for k in model.K
            for o in model.O
        ) <= model.l[i, s]

    model.load_balance_min = pyo.Constraint(
        model.I,
        model.S,
        rule=load_balance_min_rule
    )

    def load_balance_max_rule(model, i, s):
        if not is_access_point_node(i):
            return pyo.Constraint.Skip
        return sum(
            model.pi[i, k, s, o]
            for k in model.K
            for o in model.O
        ) >= model.l[i, s] - (
            1 - sum(model.b[i, k, s, o] for k in model.K for o in model.O)
        ) * model.M

    model.load_balance_max = pyo.Constraint(
        model.I,
        model.S,
        rule=load_balance_max_rule
    )

    def load_activation_link_rule(model, i, s):
        if not is_access_point_node(i):
            return pyo.Constraint.Skip
        return model.l[i, s] <= model.M * sum(
            model.x[i, j, k, s, o]
            for k in model.K
            for j in model.I
            for o in model.O
            if is_depot_or_customer(j)
        )

    model.load_activation_link = pyo.Constraint(
        model.I,
        model.S,
        rule=load_activation_link_rule
    )

    def nearest_access_point_rule(model, ii, j):
        if (not is_access_point_node(ii)) or (not is_customer_node(j)):
            return pyo.Constraint.Skip
        return sum(
            model.y[i, j] * model.c[i, j]
            for i in model.I
            if is_access_point_node(i)
        ) <= model.a[ii] * model.c[ii, j] + (1 - model.a[ii]) * model.M

    model.nearest_access_point = pyo.Constraint(
        model.I,
        model.I,
        rule=nearest_access_point_rule
    )

    def single_assignment_rule(model, j):
        if not is_customer_node(j):
            return pyo.Constraint.Skip
        return sum(
            model.y[i, j]
            for i in model.I
            if is_access_point_node(i)
        ) == 1

    model.single_assignment = pyo.Constraint(
        model.I,
        rule=single_assignment_rule
    )

    def distance_betw_customer_and_her_access_point_rule(model, j):
        if not is_customer_node(j):
            return pyo.Constraint.Skip
        return sum(
            model.y[i, j] * model.c[i, j]
            for i in model.I
            if is_access_point_node(i)
        ) == model.cust_distance_to_access[j]

    model.distance_betw_customer_and_her_access_point = pyo.Constraint(
        model.I,
        rule=distance_betw_customer_and_her_access_point_rule
    )

    def is_not_first_order(o):
        try:
            num = int(o[1:])
            return num > 1
        except:
            return False

    def no_depot_after_first_rule(model, s):
        return sum(
            model.x['i0', j, k, s, o]
            for k in model.K
            for j in model.I
            for o in model.O
            if is_not_first_order(o)
        ) == 0

    model.no_depot_after_first = pyo.Constraint(
        model.S,
        rule=no_depot_after_first_rule
    )

    def next_order(o):
        try:
            num = int(o[1:])
            return f"o{num+1}"
        except:
            return None

    def sequencing_order_rule(model, k, s, o, j):
        if j == 'i0':
            return pyo.Constraint.Skip

        oo = next_order(o)
        if oo not in model.O:
            return pyo.Constraint.Skip

        return sum(
            model.x[i, j, k, s, o]
            for i in model.I
        ) >= sum(
            model.x[j, i, k, s, oo]
            for i in model.I
        )

    model.sequencing_order = pyo.Constraint(
        model.K,
        model.S,
        model.O,
        model.I,
        rule=sequencing_order_rule
    )


    def is_first_order(o):
        try:
            num = int(o[1:])
            return num == 1
        except:
            return False

    def is_middle_or_later_but_not_last_order(o, model):
        try:
            num = int(o[1:])
            max_num = max(int(oo[1:]) for oo in model.O)
            return (num > 1) and (num < max_num)
        except:
            return False

    def how_much_each_k_is_loaded_rule(model, k, s):
        return (
            sum(
                model.pi[i, k, s, o]
                for i in model.I
                for o in model.O
                if is_access_point_node(i)
            )
            + (
                sum(
                    model.dh[j, s] * model.x[ii, j, k, s, o]
                    for ii in model.I
                    for j in model.I
                    for o in model.O
                    if ii != j
                )
                + sum(
                    model.dh[j, s] * model.x[j, ii, k, s, o]
                    for ii in model.I
                    for j in model.I
                    for o in model.O
                    if ii != j
                )
            ) / 2
            == model.lambdatotalload[k, s, 'o1']
        )

    model.how_much_each_k_is_loaded = pyo.Constraint(
        model.K,
        model.S,
        rule=how_much_each_k_is_loaded_rule
    )

    def lambda_balance_initial_rule(model, k, s, o):
        if not is_first_order(o):
            return pyo.Constraint.Skip

        oo = next_order(o)
        if oo not in model.O:
            return pyo.Constraint.Skip

        return (
            model.lambdatotalload[k, s, o]
            + (
                sum(
                    model.mi[j, s] * model.x[j, i, k, s, oo]
                    for j in model.I
                    for i in model.I
                )
                + sum(
                    model.pr[i, k, s, o]
                    for i in model.I
                    if is_access_point_node(i)
                )
            )
            == model.lambdatotalload[k, s, oo]
        )

    model.lambda_balance_initial = pyo.Constraint(
        model.K,
        model.S,
        model.O,
        rule=lambda_balance_initial_rule
    )

    def lambda_balance_rule(model, k, s, o):
        if not is_middle_or_later_but_not_last_order(o, model):
            return pyo.Constraint.Skip

        oo = next_order(o)
        if oo not in model.O:
            return pyo.Constraint.Skip

        return (
            model.lambdatotalload[k, s, o]
            + (
                sum(
                    model.mi[j, s] * model.x[j, i, k, s, oo]
                    for j in model.I
                    for i in model.I
                )
                + sum(
                    model.pr[i, k, s, o]
                    for i in model.I
                    if is_access_point_node(i)
                )
            )
            == model.lambdatotalload[k, s, oo]
        )

    model.lambda_balance = pyo.Constraint(
        model.K,
        model.S,
        model.O,
        rule=lambda_balance_rule
    )

    def accesspoint_demand_rule(model, i, s):
        if not is_access_point_node(i):
            return pyo.Constraint.Skip
        return sum(
            model.y[i, j] * (model.p[j, s] - model.d[j, s])
            for j in model.I
        ) == model.mi_ap[i, s]

    model.accesspoint_demand = pyo.Constraint(
        model.I,
        model.S,
        rule=accesspoint_demand_rule
    )

    def pr_ub1_rule(model, i, k, s, o):
        if not is_access_point_node(i):
            return pyo.Constraint.Skip
        return model.pr[i, k, s, o] <= (
            sum(model.x[j, i, k, s, o] for j in model.I)
        ) * model.M

    model.pr_ub1 = pyo.Constraint(
        model.I,
        model.K,
        model.S,
        model.O,
        rule=pr_ub1_rule
    )

    def pr_ub2_rule(model, i, k, s, o):
        if not is_access_point_node(i):
            return pyo.Constraint.Skip
        return model.pr[i, k, s, o] >= (
            sum(model.x[j, i, k, s, o] for j in model.I)
        ) * (-model.M)

    model.pr_ub2 = pyo.Constraint(
        model.I,
        model.K,
        model.S,
        model.O,
        rule=pr_ub2_rule
    )

    def pr_lb1_rule(model, i, k, s, o):
        if not is_access_point_node(i):
            return pyo.Constraint.Skip
        return model.pr[i, k, s, o] >= model.mi_ap[i, s] - (
            1 - sum(model.x[j, i, k, s, o] for j in model.I)
        ) * model.M

    model.pr_lb1 = pyo.Constraint(
        model.I,
        model.K,
        model.S,
        model.O,
        rule=pr_lb1_rule
    )

    def pr_lb2_rule(model, i, k, s, o):
        if not is_access_point_node(i):
            return pyo.Constraint.Skip
        return model.pr[i, k, s, o] <= model.mi_ap[i, s] - (
            1 - sum(model.x[j, i, k, s, o] for j in model.I)
        ) * (-model.M)

    model.pr_lb2 = pyo.Constraint(
        model.I,
        model.K,
        model.S,
        model.O,
        rule=pr_lb2_rule
    )

    def dmax_definition_rule(model, j):
        if not is_customer_node(j):
            return pyo.Constraint.Skip
        return model.cust_distance_to_access[j] <= model.Dmax
    
    model.dmax_definition = pyo.Constraint(
        model.I,
        rule=dmax_definition_rule
    )

    def scenario_cost_definition_rule(model, s):
      
      fixed_ap_cost = sum(
        model.af[i] * model.a[i]
        for i in model.I
        if i != "i0"
      )

      routing_cost = sum(
        model.c[i, j] * model.x[i, j, k, s, o]
        for i in model.I
        for j in model.I
        for k in model.K
        for o in model.O
        if i != j
      )

      vehicle_fixed_cost = sum(
        model.tf[k] * model.t[k, s]
        for k in model.K
      )

      variable_load_cost = sum(
        model.v[i] * model.l[i, s]
        for i in model.I
        if i != "i0"
      )

      return model.Cs[s] == fixed_ap_cost + routing_cost + vehicle_fixed_cost + variable_load_cost

    model.scenario_cost_constraint = pyo.Constraint(model.S, rule=scenario_cost_definition_rule)

    def total_cost_definition_rule(model):
     return model.z == sum(model.Cs[s] for s in model.S) / len(model.S)

    #model.total_cost_definition = pyo.Constraint(rule=total_cost_definition_rule)