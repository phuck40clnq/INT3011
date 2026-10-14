"""Exact non-SAT baselines: CP-SAT, Gurobi MIP, CPLEX MIP, CPLEX CP Optimizer."""
from __future__ import annotations

from nqueens.encodings.nqueens_cnf import board_lines


def cell_lines(n: int) -> tuple[list[list[int]], list[list[int]], list[list[int]]]:
    """Rows, columns and diagonals (length >= 2) as 0-based cell indices r*n + c.

    Shared by the 0-1 models so that MIP, CP-SAT (Boolean) and the CNF use
    exactly the same lines.
    """
    rows, cols, diagonals = board_lines(n)
    to_idx = lambda line: [v - 1 for v in line]    # DIMACS var -> cell index
    return (
        [to_idx(line) for line in rows],
        [to_idx(line) for line in cols],
        [to_idx(line) for line in diagonals if len(line) >= 2],
    )


def mip_size(n: int) -> tuple[int, int]:
    """(variables, constraints) of the 0-1 model: n^2 and 6n - 6 (n >= 2)."""
    rows, cols, diagonals = cell_lines(n)
    return n * n, len(rows) + len(cols) + len(diagonals)
