"""IBM CP Optimizer model of N-Queens (docplex.cp).

docplex.cp needs the `cpoptimizer` executable, which is not part of the pip
`cplex` wheel. It is looked up in $CPOPTIMIZER_PATH, then in PATH, then in a
standard CPLEX Optimization Studio installation under /Applications.
"""
from __future__ import annotations

import glob
import os
import shutil
import time

from nqueens.common import SolveResult, is_valid_solution


def find_cpoptimizer() -> str | None:
    """Return the path of the `cpoptimizer` executable, or None if absent."""
    candidates = [os.environ.get("CPOPTIMIZER_PATH"), shutil.which("cpoptimizer")]
    candidates += sorted(glob.glob("/Applications/CPLEX_Studio*/cpoptimizer/bin/*/cpoptimizer"))
    candidates += sorted(glob.glob(os.path.expanduser(
        "~/Applications/CPLEX_Studio*/cpoptimizer/bin/*/cpoptimizer")))
    for path in candidates:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def solve_cplex_cp(
    n: int, time_limit: float = 60.0, workers: int = 1, seed: int = 0
) -> SolveResult:
    """Integer CP model with three all_diff constraints, as in `solve_cpsat_int`.

    Args:
        n: board size.
        time_limit: CP Optimizer TimeLimit in seconds.
        workers: CP Optimizer Workers parameter.
        seed: CP Optimizer RandomSeed parameter.

    Returns:
        SolveResult; status "ERROR" with a note if cpoptimizer is missing.
    """
    execfile = find_cpoptimizer()
    if execfile is None:
        return SolveResult("ERROR", None, 0.0, n, 3, note="cpoptimizer not installed")
    from docplex.cp.model import CpoModel

    t0 = time.perf_counter()
    mdl = CpoModel(name=f"queens{n}")
    q = mdl.integer_var_list(n, 0, n - 1, "q")
    mdl.add(mdl.all_diff(q))
    mdl.add(mdl.all_diff([q[r] + r for r in range(n)]))
    mdl.add(mdl.all_diff([q[r] - r for r in range(n)]))
    build = time.perf_counter() - t0
    start = time.perf_counter()
    sol = mdl.solve(TimeLimit=time_limit, Workers=workers, RandomSeed=seed,
                    LogVerbosity="Quiet", execfile=execfile)
    elapsed = time.perf_counter() - start
    result = SolveResult("ERROR", None, elapsed, n, 3, build)
    status = sol.get_solve_status()
    if sol.is_solution():
        result.status = "SAT"
        result.cols = [sol.get_value(v) for v in q]
        if not is_valid_solution(result.cols, n):
            result.status, result.note = "ERROR", "invalid solution"
    elif status == "Infeasible":
        result.status = "UNSAT"
    elif sol.get_fail_status() == "SearchStoppedByLimit" or status == "Unknown":
        result.status = "TIMEOUT"
    else:
        result.note = f"cpo status: {status}"
    return result
