import pyomo.environ as pyo


def build_parameters(model, data):

    # Delivery demand
    d_dict = {
        (row["customer"], row["scenario"]): row["demand"]
        for _, row in data["d"].iterrows()
    }
    model.d = pyo.Param(model.I, model.S, initialize=d_dict, default=0)

    # Hand-to-hand delivery demand
    dh_dict = {
        (row["customer"], row["scenario"]): row["handtohand_demand"]
        for _, row in data["dh"].iterrows()
    }
    model.dh = pyo.Param(model.I, model.S, initialize=dh_dict, default=0)

    # Pickup demand
    p_dict = {
        (row["customer"], row["scenario"]): row["pickup"]
        for _, row in data["p"].iterrows()
    }
    model.p = pyo.Param(model.I, model.S, initialize=p_dict, default=0)

    # Hand-to-hand pickup demand
    ph_dict = {
        (row["customer"], row["scenario"]): row["handtohand_pickup"]
        for _, row in data["ph"].iterrows()
    }
    model.ph = pyo.Param(model.I, model.S, initialize=ph_dict, default=0)

    # Distance / cost matrix
    c_dict = {
        (row["i"], row["j"]): row["distance"]
        for _, row in data["c"].iterrows()
    }
    model.c = pyo.Param(model.I, model.I, initialize=c_dict, default=0, within=pyo.Reals)

    # Vehicle capacity
    q_dict = {
        row["vehicle"]: row["capacity"]
        for _, row in data["q"].iterrows()
    }
    model.q = pyo.Param(model.K, initialize=q_dict, default=0)

    # Vehicle fixed cost
    tf_dict = {
        row["vehicle"]: row["fixed cost"]
        for _, row in data["tf"].iterrows()
    }
    model.tf = pyo.Param(model.K, initialize=tf_dict, default=0)

    # AP fixed cost
    af_dict = {
        row["AP"]: row["fixed cost"]
        for _, row in data["af"].iterrows()
    }
    model.af = pyo.Param(model.I, initialize=af_dict, default=0)

    # AP variable cost
    v_dict = {
        row["AP"]: row["variable cost"]
        for _, row in data["v"].iterrows()
    }
    model.v = pyo.Param(model.I, initialize=v_dict, default=0)

    # AP capacity
    apc_dict = {
        row["AP"]: row["capacity"]
        for _, row in data["apc"].iterrows()
    }
    model.apc = pyo.Param(model.I, initialize=apc_dict, default=0)

    # Scalar constants
    model.M = pyo.Param(initialize=10000)

    # mi(i,s) = ph(i,s) - dh(i,s)
    def mi_rule(model, i, s):
        return model.ph[i, s] - model.dh[i, s]

    model.mi = pyo.Param(model.I, model.S, initialize=mi_rule)

    print(">>> PARAMETERS BUILT SUCCESSFULLY")