import pyomo.environ as pyo

def build_objective_equation(model, w):
 
 def z_rule(model):

    return model.z == sum(model.Cs[s] for s in model.S) / len(model.S)

 model.z_definition = pyo.Constraint(rule=z_rule)

def build_cost_objective(model):

    model.obj_cost = pyo.Objective(
        expr=model.z,
        sense=pyo.minimize
    )

def build_dmax_objective(model):
    model.obj_dmax = pyo.Objective(
        expr=model.Dmax,
        sense=pyo.minimize
    )