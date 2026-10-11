"""Shared helpers: variable mapping, model decoding, solution verification."""
from __future__ import annotations

from dataclasses import dataclass

# Number of distinct solutions of the n-queens problem (OEIS A000170).
OEIS_A000170: dict[int, int] = {
    1: 1, 2: 0, 3: 0, 4: 2, 5: 10, 6: 4, 7: 40, 8: 92,
    9: 352, 10: 724, 11: 2680, 12: 14200, 13: 73712, 14: 365596,
}

STATUSES = ("SAT", "UNSAT", "TIMEOUT", "ERROR")


def var(r: int, c: int, n: int) -> int:
    """DIMACS variable (1-based) meaning 'a queen sits on square (r, c)'.

    Args:
        r: row index, 0 <= r < n.
        c: column index, 0 <= c < n.
        n: board size.

    Returns:
        r * n + c + 1, so the board uses variables 1..n*n.
    """
    return r * n + c + 1


def decode_model(model: list[int], n: int) -> list[int] | None:
    """Turn a SAT model (signed literals) into the column vector cols[r].

    Only the n*n board variables are read; auxiliary variables are ignored.

    Args:
        model: list of signed literals returned by a SAT solver.
        n: board size.

    Returns:
        cols with cols[r] = column of the queen in row r, or None when some
        row holds zero or several queens (the model is then malformed).
    """
    cols = [-1] * n
    for lit in model:
        if 0 < lit <= n * n:
            r, c = divmod(lit - 1, n)
            if cols[r] != -1:
                return None
            cols[r] = c
    if -1 in cols:
        return None
    return cols


def is_valid_solution(cols: list[int] | None, n: int) -> bool:
    """Return True iff `cols` places n mutually non-attacking queens.

    cols[r] is the column of the queen in row r (0-based). Two queens attack
    each other when they share a column, a main diagonal (same r - c) or an
    anti-diagonal (same r + c); rows are distinct by construction.

    Args:
        cols: candidate solution, or None.
        n: board size.

    Returns:
        True for a correct n-queens placement, False otherwise.
    """
    if cols is None or len(cols) != n:
        return False
    if any(not (0 <= c < n) for c in cols):
        return False
    if len(set(cols)) != n:
        return False
    if len({r - c for r, c in enumerate(cols)}) != n:
        return False
    if len({r + c for r, c in enumerate(cols)}) != n:
        return False
    return True


@dataclass
class SolveResult:
    """Outcome of one solver run.

    Attributes:
        status: one of "SAT", "UNSAT", "TIMEOUT", "ERROR".
        cols: decoded solution (cols[r]) when status == "SAT", else None.
        time_s: wall-clock time spent inside the solver (load + search).
        num_vars: number of variables of the model given to the solver.
        num_clauses: number of clauses (SAT) or constraints (MIP/CP).
        build_time_s: time spent building the encoding / model in Python.
        note: free-form remark (error message, license limit, ...).
    """

    status: str
    cols: list[int] | None
    time_s: float
    num_vars: int = 0
    num_clauses: int = 0
    build_time_s: float = 0.0
    note: str = ""
