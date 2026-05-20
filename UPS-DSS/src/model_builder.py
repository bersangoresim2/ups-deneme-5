import pyomo.environ as pyo

from src.sets import build_sets
from src.parameters import build_parameters
from src.variables import build_variables
from src.constraints import build_constraints
from src.objective import build_objective_equation

def build_model(data, w):

    model = pyo.ConcreteModel()

    build_sets(model, data)
    build_parameters(model, data)
    build_variables(model)
    build_constraints(model, w)
    build_objective_equation(model, w)
    

    return model