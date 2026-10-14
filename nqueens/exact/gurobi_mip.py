"""Gurobi 0-1 integer programming model of N-Queens."""
from __future__ import annotations

import time

import gurobipy as gp
from gurobipy import GRB

from nqueens.common import SolveResult, is_valid_solution
from nqueens.exact import cell_lines, mip_size

# Size-limited (pip) license: at most 2000 variables and 2000 constraints.
GUROBI_MAX_VARS = 2000


def solve_gurobi(
    n: int, time_limit: float = 60.0, threads: int = 1, seed: int = 0
) -> SolveResult:
    """Feasibility MIP: sum of a row/column = 1, sum of a diagonal <= 1, x binary.

    Args:
        n: board size.
        time_limit: Gurobi TimeLimit in seconds.
        threads: Gurobi Threads parameter.
        seed: Gurobi Seed parameter.

    Returns:
        SolveResult; status "ERROR" with a note when n^2 exceeds the license.
    """
    num_vars, num_cons = mip_size(n)
    if num_vars > GUROBI_MAX_VARS:
        return SolveResult("ERROR", None, 0.0, num_vars, num_cons,
                           note="exceeds size-limited license")
    t0 = time.perf_counter()
    with gp.Env(empty=True) as env:
        env.setParam("OutputFlag", 0)
        env.start()
        with gp.Model(env=env) as model:
            model.Params.TimeLimit = time_limit
            model.Params.Threads = threads
            model.Params.Seed = seed
            x = model.addVars(n * n, vtype=GRB.BINARY)
            rows, cols, diagonals = cell_lines(n)
            for line in rows + cols:
                model.addConstr(gp.quicksum(x[i] for i in line) == 1)
            for line in diagonals:
                model.addConstr(gp.quicksum(x[i] for i in line) <= 1)
            model.setObjective(0, GRB.MINIMIZE)
            build = time.perf_counter() - t0
            start = time.perf_counter()
            model.optimize()
            elapsed = time.perf_counter() - start
            result = SolveResult("ERROR", None, elapsed, num_vars, num_cons, build)
            if model.SolCount > 0:
                result.status = "SAT"
                result.cols = [next(c for c in range(n) if x[r * n + c].X > 0.5)
                               for r in range(n)]
                if not is_valid_solution(result.cols, n):
                    result.status, result.note = "ERROR", "invalid solution"
            elif model.Status == GRB.INFEASIBLE:
                result.status = "UNSAT"
            elif model.Status == GRB.TIME_LIMIT:
                result.status = "TIMEOUT"
            else:
                result.note = f"gurobi status {model.Status}"
    return result
