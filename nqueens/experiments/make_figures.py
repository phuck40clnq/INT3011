"""Draw the report figures from results/*.csv into results/figures/ and report/figures/.

Usage: .venv/bin/python -m nqueens.experiments.make_figures
"""
from __future__ import annotations

import os
import shutil

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

RESULTS = "results"
OUT_DIRS = [os.path.join(RESULTS, "figures"), os.path.join("report", "figures")]

# Validated categorical palette (fixed order, never cycled). One colour per
# encoding family; own encodings are solid lines with circles, PySAT ones
# dashed with squares, so identity never relies on colour alone.
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
FAMILY = {
    "pairwise": 0, "pysat_pairwise": 0,
    "sequential": 1, "pysat_seqcounter": 1,
    "binary": 2, "pysat_bitwise": 2,
    "commander": 3,
    "product": 4,
    "pysat_ladder": 5,
    "pysat_totalizer": 6,
    "pysat_cardnetwrk": 7,
}
ENC_ORDER = list(FAMILY)
LABEL = {
    "pairwise": "pairwise", "sequential": "sequential", "binary": "binary",
    "commander": "commander", "product": "product",
    "pysat_pairwise": "PySAT pairwise", "pysat_seqcounter": "PySAT seqcounter",
    "pysat_bitwise": "PySAT bitwise", "pysat_ladder": "PySAT ladder",
    "pysat_totalizer": "PySAT totalizer", "pysat_cardnetwrk": "PySAT cardnetwrk",
}
SOLVER_LABEL = {"cadical195": "CaDiCaL 1.9.5", "glucose4": "Glucose 4.1",
                "kissat404": "Kissat 4.0.4", "minisat22": "MiniSat 2.2"}
GRID = "#e4e3df"
AXIS = "#8a8984"
TEXT = "#2b2b2a"


def style() -> None:
    plt.rcParams.update({
        "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8,
        "legend.fontsize": 7, "xtick.labelsize": 7, "ytick.labelsize": 7,
        "axes.edgecolor": AXIS, "axes.labelcolor": TEXT, "xtick.color": AXIS,
        "ytick.color": AXIS, "text.color": TEXT, "axes.linewidth": 0.6,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.5, "grid.linestyle": "-",
        "axes.spines.top": False, "axes.spines.right": False,
        "legend.frameon": False, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
        "pdf.fonttype": 42,
    })


def enc_line(name: str) -> dict:
    own = not name.startswith("pysat_")
    return dict(color=PALETTE[FAMILY[name]], linestyle="-" if own else (0, (4, 2)),
                marker="o" if own else "s", markersize=3.6, linewidth=1.3,
                markeredgecolor="white", markeredgewidth=0.6, label=LABEL[name])


def log2_axis(ax, ns) -> None:
    ax.set_xscale("log", base=2)
    ax.set_xticks(ns)
    ax.set_xticklabels([str(n) for n in ns])
    ax.minorticks_off()


def save(fig, name: str) -> None:
    for d in OUT_DIRS:
        os.makedirs(d, exist_ok=True)
    path = os.path.join(OUT_DIRS[0], name)
    fig.savefig(path)
    for d in OUT_DIRS[1:]:
        shutil.copy(path, os.path.join(d, name))
    plt.close(fig)
    print("wrote", path)


def fig_size() -> None:
    df = pd.read_csv(os.path.join(RESULTS, "size.csv"))
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.7))
    for ax, col, title in ((axes[0], "num_clauses", "Clauses"), (axes[1], "num_vars", "Variables")):
        for enc in ENC_ORDER:
            d = df[df.encoding == enc].sort_values("n")
            ax.plot(d.n, d[col], **enc_line(enc))
        ax.set_yscale("log")
        log2_axis(ax, sorted(df.n.unique()))
        ax.set_xlabel("board size n")
        ax.set_title(title, loc="left")
    axes[0].set_ylabel("count (log scale)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=6, bbox_to_anchor=(0.5, 0.0))
    save(fig, "fig_size.pdf")


def fig_sat_time(limit: float) -> None:
    df = pd.read_csv(os.path.join(RESULTS, "sat.csv"))
    ok = df[df.status == "SAT"]
    ns = sorted(n for n in df.n.unique() if n >= 8)
    fig, axes = plt.subplots(2, 2, figsize=(6.6, 4.9), sharex=True, sharey=True)
    for ax, solver in zip(axes.flat, SOLVER_LABEL):
        for enc in ENC_ORDER:
            d = ok[(ok.solver == solver) & (ok.encoding == enc)].sort_values("n")
            if len(d):
                ax.plot(d.n, d.time_s, **enc_line(enc))
        ax.axhline(limit, color=AXIS, linewidth=0.7)
        ax.text(ns[0], limit * 1.12, f"time limit {limit:g} s", fontsize=6.5, color=AXIS)
        ax.set_yscale("log")
        log2_axis(ax, ns)
        ax.set_title(SOLVER_LABEL[solver], loc="left")
    for ax in axes[1]:
        ax.set_xlabel("board size n")
    for ax in axes[:, 0]:
        ax.set_ylabel("solver time (s, log)")
    handles, labels = [], []
    for ax in axes.flat:
        for h, l in zip(*ax.get_legend_handles_labels()):
            if l not in labels:
                handles.append(h)
                labels.append(l)
    order = [labels.index(LABEL[e]) for e in ENC_ORDER if LABEL[e] in labels]
    fig.legend([handles[i] for i in order], [labels[i] for i in order],
               loc="lower center", ncol=6, bbox_to_anchor=(0.5, -0.06))
    save(fig, "fig_sat_time.pdf")


def sat_runs() -> pd.DataFrame:
    """Rows of `sat.csv` plus the extra board sizes of `exactsat.csv` (if present)."""
    frames = [pd.read_csv(os.path.join(RESULTS, "sat.csv"))]
    extra = os.path.join(RESULTS, "exactsat.csv")
    if os.path.exists(extra):
        frames.append(pd.read_csv(extra))
    return pd.concat(frames).drop_duplicates(["n", "encoding", "solver"], keep="first")


def best_sat_configs(k: int = 2) -> list[tuple[str, str]]:
    """Configurations ranked by largest n solved, then by summed time on common n."""
    df = pd.read_csv(os.path.join(RESULTS, "sat.csv"))
    ok = df[df.status == "SAT"]
    stats = []
    for (enc, solver), d in ok.groupby(["encoding", "solver"]):
        nmax = d.n.max()
        stats.append((-nmax, d[d.n <= 256].time_s.sum(), enc, solver))
    stats.sort()
    return [(enc, solver) for _, _, enc, solver in stats[:k]]


def fig_exact(limit: float) -> None:
    ex = pd.read_csv(os.path.join(RESULTS, "exact.csv"))
    sat = sat_runs()
    series = []
    for enc, solver in best_sat_configs(2):
        d = sat[(sat.encoding == enc) & (sat.solver == solver) & (sat.status == "SAT")]
        series.append((f"SAT: {LABEL[enc]} + {SOLVER_LABEL[solver].split()[0]}", d))
    names = {("cp_int", "cpsat"): "CP-SAT (integer model)",
             ("cp_bool", "cpsat"): "CP-SAT (0-1 model)",
             ("mip01", "gurobi"): "Gurobi MIP",
             ("mip01", "cplex"): "CPLEX MIP",
             ("cp_int", "cpoptimizer"): "CPLEX CP Optimizer"}
    for key, label in names.items():
        d = ex[(ex.encoding == key[0]) & (ex.solver == key[1]) & (ex.status == "SAT")]
        if len(d):
            series.append((label, d))
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    markers = ["o", "s", "D", "^", "v", "P", "X"]
    for i, (label, d) in enumerate(series):
        d = d.sort_values("n")
        ax.plot(d.n, d.time_s, color=PALETTE[i], marker=markers[i], markersize=3.8,
                linewidth=1.3, markeredgecolor="white", markeredgewidth=0.6, label=label)
    ax.axhline(limit, color=AXIS, linewidth=0.7)
    ax.text(1000, limit * 1.12, f"time limit {limit:g} s", fontsize=6.5, color=AXIS, ha="right")
    ax.axvline(31, color=GRID, linewidth=0.8)
    ax.axvline(44, color=GRID, linewidth=0.8)
    ax.text(31, 1.5e-4, " CPLEX\n limit", fontsize=6, color=AXIS, va="bottom")
    ax.text(44, 1.5e-4, " Gurobi\n limit", fontsize=6, color=AXIS, va="bottom")
    ax.set_xscale("log", base=2)
    ticks = [8, 16, 32, 64, 128, 256, 512, 1000]
    ax.set_xticks(ticks)
    ax.set_xticklabels([str(t) for t in ticks])
    ax.minorticks_off()
    ax.set_yscale("log")
    ax.set_xlabel("board size n")
    ax.set_ylabel("solver time (s, log)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=3)
    save(fig, "fig_exact.pdf")


def fig_count(limit: float) -> None:
    df = pd.read_csv(os.path.join(RESULTS, "count.csv"))
    df = df[df.n >= 6]          # below n = 6 backtracking takes < 0.1 ms (rounded to 0 in the CSV)
    series = [("-", "backtracking", "bitmask backtracking"),
              ("cp_int", "cpsat", "CP-SAT (integer model)"),
              ("cp_bool", "cpsat", "CP-SAT (0-1 model)"),
              ("pairwise", "cadical195", "SAT: pairwise"),
              ("sequential", "cadical195", "SAT: sequential"),
              ("binary", "cadical195", "SAT: binary"),
              ("commander", "cadical195", "SAT: commander"),
              ("product", "cadical195", "SAT: product")]
    fig, ax = plt.subplots(figsize=(6.6, 2.8))
    markers = ["o", "s", "D", "^", "v", "P", "X", "h"]
    for i, (enc, solver, label) in enumerate(series):
        d = df[(df.encoding == enc) & (df.solver == solver) & df.status.isin(["SAT", "UNSAT"])]
        d = d.sort_values("n")
        if len(d):
            ax.plot(d.n, d.time_s, color=PALETTE[i], marker=markers[i], markersize=3.8,
                    linewidth=1.3, markeredgecolor="white", markeredgewidth=0.6, label=label)
    ax.set_yscale("log")
    ax.set_xticks(range(6, 13))
    ax.set_xlabel("board size n")
    ax.set_ylabel("time to enumerate all solutions (s, log)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=3)
    save(fig, "fig_count.pdf")


def main() -> None:
    style()
    limit = 60.0
    for fn in (fig_size, fig_sat_time, fig_exact, fig_count):
        try:
            fn(limit) if fn is not fig_size else fn()
        except FileNotFoundError as exc:
            print("skip", fn.__name__, exc)


if __name__ == "__main__":
    main()
