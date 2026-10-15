"""Benchmark grid runner: (n, encoding, solver) -> one CSV row per run.

Usage (from the repository root):

    .venv/bin/python -m nqueens.experiments.run_benchmark sat   --time-limit 60
    .venv/bin/python -m nqueens.experiments.run_benchmark exact --time-limit 60
    .venv/bin/python -m nqueens.experiments.run_benchmark size
    .venv/bin/python -m nqueens.experiments.run_benchmark count --time-limit 60
    .venv/bin/python -m nqueens.experiments.run_benchmark exactsat --time-limit 60
    .venv/bin/python -m nqueens.experiments.run_benchmark colalo --time-limit 60

Each run happens in a fresh child process that is killed at the time limit,
so a hanging solver or a memory blow-up never stops the grid. For a given
configuration (encoding, solver), n grows until the first TIMEOUT or ERROR;
larger n are then not attempted (no row is written for them). The runner
resumes: rows already present in the CSV are not run again.
"""
from __future__ import annotations

import argparse
import csv
import multiprocessing as mp
import os
import platform
import subprocess
import sys
import time
from typing import Any, Iterator

from nqueens.common import OEIS_A000170
from nqueens.encodings.amo import ENCODERS
from nqueens.experiments.worker import EXACT_METHODS, run_job
from nqueens.solvers.pysat_runner import SAT_SOLVERS

FIELDS = ["experiment", "n", "encoding", "solver", "status", "time_s", "build_time_s",
          "total_time_s", "num_vars", "num_clauses", "count", "expected", "seed", "note"]

# Pairwise needs Theta(n^3) clauses: above n = 128 the Python CNF exceeds the
# memory of the 8 GB test machine, so larger n are not attempted. The PySAT
# totalizer also grows as Theta(n^3) (29.8M clauses at n = 256); in the `sat`
# experiment its n = 512 formula was not built within BUILD_TIMEOUT_S, so later
# experiments stop it at 256.
MAX_N = {"pairwise": 128, "pysat_pairwise": 128, "pysat_totalizer": 256}

BUILD_TIMEOUT_S = 900.0     # generous limit for building one CNF in Python
EXACT_GRACE_S = 30.0        # extra wall time for solvers that enforce their own limit


def grid(experiment: str) -> tuple[list[int], list[tuple[str, str]]]:
    """Board sizes and (encoding, solver) configurations of an experiment."""
    if experiment == "sat":
        return [2, 3, 8, 16, 32, 64, 128, 256, 512], [(e, s) for e in ENCODERS for s in SAT_SOLVERS]
    if experiment == "exact":
        return ([2, 3, 8, 16, 24, 31, 32, 40, 44, 64, 128, 256, 512, 1000],
                list(EXACT_METHODS))
    if experiment == "size":
        return [8, 16, 32, 64, 128, 256, 512], [(e, "-") for e in ENCODERS]
    if experiment == "count":
        configs = [(e, "cadical195") for e in ENCODERS]
        configs += [("-", "backtracking"), ("cp_int", "cpsat"), ("cp_bool", "cpsat")]
        return list(range(1, 13)), configs
    if experiment == "exactsat":
        # the two best SAT configurations of `sat`, on the board sizes of `exact`
        from nqueens.experiments.make_figures import best_sat_configs
        return grid("exact")[0], best_sat_configs(2)
    if experiment == "colalo":
        # ablation: redundant column ALO clauses on/off, best-performing solvers
        encs = ["sequential", "commander", "product", "binary"]
        return [32, 64, 128, 256, 512], [(e, s) for e in encs for s in ("cadical195", "kissat404")]
    raise ValueError(experiment)


def run_one(job: dict[str, Any]) -> dict[str, Any]:
    """Run a job in a child process and return the CSV fields it produced."""
    ctx = mp.get_context("spawn")
    parent, child = ctx.Pipe(duplex=False)
    proc = ctx.Process(target=run_job, args=(child, job))
    proc.start()
    child.close()
    row: dict[str, Any] = {}
    limit = job["time_limit"]
    try:
        if not parent.poll(BUILD_TIMEOUT_S):
            row.update(status="ERROR", note="build timeout")
            return row
        tag, info = parent.recv()
        if tag == "error":
            row.update(status="ERROR", note=info)
            return row
        row.update(info)
        wait = limit + (EXACT_GRACE_S if job["kind"] == "exact" else 0.0)
        if job["kind"] == "size":
            wait = BUILD_TIMEOUT_S
        start = time.perf_counter()
        if not parent.poll(wait):
            row.update(status="TIMEOUT", time_s=round(time.perf_counter() - start, 4))
            return row
        tag, info = parent.recv()
        if tag == "error":
            row.update(status="ERROR", note=info)
            return row
        row.update(info)
        if job["kind"] in ("sat", "count") and row["time_s"] > limit:
            row["status"] = "TIMEOUT"      # finished, but after the limit
        return row
    except EOFError:
        row.update(status="ERROR", note=f"worker died (exit code {proc.exitcode})")
        return row
    finally:
        if proc.is_alive():
            proc.kill()
        proc.join()
        parent.close()


def pending_jobs(experiment: str, time_limit: float, done: dict) -> Iterator[dict[str, Any]]:
    """Yield the jobs still to run, skipping configurations that already failed."""
    ns, configs = grid(experiment)
    kind = {"colalo": "sat", "exactsat": "sat"}.get(experiment, experiment)
    variants = [True, False] if experiment == "colalo" else [True]
    for n in ns:
        for encoding, solver in configs:
            for col_alo in variants:
                enc_label = encoding if col_alo else f"{encoding}-nocolalo"
                key = (n, enc_label, solver)
                if key in done:
                    continue
                if n > MAX_N.get(encoding, 10**9):
                    continue
                if any(k[1:] == key[1:] and k[0] < n and st in ("TIMEOUT", "ERROR")
                       for k, st in done.items()):
                    continue
                yield {"kind": kind, "experiment": experiment, "n": n, "encoding": encoding,
                       "enc_label": enc_label, "solver": solver, "time_limit": time_limit,
                       "col_alo": col_alo}


def load_done(path: str) -> dict[tuple[int, str, str], str]:
    """(n, encoding, solver) -> status for rows already in the CSV."""
    if not os.path.exists(path):
        return {}
    with open(path, newline="") as f:
        return {(int(r["n"]), r["encoding"], r["solver"]): r["status"] for r in csv.DictReader(f)}


def write_environment(path: str) -> None:
    """Record machine, OS, Python and solver versions for the report appendix."""
    import gurobipy
    import ortools
    import pysat
    import cplex
    import docplex

    try:
        cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                             capture_output=True, text=True).stdout.strip()
        mem = int(subprocess.run(["sysctl", "-n", "hw.memsize"],
                                 capture_output=True, text=True).stdout) // 2**30
    except (OSError, ValueError):
        cpu, mem = platform.processor(), -1
    lines = [
        f"cpu: {cpu}",
        f"logical_cpus: {os.cpu_count()}",
        f"memory_gb: {mem}",
        f"os: {platform.platform()}",
        f"python: {sys.version.split()[0]}",
        f"python-sat: {pysat.__version__}",
        f"ortools: {ortools.__version__}",
        f"gurobipy: {'.'.join(map(str, gurobipy.gurobi.version()))}",
        f"cplex: {cplex.Cplex().get_version()}",
        f"docplex: {docplex.__version__}",
    ]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("experiment",
                        choices=["sat", "exact", "exactsat", "size", "count", "colalo"])
    parser.add_argument("--time-limit", type=float, default=60.0)
    parser.add_argument("--out", default=None, help="CSV path (default results/<experiment>.csv)")
    args = parser.parse_args()
    out = args.out or os.path.join("results", f"{args.experiment}.csv")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    write_environment(os.path.join(os.path.dirname(out) or ".", "environment.txt"))

    done = load_done(out)
    new_file = not os.path.exists(out)
    with open(out, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        for job in pending_jobs(args.experiment, args.time_limit, done):
            row = run_one(job)
            row.update(experiment=args.experiment, n=job["n"], encoding=job["enc_label"],
                       solver=job["solver"], seed=0)
            if args.experiment == "count":
                row["expected"] = OEIS_A000170[job["n"]]
            if row.get("time_s") is not None and row.get("build_time_s") is not None:
                row["total_time_s"] = row["time_s"] + row["build_time_s"]
            for key in ("time_s", "build_time_s", "total_time_s"):
                if isinstance(row.get(key), float):
                    row[key] = round(row[key], 4)
            writer.writerow({k: row.get(k, "") for k in FIELDS})
            f.flush()
            done[(job["n"], job["enc_label"], job["solver"])] = row["status"]
            print(f"[{args.experiment}] n={job['n']:<5} {job['enc_label']:<24} {job['solver']:<12} "
                  f"{row['status']:<8} t={row.get('time_s', '')}  {row.get('note', '')}", flush=True)


if __name__ == "__main__":
    main()
