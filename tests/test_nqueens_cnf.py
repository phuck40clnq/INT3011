import itertools
import unittest

from nqueens.common import OEIS_A000170, is_valid_solution
from nqueens.encodings.amo import ENCODERS
from nqueens.encodings.nqueens_cnf import board_lines, encode
from nqueens.solvers.pysat_runner import SAT_SOLVERS, count_solutions, solve_cnf


def brute_force(n: int) -> set[tuple[int, ...]]:
    return {p for p in itertools.permutations(range(n)) if is_valid_solution(list(p), n)}


class BoardLinesTest(unittest.TestCase):
    def test_line_counts(self):
        for n in range(1, 9):
            rows, cols, diagonals = board_lines(n)
            self.assertEqual((len(rows), len(cols), len(diagonals)), (n, n, 2 * (2 * n - 1)))
            # every cell lies on exactly one line of each of the four families
            cells = [v for line in diagonals for v in line]
            self.assertEqual(sorted(cells), sorted(list(range(1, n * n + 1)) * 2))


class NQueensCnfTest(unittest.TestCase):
    def test_counts_match_oeis_for_every_encoding(self):
        for name in ENCODERS:
            for n in range(1, 9):
                clauses, _ = encode(n, name)
                self.assertEqual(count_solutions(clauses, n)[0], OEIS_A000170[n], f"{name} n={n}")

    def test_solution_sets_equal_brute_force(self):
        for n in (5, 6, 7):
            expected = brute_force(n)
            for name in ENCODERS:
                self.assertEqual(count_solutions(encode(n, name)[0], n)[1], expected, name)

    def test_column_alo_is_redundant(self):
        for name in ("sequential", "commander", "product", "binary"):
            for n in range(1, 9):
                clauses, _ = encode(n, name, col_alo=False)
                self.assertEqual(count_solutions(clauses, n)[0], OEIS_A000170[n])

    def test_n9_n10_with_own_encodings(self):
        for name in ("sequential", "commander", "product", "binary"):
            for n in (9, 10):
                self.assertEqual(count_solutions(encode(n, name)[0], n)[0], OEIS_A000170[n])

    def test_every_solver_sat_and_unsat(self):
        for solver in SAT_SOLVERS:
            for n, expected in ((3, "UNSAT"), (8, "SAT"), (30, "SAT")):
                clauses, nv = encode(n, "sequential")
                r = solve_cnf(clauses, n, solver, nv)
                self.assertEqual(r.status, expected, f"{solver} n={n}")
                if expected == "SAT":
                    self.assertTrue(is_valid_solution(r.cols, n))


if __name__ == "__main__":
    unittest.main()
