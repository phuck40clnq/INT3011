"""Classic (non-SAT) baselines: bitmask backtracking and an explicit construction."""
from __future__ import annotations


def solve_one_bitmask(n: int) -> list[int] | None:
    """Find one solution by row-by-row backtracking with bitmasks.

    Three integers mark the columns and the two diagonal directions that are
    attacked in the current row. After placing a queen on bit b, the "\\"
    diagonal mask moves one column to the left in the next row and the "/"
    mask one column to the right.

    Args:
        n: board size (n >= 1).

    Returns:
        cols[r] for one solution, or None if no solution exists (n = 2, 3).
    """
    full = (1 << n) - 1
    cols: list[int] = []

    def place(col_mask: int, diag_l: int, diag_r: int) -> bool:
        if col_mask == full:
            return True
        free = full & ~(col_mask | diag_l | diag_r)
        while free:
            bit = free & -free          # lowest free square
            free ^= bit
            cols.append(bit.bit_length() - 1)
            if place(col_mask | bit, ((diag_l | bit) << 1) & full, (diag_r | bit) >> 1):
                return True
            cols.pop()
        return False

    return cols if place(0, 0, 0) else None


def count_all(n: int) -> int:
    """Count all solutions (OEIS A000170) with the same bitmask search.

    Args:
        n: board size (n >= 1).

    Returns:
        The number of distinct placements of n non-attacking queens.
    """
    full = (1 << n) - 1

    def count(col_mask: int, diag_l: int, diag_r: int) -> int:
        if col_mask == full:
            return 1
        total = 0
        free = full & ~(col_mask | diag_l | diag_r)
        while free:
            bit = free & -free
            free ^= bit
            total += count(col_mask | bit, ((diag_l | bit) << 1) & full, (diag_r | bit) >> 1)
        return total

    return count(0, 0, 0)


def explicit_solution(n: int) -> list[int] | None:
    """Closed-form solution for every n >= 4 (Hoffman, Loessi and Moore, 1969).

    Rows are filled with the even columns first and then the odd columns
    (1-based), with two small repairs when n mod 6 is 2 or 3. Runs in O(n).

    Args:
        n: board size.

    Returns:
        cols[r] (0-based), or None for n = 2, 3 which have no solution.
    """
    if n == 1:
        return [0]
    if n in (2, 3):
        return None
    evens = list(range(2, n + 1, 2))
    odds = list(range(1, n + 1, 2))
    if n % 6 == 2:
        # swap 1 and 3, move 5 to the end: 3, 1, 7, 9, ..., 5
        odds = [3, 1] + [x for x in odds if x not in (1, 3, 5)] + [5]
    elif n % 6 == 3:
        # move 2 to the end of the evens, 1 and 3 to the end of the odds
        evens = [x for x in evens if x != 2] + [2]
        odds = [x for x in odds if x not in (1, 3)] + [1, 3]
    return [c - 1 for c in evens + odds]
