# N-Queens via SAT encodings — comparison with CP-SAT, Gurobi and CPLEX

Assignment 1, *Modern Issues in Computer Science* (Các vấn đề hiện đại KHMT), Semester I 2026–2027,
VNU University of Engineering and Technology. Author: Nguyen Cong Phuc (24021598).

The N-Queens problem is encoded into CNF with eleven at-most-one (AMO) encodings:
five implemented here (pairwise, sequential counter, binary, commander, product) and six
from `pysat.card` (pairwise, seqcounter, bitwise, ladder, totalizer, cardnetwrk). The CNFs are
solved with CaDiCaL 1.9.5, Glucose 4.1, Kissat 4.0.4 and MiniSat 2.2 through PySAT, and compared
with OR-Tools CP-SAT (integer and 0-1 models), Gurobi (MIP), CPLEX (MIP) and CPLEX CP Optimizer.

## Layout

```
nqueens/common.py                 variable map, model decoding, solution verifier
nqueens/baselines/backtracking.py bitmask backtracking, closed-form construction
nqueens/encodings/amo.py          AMO encoders (own + PySAT wrappers), common interface
nqueens/encodings/nqueens_cnf.py  N-Queens CNF builder
nqueens/solvers/pysat_runner.py   solve / enumerate with PySAT solvers
nqueens/exact/                    CP-SAT, Gurobi, CPLEX MIP, CPLEX CP models
nqueens/experiments/              benchmark runner, figures, LaTeX tables
tests/                            unit tests (encoding semantics, OEIS counts, solvers)
results/                          CSV results, logs, figures, environment.txt
report/                           LaTeX report (Elsevier cas-sc)
docs/LEARN.md                     detailed walkthrough of the code (Vietnamese)
```

## Reproduce

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -t .

python -m nqueens.experiments.run_benchmark exact    --time-limit 60
python -m nqueens.experiments.run_benchmark sat      --time-limit 60
python -m nqueens.experiments.run_benchmark exactsat --time-limit 60
python -m nqueens.experiments.run_benchmark count    --time-limit 60
python -m nqueens.experiments.run_benchmark colalo   --time-limit 60
python -m nqueens.experiments.run_benchmark size
python -m nqueens.experiments.make_figures
python -m nqueens.experiments.make_tables
```

Each run executes in a separate process with a 60 s limit on the solving phase; for each
configuration, larger boards are skipped after the first timeout. Gurobi and CPLEX are the
size-limited pip editions (Gurobi ≤ 2000 variables, i.e. n ≤ 44; CPLEX ≤ 1000, i.e. n ≤ 31).
CPLEX CP Optimizer needs the `cpoptimizer` executable from IBM ILOG CPLEX Optimization Studio
(set `CPOPTIMIZER_PATH` if it is not on `PATH`).

The report is compiled with `tectonic report/main.tex` or on Overleaf (upload the `report/` folder).
