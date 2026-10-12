"""Semantic tests of every AMO encoder.

For an AMO encoding F(x, aux) of lits x, correctness means: an assignment of
x extends to a model of F (some values of aux) iff at most one x is true.
We check this exhaustively for small k with solver assumptions.
"""
import itertools
import math
import random
import unittest

from pysat.solvers import Solver

from nqueens.encodings.amo import ENCODERS, binary, pairwise, sequential


def extendable(clauses: list[list[int]], assignment: list[int]) -> bool:
    with Solver(name="minisat22", bootstrap_with=clauses) as s:
        return s.solve(assumptions=assignment)


class AmoSemanticsTest(unittest.TestCase):
    def check(self, name, lits, next_var, assignments):
        clauses, new_next = ENCODERS[name](lits, next_var)
        self.assertGreaterEqual(new_next, next_var)
        used = {abs(l) for cl in clauses for l in cl}
        aux = used - {abs(l) for l in lits}
        self.assertTrue(all(next_var <= v < new_next for v in aux),
                        f"{name}: aux ids outside [{next_var}, {new_next})")
        for values in assignments:
            assumption = [l if b else -l for l, b in zip(lits, values)]
            expected = sum(values) <= 1
            self.assertEqual(extendable(clauses, assumption), expected,
                             f"{name} k={len(lits)} {values}")

    def test_exhaustive_small_k(self):
        for name in ENCODERS:
            for k in range(0, 9):
                lits = list(range(1, k + 1))
                self.check(name, lits, k + 1, itertools.product([0, 1], repeat=k))

    def test_offset_and_negative_literals(self):
        lits = [3, -5, 7, -11, 13, 2]
        for name in ENCODERS:
            self.check(name, lits, 50, itertools.product([0, 1], repeat=len(lits)))

    def test_larger_k_sampled(self):
        rng = random.Random(0)
        for name in ENCODERS:
            for k in (17, 26, 37):
                lits = list(range(1, k + 1))
                samples = [[0] * k]
                samples += [[int(i == j) for i in range(k)] for j in range(k)]
                for _ in range(30):
                    a, b = rng.sample(range(k), 2)
                    samples.append([int(i in (a, b)) for i in range(k)])
                self.check(name, lits, k + 1, samples)


class AmoSizeTest(unittest.TestCase):
    def test_formulas(self):
        for k in range(2, 40):
            lits = list(range(1, k + 1))
            cl, nv = pairwise(lits, k + 1)
            self.assertEqual((len(cl), nv - k - 1), (k * (k - 1) // 2, 0))
            cl, nv = sequential(lits, k + 1)
            self.assertEqual((len(cl), nv - k - 1), (3 * k - 4, k - 1))
            m = math.ceil(math.log2(k))
            cl, nv = binary(lits, k + 1)
            self.assertEqual((len(cl), nv - k - 1), (k * m, m))


if __name__ == "__main__":
    unittest.main()
