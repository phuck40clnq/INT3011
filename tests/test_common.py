import unittest

from nqueens.common import decode_model, is_valid_solution, var


class CommonTest(unittest.TestCase):
    def test_var_is_bijective_and_one_based(self):
        n = 5
        ids = [var(r, c, n) for r in range(n) for c in range(n)]
        self.assertEqual(sorted(ids), list(range(1, n * n + 1)))

    def test_decode_model(self):
        n = 4
        cols = [1, 3, 0, 2]
        model = [var(r, c, n) if cols[r] == c else -var(r, c, n)
                 for r in range(n) for c in range(n)] + [17, -18]   # aux vars ignored
        self.assertEqual(decode_model(model, n), cols)

    def test_decode_rejects_malformed_rows(self):
        n = 4
        self.assertIsNone(decode_model([var(0, 0, n), var(0, 1, n)], n))   # two in row 0
        self.assertIsNone(decode_model([var(0, 0, n)], n))                  # empty rows

    def test_verifier(self):
        self.assertTrue(is_valid_solution([1, 3, 0, 2], 4))
        self.assertTrue(is_valid_solution([0], 1))
        self.assertFalse(is_valid_solution(None, 4))
        self.assertFalse(is_valid_solution([1, 3, 0], 4))        # wrong length
        self.assertFalse(is_valid_solution([1, 3, 0, 4], 4))     # out of range
        self.assertFalse(is_valid_solution([1, 1, 3, 0], 4))     # shared column
        self.assertFalse(is_valid_solution([0, 1, 2, 3], 4))     # shared diagonal r - c
        self.assertFalse(is_valid_solution([3, 2, 1, 0], 4))     # shared anti-diagonal r + c


if __name__ == "__main__":
    unittest.main()
