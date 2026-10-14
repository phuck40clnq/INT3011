"""IBM CPLEX 0-1 integer programming model of N-Queens (docplex.mp)."""
from __future__ import annotations

import time

from docplex.mp.model import Model

from nqueens.common import SolveResult, is_valid_solution
from nqueens.exact import cell_lines, mip_size

# Community Edition: at most 1000 variables and 1000 constraints.
CPLEX_MAX_VARS = 1000


def solve_cplex_mip(
    n: int, time_limit: float = 60.0, threads: int = 1, seed: int = 0
) -> SolveResult:
    """Same feasibility MIP as `solve_gurobi`, solved by CPLEX.

    Args:
        n: board size.
        time_limit: CPLEX timelimit in seconds.
        threads: CPLEX threads parameter.
        seed: CPLEX randomseed parameter.

    Returns:
        SolveResult; status "ERROR" with a note when n^2 exceeds the license.
    """
    num_vars, num_cons = mip_size(n)
    if num_vars > CPLEX_MAX_VARS:
        return SolveResult("ERROR", None, 0.0, num_vars, num_cons,
                           note="exceeds Community Edition limit")
    t0 = time.perf_counter()
    with Model(name=f"queens{n}") as mdl:
        mdl.parameters.timelimit = time_limit
        mdl.parameters.threads = threads
        mdl.parameters.randomseed = seed
        x = mdl.binary_var_list(n * n, name="x")
        rows, cols, diagonals = cell_lines(n)
        for line in rows + cols:
            mdl.add_constraint(mdl.sum(x[i] for i in line) == 1)
        for line in diagonals:
            mdl.add_constraint(mdl.sum(x[i] for i in line) <= 1)
        build = time.perf_counter() - t0
        start = time.perf_counter()
        sol = mdl.solve(log_output=False)
        elapsed = time.perf_counter() - start
        result = SolveResult("ERROR", None, elapsed, num_vars, num_cons, build)
        details = mdl.solve_details.status.lower() if mdl.solve_details else ""
        if sol is not None:
            result.status = "SAT"
            result.cols = [next(c for c in range(n) if sol.get_value(x[r * n + c]) > 0.5)
                           for r in range(n)]
            if not is_valid_solution(result.cols, n):
                result.status, result.note = "ERROR", "invalid solution"
        elif "infeasible" in details:
            result.status = "UNSAT"
        elif "time limit" in details:
            result.status = "TIMEOUT"
        else:
            result.note = f"cplex status: {details}"
    return result
