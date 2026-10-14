import unittest

from nqueens.common import OEIS_A000170, is_valid_solution
from nqueens.exact import mip_size
from nqueens.exact.cplex_cp import find_cpoptimizer, solve_cplex_cp
from nqueens.exact.cplex_mip import solve_cplex_mip
from nqueens.exact.cpsat import count_cpsat, solve_cpsat_bool, solve_cpsat_int
from nqueens.exact.gurobi_mip import solve_gurobi


class ExactSolversTest(unittest.TestCase):
    def check(self, fn):
        self.assertEqual(fn(3, time_limit=30).status, "UNSAT")
        for n in (1, 8, 20):
            r = fn(n, time_limit=30)
            self.assertEqual(r.status, "SAT", f"n={n}")
            self.assertTrue(is_valid_solution(r.cols, n))

    def test_cpsat_int(self):
        self.check(solve_cpsat_int)

    def test_cpsat_bool(self):
        self.check(solve_cpsat_bool)

    def test_gurobi(self):
        self.check(solve_gurobi)
        self.assertEqual(solve_gurobi(45).status, "ERROR")       # license limit

    def test_cplex_mip(self):
        self.check(solve_cplex_mip)
        self.assertEqual(solve_cplex_mip(32).status, "ERROR")    # license limit

    @unittest.skipUnless(find_cpoptimizer(), "cpoptimizer executable not installed")
    def test_cplex_cp(self):
        self.check(solve_cplex_cp)

    def test_mip_size(self):
        for n in range(2, 30):
            self.assertEqual(mip_size(n), (n * n, 6 * n - 6))

    def test_cpsat_counting(self):
        for kind in ("int", "bool"):
            for n in (1, 3, 6, 8):
                status, count, _ = count_cpsat(n, kind)
                self.assertEqual(count, OEIS_A000170[n], f"{kind} n={n}")


if __name__ == "__main__":
    unittest.main()
