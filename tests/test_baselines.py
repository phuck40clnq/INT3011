import unittest

from nqueens.baselines.backtracking import count_all, explicit_solution, solve_one_bitmask
from nqueens.common import OEIS_A000170, is_valid_solution


class BaselineTest(unittest.TestCase):
    def test_counts_match_oeis(self):
        for n in range(1, 11):
            self.assertEqual(count_all(n), OEIS_A000170[n], f"n={n}")

    def test_backtracking_solutions_are_valid(self):
        for n in [1] + list(range(4, 21)):
            self.assertTrue(is_valid_solution(solve_one_bitmask(n), n), f"n={n}")

    def test_unsat_cases(self):
        for n in (2, 3):
            self.assertIsNone(solve_one_bitmask(n))
            self.assertIsNone(explicit_solution(n))

    def test_explicit_construction(self):
        for n in [1] + list(range(4, 400)):
            self.assertTrue(is_valid_solution(explicit_solution(n), n), f"n={n}")


if __name__ == "__main__":
    unittest.main()
