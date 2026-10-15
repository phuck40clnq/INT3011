"""Child-process side of the benchmark: execute one job and report through a pipe.

Protocol: the child sends ("built", info) once the model is ready, then
("done", info) when the run finishes, or ("error", message) on an exception.
The parent measures the time limit from the "built" message, so the limit
applies to solving only, not to building the CNF in Python.
"""
from __future__ import annotations

import time
from multiprocessing.connection import Connection
from typing import Any, Callable

from nqueens.common import SolveResult


# (model label, solver label) -> (module, function). Imported lazily so that a
# child process loads only the solver it runs (CP-SAT's time limit was observed
# to shrink when Gurobi/CPLEX were imported in the same process).
EXACT_METHODS: dict[tuple[str, str], tuple[str, str]] = {
    ("cp_int", "cpsat"): ("nqueens.exact.cpsat", "solve_cpsat_int"),
    ("cp_bool", "cpsat"): ("nqueens.exact.cpsat", "solve_cpsat_bool"),
    ("mip01", "gurobi"): ("nqueens.exact.gurobi_mip", "solve_gurobi"),
    ("mip01", "cplex"): ("nqueens.exact.cplex_mip", "solve_cplex_mip"),
    ("cp_int", "cpoptimizer"): ("nqueens.exact.cplex_cp", "solve_cplex_cp"),
}


def exact_function(key: tuple[str, str]) -> Callable[..., SolveResult]:
    """Import and return the solve function of an exact method."""
    import importlib

    module, name = EXACT_METHODS[key]
    return getattr(importlib.import_module(module), name)


def _sat_like(job: dict[str, Any], conn: Connection) -> None:
    from nqueens.encodings.nqueens_cnf import encode
    from nqueens.solvers.pysat_runner import count_solutions, solve_cnf

    n = job["n"]
    t0 = time.perf_counter()
    clauses, num_vars = encode(n, job["encoding"], col_alo=job.get("col_alo", True))
    built = {"build_time_s": time.perf_counter() - t0,
             "num_vars": num_vars, "num_clauses": len(clauses)}
    conn.send(("built", built))
    if job["kind"] == "size":
        conn.send(("done", {"status": "BUILT", "time_s": 0.0}))
    elif job["kind"] == "sat":
        r = solve_cnf(clauses, n, job["solver"], num_vars)
        conn.send(("done", {"status": r.status, "time_s": r.time_s, "note": r.note}))
    else:   # count with a SAT solver
        start = time.perf_counter()
        count, _ = count_solutions(clauses, n, job["solver"])
        conn.send(("done", {"status": "SAT" if count else "UNSAT",
                            "time_s": time.perf_counter() - start, "count": count}))


def _count_other(job: dict[str, Any], conn: Connection) -> None:
    from nqueens.baselines.backtracking import count_all
    from nqueens.exact.cpsat import count_cpsat

    n = job["n"]
    conn.send(("built", {}))
    start = time.perf_counter()
    if job["solver"] == "backtracking":
        count = count_all(n)
        status, elapsed = ("SAT" if count else "UNSAT"), time.perf_counter() - start
    else:   # cpsat with the int or bool model
        model_kind = "int" if job["encoding"] == "cp_int" else "bool"
        status, count, elapsed = count_cpsat(n, model_kind, job["time_limit"])
    conn.send(("done", {"status": status, "time_s": elapsed, "count": count}))


def _exact(job: dict[str, Any], conn: Connection) -> None:
    fn = exact_function((job["encoding"], job["solver"]))
    conn.send(("built", {}))
    r = fn(job["n"], time_limit=job["time_limit"])
    conn.send(("done", {"status": r.status, "time_s": r.time_s,
                        "build_time_s": r.build_time_s, "num_vars": r.num_vars,
                        "num_clauses": r.num_clauses, "note": r.note}))


def run_job(conn: Connection, job: dict[str, Any]) -> None:
    """Entry point of the child process."""
    try:
        if job["kind"] == "exact":
            _exact(job, conn)
        elif job["kind"] == "count" and job["solver"] in ("backtracking", "cpsat"):
            _count_other(job, conn)
        else:
            _sat_like(job, conn)
    except Exception as exc:   # report, never hang the parent
        conn.send(("error", f"{type(exc).__name__}: {exc}"))
    finally:
        conn.close()
