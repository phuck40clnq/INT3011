"""Build the N-Queens CNF with a pluggable AMO encoding."""
from __future__ import annotations

from nqueens.common import var
from nqueens.encodings.amo import ENCODERS, AmoEncoder


def board_lines(n: int) -> tuple[list[list[int]], list[list[int]], list[list[int]]]:
    """Group the board variables into rows, columns and diagonals.

    Args:
        n: board size.

    Returns:
        (rows, cols, diagonals). `diagonals` holds both directions (cells with
        equal r - c and cells with equal r + c), 2(2n - 1) lines in total,
        including the four corner lines of length 1.
    """
    rows = [[var(r, c, n) for c in range(n)] for r in range(n)]
    cols = [[var(r, c, n) for r in range(n)] for c in range(n)]
    diagonals = []
    for d in range(-(n - 1), n):              # r - c = d
        diagonals.append([var(r, r - d, n) for r in range(n) if 0 <= r - d < n])
    for s in range(2 * n - 1):                # r + c = s
        diagonals.append([var(r, s - r, n) for r in range(n) if 0 <= s - r < n])
    return rows, cols, diagonals


def build_cnf(
    n: int, amo: AmoEncoder, col_alo: bool = True
) -> tuple[list[list[int]], int]:
    """Encode n-queens as CNF.

    Constraints:
        each row:      exactly one queen  (ALO clause + AMO)
        each column:   at most one queen  (+ redundant ALO clause if col_alo)
        each diagonal: at most one queen  (lines of length 1 are skipped)

    Exactly one queen per row already forces n queens; with AMO on columns the
    pigeonhole principle makes every column hold exactly one queen, so the
    column ALO clauses are implied and kept only to help propagation.

    Args:
        n: board size (n >= 1).
        amo: AMO encoder with the interface of `nqueens.encodings.amo`.
        col_alo: add the redundant at-least-one clause for each column.

    Returns:
        (clauses, num_vars); variables 1..n*n are the board, the rest are
        auxiliary variables created by the AMO encoder.
    """
    rows, cols, diagonals = board_lines(n)
    clauses: list[list[int]] = []
    next_var = n * n + 1
    for line in rows:
        clauses.append(list(line))
        amo_clauses, next_var = amo(line, next_var)
        clauses.extend(amo_clauses)
    for line in cols:
        if col_alo:
            clauses.append(list(line))
        amo_clauses, next_var = amo(line, next_var)
        clauses.extend(amo_clauses)
    for line in diagonals:
        if len(line) >= 2:
            amo_clauses, next_var = amo(line, next_var)
            clauses.extend(amo_clauses)
    return clauses, next_var - 1


def encode(n: int, encoding: str, col_alo: bool = True) -> tuple[list[list[int]], int]:
    """Shortcut for `build_cnf` with an encoder looked up by name in ENCODERS."""
    return build_cnf(n, ENCODERS[encoding], col_alo=col_alo)
