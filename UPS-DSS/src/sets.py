import pyomo.environ as pyo

def build_sets(model, data):

    model.I = pyo.Set(initialize=data["I"]["Customer"].tolist())
    model.K = pyo.Set(initialize=data["K"]["Vehicle"].tolist())
    model.S = pyo.Set(initialize=data["S"]["Scenario"].tolist())
    model.O = pyo.Set(initialize=data["O"]["Order"].tolist(), ordered=True)