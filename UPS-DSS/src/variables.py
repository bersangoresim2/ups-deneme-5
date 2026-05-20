import pyomo.environ as pyo

def build_variables(model):

    model.x = pyo.Var(model.I, model.I, model.K, model.S, model.O, domain=pyo.Binary)

    model.y = pyo.Var(model.I, model.I, domain=pyo.Binary)

    model.a = pyo.Var(model.I, domain=pyo.Binary)

    model.t = pyo.Var(model.K, model.S, domain=pyo.Binary)

    model.f = pyo.Var(model.I, model.I, model.K, model.S, domain=pyo.NonNegativeReals)

    model.l = pyo.Var(model.I, model.S, domain=pyo.NonNegativeReals)

    model.b = pyo.Var(model.I, model.K, model.S, model.O, domain=pyo.Binary)

    model.pi = pyo.Var(model.I, model.K, model.S, model.O, domain=pyo.NonNegativeReals)

    model.pr = pyo.Var(model.I, model.K, model.S, model.O, domain=pyo.Reals)

    model.lambdatotalload = pyo.Var(model.K, model.S, model.O, domain=pyo.NonNegativeReals)

    model.z = pyo.Var(domain=pyo.Reals)

    model.mi_ap = pyo.Var(model.I, model.S, domain=pyo.Reals)

    model.cust_distance_to_access = pyo.Var(model.I, domain=pyo.NonNegativeReals)

    model.Dmax = pyo.Var(domain=pyo.NonNegativeReals)

    model.Cs = pyo.Var(model.S, domain=pyo.NonNegativeReals)
