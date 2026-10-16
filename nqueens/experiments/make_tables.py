"""Generate the LaTeX tables of the report from results/*.csv into report/tables/.

Every number printed in the report tables comes from these CSV files.
Usage: .venv/bin/python -m nqueens.experiments.make_tables
"""
from __future__ import annotations

import os

import pandas as pd

from nqueens.experiments.make_figures import (ENC_ORDER, LABEL, SOLVER_LABEL, best_sat_configs,
                                              sat_runs)

RESULTS = "results"
OUT = os.path.join("report", "tables")
SOLVERS = list(SOLVER_LABEL)
SOLVER_SHORT = {"cadical195": "CaDiCaL", "glucose4": "Glucose",
                "kissat404": "Kissat", "minisat22": "MiniSat"}


def num(x: float) -> str:
    """Integer with thin-space thousands separators."""
    return f"{int(x):,}".replace(",", "\\,")


def t(x: float) -> str:
    if x < 0.01:
        return "$<$0.01"
    if x < 10:
        return f"{x:.2f}"
    if x < 100:
        return f"{x:.1f}"
    return f"{x:.0f}"


def cell(df: pd.DataFrame, **key) -> str:
    """Time of one run, or TO (timeout), lic. (license limit), b.t. (build timeout), -- (not run)."""
    d = df
    for k, v in key.items():
        d = d[d[k] == v]
    if d.empty:
        return "--"
    r = d.iloc[0]
    if r.status in ("SAT", "UNSAT"):
        return t(r.time_s)
    if r.status == "TIMEOUT":
        return "TO"
    note = str(r.note).lower()
    if "licen" in note or "limit" in note:
        return "lic."
    if "build timeout" in note:
        return "b.t."                  # CNF not built within the build limit
    return "err"


def write(name: str, body: str) -> None:
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w") as f:
        f.write(body)
    print("wrote", os.path.join(OUT, name))


def tab_size() -> None:
    df = pd.read_csv(os.path.join(RESULTS, "size.csv"))
    ns = [n for n in (8, 64, 256, 512) if n in set(df.n)]
    head = " & ".join(f"\\multicolumn{{2}}{{c}}{{$n={n}$}}" for n in ns)
    rules = "".join(f"\\cmidrule(lr){{{2 + 2 * i}-{3 + 2 * i}}}" for i in range(len(ns)))
    sub = " & ".join(["vars & clauses"] * len(ns))
    lines = ["\\begin{tabular}{@{}l" + "rr" * len(ns) + "@{}}", "\\toprule",
             f"Encoding & {head} \\\\", rules, f" & {sub} \\\\", "\\midrule"]
    for enc in ENC_ORDER:
        row = [LABEL[enc]]
        for n in ns:
            d = df[(df.encoding == enc) & (df.n == n)]
            row += [num(d.num_vars.iloc[0]), num(d.num_clauses.iloc[0])] if len(d) else ["--", "--"]
        lines.append(" & ".join(row) + " \\\\")
        if enc == "product":
            lines.append("\\midrule")
    lines += ["\\bottomrule", "\\end{tabular}", ""]
    write("tab_size.tex", "\n".join(lines))


def tab_sat_summary() -> None:
    df = pd.read_csv(os.path.join(RESULTS, "sat.csv"))
    ok = df[df.status == "SAT"]
    head = " & ".join(f"\\multicolumn{{2}}{{c}}{{{SOLVER_SHORT[s]}}}" for s in SOLVERS)
    rules = "".join(f"\\cmidrule(lr){{{2 + 2 * i}-{3 + 2 * i}}}" for i in range(len(SOLVERS)))
    sub = " & ".join(["$n_{\\max}$ & $t_{256}$"] * len(SOLVERS))
    lines = ["\\begin{tabular}{@{}l" + "rr" * len(SOLVERS) + "@{}}", "\\toprule",
             f"Encoding & {head} \\\\", rules, f" & {sub} \\\\", "\\midrule"]
    for enc in ENC_ORDER:
        row = [LABEL[enc]]
        for s in SOLVERS:
            d = ok[(ok.encoding == enc) & (ok.solver == s)]
            runs = df[(df.encoding == enc) & (df.solver == s)]
            capped = len(d) and d.n.max() < max(df.n) and not (runs.status == "TIMEOUT").any()
            # dagger: stopped by the memory cap or the build limit, not by a solver timeout
            row.append((str(d.n.max()) + ("$^\\dagger$" if capped else "")) if len(d) else "--")
            row.append(cell(df, encoding=enc, solver=s, n=256))
        lines.append(" & ".join(row) + " \\\\")
        if enc == "product":
            lines.append("\\midrule")
    lines += ["\\bottomrule", "\\end{tabular}", ""]
    write("tab_sat_summary.tex", "\n".join(lines))


def tab_sat_detail() -> None:
    df = pd.read_csv(os.path.join(RESULTS, "sat.csv"))
    for part, ns in (("a", (32, 64)), ("b", (128, 256)), ("c", (512,))):
        head = " & ".join(f"\\multicolumn{{4}}{{c}}{{$n={n}$}}" for n in ns)
        rules = "".join(f"\\cmidrule(lr){{{2 + 4 * i}-{5 + 4 * i}}}" for i in range(len(ns)))
        sub = " & ".join([" & ".join(SOLVER_SHORT[s] for s in SOLVERS)] * len(ns))
        lines = ["\\begin{tabular}{@{}l" + "rrrr" * len(ns) + "@{}}", "\\toprule",
                 f"Encoding & {head} \\\\", rules, f" & {sub} \\\\", "\\midrule"]
        for enc in ENC_ORDER:
            row = [LABEL[enc]]
            for n in ns:
                row += [cell(df, encoding=enc, solver=s, n=n) for s in SOLVERS]
            lines.append(" & ".join(row) + " \\\\")
            if enc == "product":
                lines.append("\\midrule")
        lines += ["\\bottomrule", "\\end{tabular}", ""]
        write(f"tab_sat_detail_{part}.tex", "\n".join(lines))


EXACT_COLS = [(("cp_int", "cpsat"), "CP-SAT int"), (("cp_bool", "cpsat"), "CP-SAT 0-1"),
              (("mip01", "gurobi"), "Gurobi MIP"), (("mip01", "cplex"), "CPLEX MIP"),
              (("cp_int", "cpoptimizer"), "CPLEX CP")]


def tab_exact() -> None:
    ex = pd.read_csv(os.path.join(RESULTS, "exact.csv"))
    sat = sat_runs()
    best = best_sat_configs(2)
    cols = EXACT_COLS
    if not (ex[(ex.solver == "cpoptimizer")].status.isin(["SAT", "UNSAT"])).any():
        cols = EXACT_COLS[:-1]          # CP Optimizer could not be run
    heads = [f"{LABEL[e]}+{SOLVER_SHORT[s]}" for e, s in best] + [c[1] for c in cols]
    lines = ["\\begin{tabular}{@{}r" + "r" * len(heads) + "@{}}", "\\toprule",
             f"& \\multicolumn{{{len(best)}}}{{c}}{{SAT (this work)}} & "
             f"\\multicolumn{{{len(cols)}}}{{c}}{{Other exact methods}} \\\\",
             f"\\cmidrule(lr){{2-{1 + len(best)}}}\\cmidrule(lr){{{2 + len(best)}-{1 + len(heads)}}}",
             "$n$ & " + " & ".join(heads) + " \\\\", "\\midrule"]
    for n in sorted(ex.n.unique()):
        row = [str(n)]
        row += [cell(sat, encoding=e, solver=s, n=n) for e, s in best]
        row += [cell(ex, encoding=k[0], solver=k[1], n=n) for k, _ in cols]
        lines.append(" & ".join(row) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}", ""]
    write("tab_exact.tex", "\n".join(lines))


def tab_count() -> None:
    df = pd.read_csv(os.path.join(RESULTS, "count.csv"))
    sat = df[df.solver == "cadical195"]
    lines = ["\\begin{tabular}{@{}rrcrrrrr@{}}", "\\toprule",
             "$n$ & solutions & correct encodings & backtracking & CP-SAT int & CP-SAT 0-1 "
             "& SAT fastest & SAT slowest \\\\", "\\midrule"]
    for n in sorted(df.n.unique()):
        d = sat[sat.n == n]
        done = d[d.status.isin(["SAT", "UNSAT"])]
        correct = int((done["count"] == done["expected"]).sum())
        expected = int(df[df.n == n].expected.iloc[0])
        fast = t(done.time_s.min()) if len(done) else "--"
        slow = t(done.time_s.max()) if len(done) == len(ENC_ORDER) else "TO"
        row = [str(n), num(expected), f"{correct}/{len(ENC_ORDER)}",
               cell(df, encoding="-", solver="backtracking", n=n),
               cell(df, encoding="cp_int", solver="cpsat", n=n),
               cell(df, encoding="cp_bool", solver="cpsat", n=n), fast, slow]
        lines.append(" & ".join(row) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}", ""]
    write("tab_count.tex", "\n".join(lines))


def tab_colalo() -> None:
    df = pd.read_csv(os.path.join(RESULTS, "colalo.csv"))
    ns = [n for n in (64, 128, 256, 512) if n in set(df.n)]
    head = " & ".join(f"\\multicolumn{{2}}{{c}}{{$n={n}$}}" for n in ns)
    rules = "".join(f"\\cmidrule(lr){{{3 + 2 * i}-{4 + 2 * i}}}" for i in range(len(ns)))
    sub = " & ".join(["with & without"] * len(ns))
    lines = ["\\begin{tabular}{@{}ll" + "rr" * len(ns) + "@{}}", "\\toprule",
             f"Encoding & Solver & {head} \\\\", rules, f" & & {sub} \\\\", "\\midrule"]
    for enc in ("sequential", "commander", "product", "binary"):
        for s in ("cadical195", "kissat404"):
            row = [LABEL[enc], SOLVER_SHORT[s]]
            for n in ns:
                row += [cell(df, encoding=enc, solver=s, n=n),
                        cell(df, encoding=f"{enc}-nocolalo", solver=s, n=n)]
            lines.append(" & ".join(row) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}", ""]
    write("tab_colalo.tex", "\n".join(lines))


def main() -> None:
    for fn in (tab_size, tab_sat_summary, tab_sat_detail, tab_exact, tab_count, tab_colalo):
        try:
            fn()
        except FileNotFoundError as exc:
            print("skip", fn.__name__, exc)


if __name__ == "__main__":
    main()
