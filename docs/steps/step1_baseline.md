# Bước 1: Baseline và bộ kiểm chứng

Chép các stub dưới đây sang `nqueens/` rồi tự điền thân hàm. Không có lời giải ở đây.

## Kiến thức cần nắm
- Một nghiệm là hoán vị: hàng r có đúng 1 hậu ở cột `cols[r]`, nên chỉ còn phải xử lý cột và đường chéo
- Hai ô cùng đường chéo ⟺ cùng `r−c` hoặc cùng `r+c`
- Bitmask: 3 số nguyên đánh dấu cột và 2 chiều đường chéo đang bị tấn công; ô còn trống = bit 0 ở cả ba

## `nqueens/common.py`

```python
from __future__ import annotations
from dataclasses import dataclass


def is_valid_solution(cols: list[int], n: int) -> bool:
    """Return True iff `cols` places n non-attacking queens on an n x n board.

    cols[r] is the column of the queen in row r (0-based).
    Must reject: wrong length, out-of-range columns, shared column, shared diagonal.
    """
    raise NotImplementedError


def var(r: int, c: int, n: int) -> int:
    """DIMACS variable (1-based) meaning 'a queen sits on (r, c)'."""
    raise NotImplementedError


def decode_model(model: list[int], n: int) -> list[int]:
    """Turn a SAT model (signed ints) into cols[r]. Return -1 for a row with no queen."""
    raise NotImplementedError


@dataclass
class SolveResult:
    status: str            # "SAT" | "UNSAT" | "TIMEOUT" | "ERROR"
    cols: list[int] | None
    time_s: float
    num_vars: int = 0
    num_clauses: int = 0
```

## `nqueens/baselines/backtracking.py`

```python
def solve_one_set(n: int) -> list[int] | None:
    """Backtracking row by row, tracking used columns / diagonals with sets.

    Return one solution as cols[r], or None if none exists.
    """
    raise NotImplementedError


def solve_one_bitmask(n: int) -> list[int] | None:
    """Same search, but column and both diagonal sets are int bitmasks.

    Hint: the lowest set bit of `free` is `free & -free`.
    """
    raise NotImplementedError


def count_all(n: int) -> int:
    """Number of distinct solutions (OEIS A000170). Use the bitmask search."""
    raise NotImplementedError
```

## `tests/test_baseline.py` (khung)

```python
import unittest

KNOWN = {1: 1, 2: 0, 3: 0, 4: 2, 5: 10, 6: 4, 7: 40, 8: 92, 9: 352, 10: 724}


class BaselineTest(unittest.TestCase):
    def test_counts_match_oeis(self):
        """For every n in KNOWN, count_all(n) must equal KNOWN[n]."""
        raise NotImplementedError

    def test_solutions_are_valid(self):
        """solve_one_* returns a solution accepted by is_valid_solution (n = 4, 8, 12, 20)."""
        raise NotImplementedError

    def test_unsat_cases(self):
        """n = 2 and n = 3 return None."""
        raise NotImplementedError

    def test_verifier_rejects_bad_input(self):
        """Wrong length, repeated column, shared diagonal, out-of-range value."""
        raise NotImplementedError
```

## Bài đo (tự làm, ghi vào nhật ký trong ROADMAP.md)
1. Thời gian `solve_one_set` và `solve_one_bitmask` với n = 8, 12, 16, 20, 24
2. Thời gian `count_all` với n = 8..13
3. Quan sát: tốc độ tăng theo n có dạng gì?

## Gợi ý theo thang (đọc từng mức khi kẹt)
1. Mask đường chéo `\` và `/` thay đổi thế nào khi chuyển sang hàng kế tiếp?
2. Sau khi đặt hậu ở bit `b`: cột thêm `b`, một mask dịch trái 1, mask kia dịch phải 1.
3. Cần cắt mask bằng `(1 << n) − 1` sau khi dịch trái để không tràn ra ngoài bàn cờ.
