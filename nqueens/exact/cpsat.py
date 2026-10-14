"""Google OR-Tools CP-SAT models of N-Queens."""
from __future__ import annotations

import time

from ortools.sat.python import cp_model

from nqueens.common import SolveResult, is_valid_solution
from nqueens.exact import cell_lines


def build_int_model(n: int) -> tuple[cp_model.CpModel, list[cp_model.IntVar]]:
    """Integer CP model: q[r] = column of the queen in row r.

        AllDifferent(q[r]),  AllDifferent(q[r] + r),  AllDifferent(q[r] - r)
    """
    model = cp_model.CpModel()
    q = [model.new_int_var(0, n - 1, f"q{r}") for r in range(n)]
    model.add_all_different(q)
    model.add_all_different([q[r] + r for r in range(n)])
    model.add_all_different([q[r] - r for r in range(n)])
    return model, q


def build_bool_model(n: int) -> tuple[cp_model.CpModel, list[cp_model.IntVar], int]:
    """0-1 model identical to the MIP: ExactlyOne per row/column, AtMostOne per diagonal.

    Returns:
        (model, x, number of constraints) with x[r*n + c] the cell variables.
    """
    model = cp_model.CpModel()
    x = [model.new_bool_var(f"x{i}") for i in range(n * n)]
    rows, cols, diagonals = cell_lines(n)
    for line in rows + cols:
        model.add_exactly_one(x[i] for i in line)
    for line in diagonals:
        model.add_at_most_one(x[i] for i in line)
    return model, x, len(rows) + len(cols) + len(diagonals)


def _solver(time_limit: float, workers: int, seed: int) -> cp_model.CpSolver:
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = workers
    solver.parameters.random_seed = seed
    return solver


def _status(status: int) -> str:
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return "SAT"
    if status == cp_model.INFEASIBLE:
        return "UNSAT"
    if status == cp_model.UNKNOWN:
        return "TIMEOUT"
    return "ERROR"


def solve_cpsat_int(
    n: int, time_limit: float = 60.0, workers: int = 1, seed: int = 0
) -> SolveResult:
    """Solve the integer model (see `build_int_model`) with CP-SAT.

    Args:
        n: board size.
        time_limit: seconds given to CP-SAT.
        workers: search threads (1 for a fair comparison with SAT solvers).
        seed: random seed.

    Returns:
        SolveResult; num_vars = n, num_clauses = 3 (global constraints).
    """
    t0 = time.perf_counter()
    model, q = build_int_model(n)
    build = time.perf_counter() - t0
    solver = _solver(time_limit, workers, seed)
    start = time.perf_counter()
    status = solver.solve(model)
    result = SolveResult(_status(status), None, time.perf_counter() - start, n, 3, build)
    if result.status == "SAT":
        result.cols = [solver.value(v) for v in q]
        if not is_valid_solution(result.cols, n):
            result.status, result.note = "ERROR", "invalid solution"
    return result


def solve_cpsat_bool(
    n: int, time_limit: float = 60.0, workers: int = 1, seed: int = 0
) -> SolveResult:
    """Solve the 0-1 model (see `build_bool_model`) with CP-SAT.

    Args and Returns: as `solve_cpsat_int`; num_vars = n^2 and num_clauses is
    the number of ExactlyOne / AtMostOne constraints (6n - 6).
    """
    t0 = time.perf_counter()
    model, x, num_cons = build_bool_model(n)
    build = time.perf_counter() - t0
    solver = _solver(time_limit, workers, seed)
    start = time.perf_counter()
    status = solver.solve(model)
    result = SolveResult(_status(status), None, time.perf_counter() - start,
                         n * n, num_cons, build)
    if result.status == "SAT":
        result.cols = [next(c for c in range(n) if solver.value(x[r * n + c]))
                       for r in range(n)]
        if not is_valid_solution(result.cols, n):
            result.status, result.note = "ERROR", "invalid solution"
    return result


class _Counter(cp_model.CpSolverSolutionCallback):
    """Counts solutions during enumeration."""

    def __init__(self) -> None:
        super().__init__()
        self.count = 0

    def on_solution_callback(self) -> None:
        self.count += 1


def count_cpsat(
    n: int, model_kind: str = "int", time_limit: float = 60.0, seed: int = 0
) -> tuple[str, int, float]:
    """Enumerate all solutions with CP-SAT (single worker, as enumeration requires).

    Args:
        n: board size.
        model_kind: "int" (`build_int_model`) or "bool" (`build_bool_model`).
        time_limit: seconds.
        seed: random seed.

    Returns:
        (status, number of solutions found, search time). status is "SAT" or
        "UNSAT" when the enumeration finished, "TIMEOUT" otherwise.
    """
    model = build_int_model(n)[0] if model_kind == "int" else build_bool_model(n)[0]
    solver = _solver(time_limit, 1, seed)
    solver.parameters.enumerate_all_solutions = True
    counter = _Counter()
    start = time.perf_counter()
    status = solver.solve(model, counter)
    elapsed = time.perf_counter() - start
    if status == cp_model.OPTIMAL:
        return ("SAT" if counter.count else "UNSAT"), counter.count, elapsed
    if status == cp_model.INFEASIBLE:
        return "UNSAT", 0, elapsed
    return "TIMEOUT", counter.count, elapsed
