"""Solve an N-Queens CNF with the SAT solvers shipped by PySAT."""
from __future__ import annotations

import time

from pysat.solvers import Solver

from nqueens.common import SolveResult, decode_model, is_valid_solution, var

# Solvers compared in the experiments (PySAT names).
SAT_SOLVERS = ("cadical195", "glucose4", "kissat404", "minisat22")


def solve_cnf(
    clauses: list[list[int]], n: int, solver_name: str, num_vars: int = 0
) -> SolveResult:
    """Run one SAT solver on the CNF and decode the queens.

    The time limit is enforced by the caller (the benchmark runs each solve in
    a child process and kills it), because not every PySAT backend supports
    `interrupt()`.

    Args:
        clauses: CNF produced by `nqueens.encodings.nqueens_cnf.build_cnf`.
        n: board size, used to decode the board variables 1..n*n.
        solver_name: PySAT solver name, e.g. "cadical195".
        num_vars: number of variables, copied into the result.

    Returns:
        SolveResult with time_s = clause loading + search. A SAT answer whose
        decoded board fails `is_valid_solution` is reported as "ERROR".
    """
    start = time.perf_counter()
    with Solver(name=solver_name, bootstrap_with=clauses) as solver:
        sat = solver.solve()
        model = solver.get_model() if sat else None
    elapsed = time.perf_counter() - start
    if not sat:
        return SolveResult("UNSAT", None, elapsed, num_vars, len(clauses))
    cols = decode_model(model, n)
    if not is_valid_solution(cols, n):
        return SolveResult("ERROR", cols, elapsed, num_vars, len(clauses),
                           note="invalid solution")
    return SolveResult("SAT", cols, elapsed, num_vars, len(clauses))


def count_solutions(
    clauses: list[list[int]], n: int, solver_name: str = "cadical195",
    limit: int | None = None,
) -> tuple[int, set[tuple[int, ...]]]:
    """Enumerate all solutions with blocking clauses on the board variables.

    After each model the clause "not this exact set of queens" is added.
    Blocking only the n*n board variables (not the auxiliary ones) makes each
    board counted once even if an encoding admits several auxiliary values.

    Args:
        clauses: N-Queens CNF.
        n: board size.
        solver_name: an incremental PySAT solver.
        limit: stop after this many solutions (None = all).

    Returns:
        (count, set of solutions as tuples). Every solution is checked with
        `is_valid_solution`; an invalid one raises ValueError.
    """
    found: set[tuple[int, ...]] = set()
    with Solver(name=solver_name, bootstrap_with=clauses) as solver:
        while solver.solve():
            cols = decode_model(solver.get_model(), n)
            if not is_valid_solution(cols, n):
                raise ValueError(f"invalid model decoded: {cols}")
            found.add(tuple(cols))
            solver.add_clause([-var(r, c, n) for r, c in enumerate(cols)])
            if limit is not None and len(found) >= limit:
                break
    return len(found), found
