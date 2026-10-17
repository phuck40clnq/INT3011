# Đọc hiểu dự án N-Queens SAT (BTL1)

Tài liệu này giải thích **toàn bộ code** trong `nqueens/` và `tests/`: mỗi file làm gì, vì sao viết như vậy, kèm ví dụ nhỏ n=4 để bạn tự kiểm tra bằng tay. Đọc theo thứ tự từ mục 1 đến mục 9. Mục 10 là bộ câu hỏi vấn đáp để tự kiểm tra.

---

## 0. Bản đồ code

```
nqueens/
├── common.py               var(), decode_model(), is_valid_solution(), SolveResult, OEIS_A000170
├── baselines/backtracking.py   backtracking bitmask (1 nghiệm / đếm nghiệm), công thức tường minh O(n)
├── encodings/
│   ├── amo.py              5 AMO tự viết + 6 AMO bọc từ pysat.card, cùng một giao diện
│   └── nqueens_cnf.py      board_lines() + build_cnf(): ghép ALO/AMO thành CNF N-Queens
├── solvers/pysat_runner.py solve_cnf() (1 nghiệm), count_solutions() (liệt kê bằng blocking clause)
├── exact/                  các phương pháp chính xác khác để so sánh
│   ├── cpsat.py            OR-Tools CP-SAT: mô hình nguyên (AllDifferent) và mô hình 0-1
│   ├── gurobi_mip.py       Gurobi MIP 0-1
│   ├── cplex_mip.py        CPLEX MIP 0-1 (docplex.mp)
│   └── cplex_cp.py         CPLEX CP Optimizer (docplex.cp), cần file thực thi cpoptimizer
└── experiments/
    ├── run_benchmark.py    chạy lưới (n, encoding, solver), ghi results/<exp>.csv
    ├── worker.py           tiến trình con chạy 1 cấu hình, gửi kết quả qua pipe
    ├── make_figures.py     vẽ hình cho báo cáo từ CSV
    └── make_tables.py      sinh bảng LaTeX cho báo cáo từ CSV
tests/                      25 unittest (chạy: .venv/bin/python -m unittest discover -s tests -t .)
```

Luồng dữ liệu:

```
n, tên encoding ──► build_cnf ──► CNF (list[list[int]]) ──► PySAT solver ──► model
                                                                       │
                                     is_valid_solution ◄── decode_model ◄┘
                                             │
                            results/*.csv ──► make_figures / make_tables ──► report/
```

---

## 1. Mô hình hóa N-Queens thành SAT

### 1.1 Biến
Mỗi ô (r, c) có một biến Boolean `x[r][c]` mang nghĩa "có hậu ở ô (r, c)". Theo chuẩn DIMACS, biến là số nguyên dương bắt đầu từ 1:

```
var(r, c, n) = r*n + c + 1          (common.py)
```

Với n=4, bàn cờ dùng các biến 1..16:

```
       c=0  c=1  c=2  c=3
r=0     1    2    3    4
r=1     5    6    7    8
r=2     9   10   11   12
r=3    13   14   15   16
```

Literal dương `6` nghĩa là "có hậu ở (1,1)", literal âm `-6` nghĩa là "không có hậu ở (1,1)". Một mệnh đề (clause) là một list literal nối với nhau bằng OR. CNF là list các mệnh đề nối với nhau bằng AND.

### 1.2 Ràng buộc (`nqueens_cnf.build_cnf`)

| Đường | Ràng buộc | CNF |
|---|---|---|
| mỗi hàng | đúng 1 hậu | 1 mệnh đề ALO `(x1 ∨ x2 ∨ x3 ∨ x4)` + AMO |
| mỗi cột | ≤ 1 hậu (+ ALO dư thừa) | AMO (+ ALO) |
| mỗi đường chéo | ≤ 1 hậu | AMO, bỏ qua đường chéo độ dài 1 |

**ALO** (at-least-one) chỉ là một mệnh đề. **AMO** (at-most-one) mới là phần khó, vì có nhiều cách mã hóa. Đây là trọng tâm của bài.

**Đường chéo:** hai ô cùng đường chéo chính khi `r − c` bằng nhau, cùng đường chéo phụ khi `r + c` bằng nhau. Mỗi chiều có `2n − 1` đường, tổng cộng `2(2n − 1)`. Với n=4, `board_lines` trả về (theo số biến):

```
r-c const: [4] [3,8] [2,7,12] [1,6,11,16] [5,10,15] [9,14] [13]
r+c const: [1] [2,5] [3,6,9] [4,7,10,13] [8,11,14] [12,15] [16]
```

Bốn đường độ dài 1 ở bốn góc không cần ràng buộc gì (1 ô thì không thể có 2 hậu), nên code bỏ qua `len(line) < 2`.

**Vì sao ALO cho cột là dư thừa?** Mỗi hàng có đúng 1 hậu, nên tổng cộng có đúng n hậu. Mỗi cột có tối đa 1 hậu, và có n cột. Theo nguyên lý chuồng bồ câu, n hậu nằm trong n cột với mỗi cột ≤ 1 thì mỗi cột phải có đúng 1. Ta vẫn thêm ALO cột (`col_alo=True`) vì mệnh đề dư thừa có thể giúp lan truyền. Thí nghiệm `colalo` đo xem việc này có giúp thật hay không. Test `test_column_alo_is_redundant` kiểm chứng rằng bỏ ALO cột vẫn cho đúng số nghiệm.

---

## 2. Năm AMO encoding tự viết (`encodings/amo.py`)

Mọi encoder có **cùng giao diện**:

```python
encoder(lits: list[int], next_var: int) -> (clauses, new_next_var)
```

`next_var` là ID biến tự do đầu tiên. Encoder nào cần biến phụ thì lấy từ `next_var` trở lên rồi trả về `next_var` mới, nhờ vậy các biến phụ không bao giờ trùng nhau. `build_cnf` bắt đầu với `next_var = n*n + 1` (ngay sau các biến bàn cờ).

Ký hiệu: k = số literal trong nhóm, ví dụ k=4 với x1..x4 và biến phụ bắt đầu từ 17.

### 2.1 Pairwise (naive)
Ý tưởng: cấm từng cặp: `(¬xi ∨ ¬xj)` với mọi i<j.

```
k=4: [-1,-2] [-1,-3] [-1,-4] [-2,-3] [-2,-4] [-3,-4]
```

* Mệnh đề: k(k−1)/2 = O(k²); biến phụ: 0.
* Với N-Queens: có 2n đường (hàng, cột) dài n, mỗi đường sinh O(n²) mệnh đề, cộng thêm các đường chéo, tổng cộng **Θ(n³)** mệnh đề. n=128 đã có 3,46 triệu mệnh đề, vì vậy thực nghiệm dừng pairwise ở n=128 (giới hạn RAM 8 GB).

### 2.2 Sequential counter (Sinz 2005)
Ý tưởng: biến phụ `s_i` = "có ít nhất một trong x1..xi đúng" (tức OR của tiền tố). Nếu tiền tố đã có một literal đúng thì literal tiếp theo phải sai.

```
x1 → s1                                  [-1, 17]
x2 → s2 ;  s1 → s2 ;  x2 → ¬s1           [-2, 18] [-17, 18] [-2, -17]
x3 → s3 ;  s2 → s3 ;  x3 → ¬s2           [-3, 19] [-18, 19] [-3, -18]
x4 → ¬s3                                 [-4, -19]
```

* Mệnh đề: 3k − 4; biến phụ: k − 1. Cả hai đều **O(k)**, nên cả bài toán chỉ còn **Θ(n²)**.
* Tự kiểm tra: đặt x1 = x3 = 1. Từ x1 suy ra s1, từ s1 suy ra s2, rồi `x3 → ¬s2` mâu thuẫn. Đúng như mong đợi.

### 2.3 Binary / bitwise (Frisch et al. 2005)
Ý tưởng: đánh số literal 0..k−1 và dùng m = ⌈log₂k⌉ bit phụ b0..b(m−1). Nếu xi đúng thì các bit phải "viết ra" số i. Hai literal khác nhau cần hai mẫu bit khác nhau, nên không thể cùng đúng.

```
k=4, m=2 (b0=17, b1=18):
x1 (i=0=00): [-1,-17] [-1,-18]
x2 (i=1=01): [-2, 17] [-2,-18]
x3 (i=2=10): [-3,-17] [-3, 18]
x4 (i=3=11): [-4, 17] [-4, 18]
```

* Mệnh đề: k·⌈log₂k⌉; biến phụ: ⌈log₂k⌉ (ít biến phụ nhất).
* Nhược điểm: số mệnh đề O(k log k) lớn hơn sequential. Ngoài ra, các bit phụ không mang nghĩa trực tiếp, nên solver có thể ra quyết định trên bit mà không suy ra được gì về x.

### 2.4 Commander (Klieber & Kwon 2007)
Ý tưởng: chia literal thành các nhóm 3. Mỗi nhóm có một "chỉ huy" c với c ↔ OR(nhóm). Trong nhóm dùng pairwise. Sau đó đệ quy AMO trên các chỉ huy.

```
k=4: nhóm {1,2,3} có chỉ huy 17, nhóm {4} có 1 phần tử nên dùng chính x4 làm chỉ huy
pairwise trong nhóm:   [-1,-2] [-1,-3] [-2,-3]
x → c:                 [-1,17] [-2,17] [-3,17]
c → OR(nhóm):          [-17, 1, 2, 3]
AMO trên {17, 4}:      [-17,-4]
```

* Mệnh đề ~3,5k; biến phụ ~k/2 (với nhóm 3). Kích thước O(k).
* Một chi tiết tối ưu trong code: nhóm chỉ có 1 literal thì dùng chính literal đó làm chỉ huy, không tạo biến mới.

### 2.5 Product (Chen 2010)
Ý tưởng: xếp k literal lên lưới p×q (≈√k × √k). Literal ở ô (i, j) kéo theo "hàng" u_i và "cột" v_j. Sau đó đặt AMO(u) và AMO(v), mã hóa đệ quy bằng chính product. Hai literal đúng thì hoặc khác hàng (vi phạm AMO(u)), hoặc khác cột (vi phạm AMO(v)).

```
k=9, lưới 3×3, u = {u0,u1,u2}, v = {v0,v1,v2}
x_idx → u[idx // 3],  x_idx → v[idx % 3]      (18 mệnh đề)
AMO(u), AMO(v) bằng pairwise (vì 3 ≤ base=4)  (3 + 3 mệnh đề)
Tổng: 24 mệnh đề, 6 biến phụ (pairwise cần 36 mệnh đề)
```

* Mệnh đề 2k + 4√k + O(k^¼), biến phụ ~2√k.
* Khi k ≤ 4 (`base`), code dùng pairwise vì với k nhỏ pairwise còn gọn hơn. Đây là lý do với n=4, product cho đúng 84 mệnh đề như pairwise.

### 2.6 Bảng tóm tắt (k literal)

| Encoding | Mệnh đề | Biến phụ | N-Queens (cả bài) |
|---|---|---|---|
| pairwise | k(k−1)/2 | 0 | Θ(n³) mệnh đề |
| sequential | 3k − 4 | k − 1 | Θ(n²) |
| binary | k⌈log₂k⌉ | ⌈log₂k⌉ | Θ(n² log n) mệnh đề |
| commander | ~3,5k | ~k/2 | Θ(n²) |
| product | 2k + 4√k + … | ~2√k | Θ(n²) |

Với n=4, kích thước toàn bài (đo bằng code): pairwise 16 biến/84 mệnh đề; sequential 58/116; binary 48/120; commander 26/104; product 16/84.

### 2.7 Sức mạnh lan truyền (unit propagation)
Cả 5 encoding đều có tính chất: **khi một xi được gán đúng, unit propagation suy ra mọi xj còn lại phải sai**. Ví dụ:
* sequential: x2 đúng ⇒ s2 đúng ⇒ s3 đúng ⇒ x4 sai (qua `x4 → ¬s3`). Chiều ngược lại, x2 đúng ⇒ ¬s1 ⇒ x1 sai (qua `x1 → s1`).
* binary: x1 đúng ⇒ b0 = b1 = 0 ⇒ mọi xj có ít nhất một bit khác 0 đều bị mệnh đề `(¬xj ∨ b)` ép sai.

Vì vậy, khác biệt về tốc độ giữa các encoding chủ yếu đến từ **kích thước** (số mệnh đề, số biến), **cấu trúc biến phụ** (solver có thể quyết định trên biến phụ, và mệnh đề học được có thể chứa biến phụ, ngắn hơn) và **heuristic** của từng solver. Lý thuyết không dự đoán trước được hoàn toàn, nên cần thực nghiệm.

### 2.8 PySAT encodings (`PYSAT_ENCODERS`)
`CardEnc.atmost(lits, bound=1, top_id=next_var-1, encoding=EncType.X)` trả về một đối tượng CNF. `top_id` báo cho PySAT biết ID lớn nhất đã dùng, để biến phụ của nó bắt đầu từ `top_id+1`. Ta bọc lại để có cùng giao diện. Có 6 encoding: `pairwise`, `seqcounter`, `bitwise`, `ladder`, `totalizer`, `cardnetwrk`. PySAT **không có** commander và product, nên phải tự viết (đây là phần đóng góp riêng).

So sánh kích thước với n=8: `sequential` của ta có 274 biến/604 mệnh đề, `pysat_seqcounter` có 270/600. Chênh nhau 4 biến/4 mệnh đề, tương ứng 4 đường chéo dài 2: với k=2, PySAT chỉ sinh 1 mệnh đề pairwise, còn bản của ta sinh đúng công thức 3k−4 = 2 mệnh đề + 1 biến phụ. Tập nghiệm như nhau (đã test).

---

## 3. Gọi SAT solver qua PySAT (`solvers/pysat_runner.py`)

```python
with Solver(name="cadical195", bootstrap_with=clauses) as s:
    sat = s.solve()
    model = s.get_model()      # list literal có dấu, ví dụ [-1, 2, -3, ...]
```

* `decode_model` chỉ đọc biến 1..n² và bỏ qua biến phụ. Nếu một hàng có 0 hoặc ≥ 2 hậu thì trả về None.
* **Mọi nghiệm đều đi qua `is_valid_solution`.** Nếu solver trả SAT mà nghiệm sai, kết quả bị ghi là ERROR. Đây là "bộ kiểm chứng độc lập": ta không tin encoding, ta kiểm tra đầu ra.
* `count_solutions`: sau mỗi nghiệm, thêm **blocking clause** "không được lặp lại đúng tập hậu này", ví dụ với nghiệm n=4 `cols=[1,3,0,2]` thì thêm `[-2,-8,-9,-15]`. Chỉ chặn trên biến bàn cờ, không chặn biến phụ, để mỗi bàn cờ chỉ được đếm một lần dù biến phụ có thể nhận nhiều giá trị.
* Solver dùng: `cadical195` (CaDiCaL 1.9.5), `glucose4` (Glucose 4.1), `kissat404` (Kissat 4.0.4), `minisat22` (MiniSat 2.2). Tất cả đều là CDCL: lan truyền đơn vị, học mệnh đề từ xung đột, khởi động lại, heuristic chọn biến kiểu VSIDS/VMTF.

---

## 4. Các phương pháp chính xác khác (`exact/`)

### 4.1 Mô hình 0-1 (dùng cho Gurobi, CPLEX MIP, CP-SAT bool)
```
x_rc ∈ {0,1}
Σ_c x_rc = 1   ∀ hàng r          (n ràng buộc)
Σ_r x_rc = 1   ∀ cột c           (n ràng buộc)
Σ_{(r,c) ∈ D} x_rc ≤ 1   ∀ đường chéo D dài ≥ 2   (2(2n−3) ràng buộc)
```
Tổng cộng n² biến và 6n − 6 ràng buộc (`mip_size`, có test). Bài toán chỉ cần tìm nghiệm khả thi, nên hàm mục tiêu là 0.

**Vì sao LP relaxation vô dụng ở đây?** Gán x_rc = 1/n cho mọi ô thì mọi hàng/cột có tổng bằng 1, mọi đường chéo có tổng ≤ 1. LP luôn khả thi, nên không cắt tỉa được gì. Solver MIP phải dựa vào heuristic, presolve và rẽ nhánh.

**Giới hạn license (đã kiểm chứng bằng cách gọi thật):**
* Gurobi pip (size-limited): ≤ 2000 biến, nên n ≤ 44 (44² = 1936). n=45 báo "Model too large for size-limited license".
* CPLEX Community: ≤ 1000 biến, nên n ≤ 31. n=32 báo "CPLEX code=1016 ... Problem size limits (1000 vars, 1000 consts) exceeded".
Code kiểm tra trước kích thước và ghi ERROR kèm ghi chú, để không gọi solver vô ích.

### 4.2 Mô hình CP nguyên (CP-SAT int, CPLEX CP)
```
q_r ∈ {0..n−1}           (cột của hậu ở hàng r; mỗi hàng đúng 1 hậu là tự động)
AllDifferent(q_r)        (khác cột)
AllDifferent(q_r + r)    (khác đường chéo r+c)
AllDifferent(q_r − r)    (khác đường chéo r−c)
```
Chỉ có n biến, 3 ràng buộc toàn cục. Tuy nhiên CP-SAT là solver "lazy clause generation": bên dưới nó vẫn mã hóa biến nguyên thành biến Boolean. Log của CP-SAT với n=256 cho thấy presolve tạo 65.536 biến Boolean (`new_bool: integer encoding`) và 131.330 ràng buộc. Presolve ăn gần hết thời gian, và với 1 luồng thì mô hình này chậm hơn hẳn mô hình 0-1.

### 4.3 CPLEX CP Optimizer
Gói pip `cplex` **không chứa** file thực thi `cpoptimizer`. Phải cài IBM ILOG CPLEX Optimization Studio (bản Community miễn phí, cần IBMid). `find_cpoptimizer()` tìm theo thứ tự: biến môi trường `$CPOPTIMIZER_PATH`, `PATH`, `/Applications/CPLEX_Studio*/cpoptimizer/bin/*/cpoptimizer`. Nếu không thấy, kết quả là ERROR "cpoptimizer not installed" và test của nó được skip.

### 4.4 Công bằng khi so sánh
Mọi solver chạy **1 luồng** (CP-SAT `num_workers=1`, Gurobi `Threads=1`, CPLEX `threads=1`), seed 0, cùng time limit 60 s, cùng máy. Các SAT solver trong PySAT vốn là đơn luồng.

---

## 5. Baseline không dùng SAT (`baselines/backtracking.py`)

* **Bitmask backtracking**: 3 số nguyên `col_mask`, `diag_l`, `diag_r` đánh dấu các ô bị tấn công ở hàng hiện tại. Sau khi đặt hậu ở bit `b`, sang hàng sau thì `diag_l` dịch trái 1 (đường chéo đi xuống phải) và `diag_r` dịch phải 1 (đi xuống trái). Ô trống là `free = full & ~(col|dl|dr)`, và `free & -free` lấy bit thấp nhất.
* **Công thức tường minh** (Hoffman, Loessi & Moore 1969): đặt các cột chẵn trước rồi đến các cột lẻ, sửa riêng khi n mod 6 ∈ {2, 3}. Tìm **một** nghiệm mất **O(n)**, đã test đúng cho mọi n từ 4 đến 399.

⇒ **Ý nghĩa cho báo cáo:** tìm một nghiệm N-Queens là bài toán dễ (có thuật toán O(n)), nên benchmark này không nhằm "giải N-Queens nhanh nhất". Nó đo **chất lượng encoding và solver** trên một họ bài toán có cấu trúc rõ, kích thước tăng dần. Bài toán khó thật là **N-Queens completion** (cho trước một số hậu, hỏi có hoàn thành được không), đã được chứng minh NP-complete (Gent, Jefferson & Nightingale 2017). Mô hình SAT ở đây mở rộng sang completion chỉ bằng cách thêm unit clause cho các hậu cho trước.

---

## 6. Runner thực nghiệm (`experiments/run_benchmark.py`, `worker.py`)

* **Mỗi lần chạy là một tiến trình con riêng** (multiprocessing, spawn). Nhờ vậy:
  * time limit được thực thi bằng cách **kill** tiến trình. Không phải backend PySAT nào cũng hỗ trợ `interrupt()`;
  * nếu hết RAM thì chỉ tiến trình con chết, lưới thực nghiệm vẫn chạy tiếp;
  * thời gian đo không bị ảnh hưởng bởi rác bộ nhớ của lần chạy trước.
* **Giao thức:** con gửi `("built", info)` sau khi dựng xong CNF, cha **bắt đầu tính time limit từ đây**. Vì vậy time limit chỉ áp cho phần giải, còn thời gian dựng CNF bằng Python được ghi riêng (`build_time_s`).
* **Dừng sớm:** với mỗi cấu hình (encoding, solver), n tăng dần cho đến lần TIMEOUT/ERROR đầu tiên. Các n lớn hơn không chạy và không có dòng CSV. Đây là quy ước phổ biến, phải ghi rõ trong báo cáo.
* **Resume:** dòng nào đã có trong CSV thì không chạy lại (chạy tiếp được khi bị ngắt).
* **CSV:** `experiment, n, encoding, solver, status, time_s, build_time_s, total_time_s, num_vars, num_clauses, count, expected, seed, note`.
* `results/environment.txt` ghi CPU, RAM, OS, phiên bản Python và các thư viện, dùng cho phụ lục báo cáo.

Sáu thí nghiệm:

| Tên | Nội dung | Lưới |
|---|---|---|
| `size` | kích thước CNF của 11 encoding | n = 8 … 512 |
| `sat` | 11 encoding × 4 SAT solver, tìm 1 nghiệm | n = 8 … 512 |
| `exact` | CP-SAT (int, bool), Gurobi, CPLEX MIP, CPLEX CP | n = 2, 3, 8 … 1000 |
| `count` | đếm mọi nghiệm: 11 encoding + backtracking + CP-SAT | n = 1 … 12 |
| `colalo` | ablation: có/không ALO cột | 4 encoding × 2 solver, n = 32 … 512 |
| `exactsat` | 2 cấu hình SAT tốt nhất (tự chọn từ `sat.csv`) trên đúng lưới n của `exact` | n = 2 … 1000 |

---

## 7. Test (`tests/`)

| File | Kiểm chứng điều gì |
|---|---|
| `test_common.py` | `var` là song ánh 1..n²; `decode_model` bỏ biến phụ, từ chối hàng 0/2 hậu; `is_valid_solution` bắt đủ 5 kiểu lỗi |
| `test_baselines.py` | backtracking đếm đúng OEIS n=1..10; nghiệm hợp lệ; n=2,3 vô nghiệm; công thức tường minh đúng với n=4..399 |
| `test_amo.py` | **ngữ nghĩa** của 11 AMO: với mọi gán của k ≤ 8 literal (vét cạn) và mẫu ngẫu nhiên với k = 17, 26, 37, CNF thỏa được ⟺ ≤ 1 literal đúng; biến phụ nằm đúng khoảng; literal âm và offset bất kỳ; công thức số mệnh đề/biến phụ |
| `test_nqueens_cnf.py` | 11 encoding cho đúng số nghiệm OEIS n=1..8; **tập nghiệm trùng với vét cạn hoán vị** (n=5,6,7); bỏ ALO cột vẫn đúng; 4 solver trả đúng SAT/UNSAT |
| `test_exact.py` | CP-SAT, Gurobi, CPLEX: n=3 UNSAT, n=1/8/20 cho nghiệm hợp lệ; lỗi license đúng chỗ; CP-SAT đếm đúng số nghiệm |

`test_amo.py` chính là bước "đối chiếu encoding tự viết với `pysat.card` về tính tương đương" trong quy ước. Thay vì so sánh hai CNF với nhau, nó so mỗi CNF với **định nghĩa** AMO, và đó là phép kiểm chứng mạnh hơn.

---

## 8. Cách chạy lại mọi thứ

```bash
source .venv/bin/activate
python -m unittest discover -s tests -t .                 # 25 test
python -m nqueens.experiments.run_benchmark exact --time-limit 60
python -m nqueens.experiments.run_benchmark size
python -m nqueens.experiments.run_benchmark count --time-limit 60
python -m nqueens.experiments.run_benchmark sat --time-limit 60
python -m nqueens.experiments.run_benchmark exactsat --time-limit 60
python -m nqueens.experiments.run_benchmark colalo --time-limit 60
python -m nqueens.experiments.make_figures                 # results/figures/*.pdf
python -m nqueens.experiments.make_tables                  # report/tables/*.tex
```

---

## 9. Kết quả chính và cách hiểu (đọc cùng `report/main.pdf`)

Mọi con số dưới đây lấy từ `results/*.csv` (time limit 60 s, 1 luồng, máy i5-7267U, 8 GB). Bảng/hình trong báo cáo do `make_tables.py` / `make_figures.py` sinh tự động, không chép tay.

**(1) Tính đúng.** 132/132 lần đếm (11 encoding × n=1..12) khớp OEIS, kể cả n=2,3 vô nghiệm. Mọi nghiệm trả về đều qua `is_valid_solution`. 369 lần chạy `sat`: 266 SAT, 88 UNSAT (n=2,3), 13 TIMEOUT, 2 ERROR (không dựng nổi CNF).

**(2) Kích thước** (n=512): product ít mệnh đề nhất (2,44 triệu), rồi sequential (3,13 triệu), commander (3,65 triệu). Binary có ít biến phụ nhất (0,29 triệu) nhưng nhiều mệnh đề nhất trong nhóm dưới bậc ba (9,26 triệu). Pairwise và **PySAT totalizer** là Θ(n³): totalizer ở n=256 đã có 29,8 triệu mệnh đề, và ở n=512 dựng không nổi trong 900 s.
→ *Bài học:* PySAT `totalizer` là encoding cho at-most-**k** tổng quát; dùng cho k=1 thì nó vẫn dựng bộ đếm đầy đủ, rất lãng phí.

**(3) SAT solver × encoding:**
* Commander và binary là 2 encoding duy nhất giải được n=512 với **cả 4** solver. Commander nhanh nhất ở n=256 với CaDiCaL/Glucose/Kissat.
* **Product + MiniSat** là cấu hình nhanh nhất: 0,77 s (n=256), 4,22 s (n=512), 14,7 s (n=1000).
* MiniSat 2.2 (cũ nhất) giải n=512 với mọi encoding dựng được CNF (8 cấu hình), Kissat 7, CaDiCaL 3, Glucose 3. *Giả thuyết (chưa kiểm chứng):* CaDiCaL/Kissat tốn công cho preprocessing/inprocessing, có lợi với bài khó nhưng là chi phí thừa với các CNF lớn mà dễ này.
* Glucose thất thường: PySAT bitwise mất 14,1 s ở n=64 nhưng chỉ 0,57 s ở n=128.
* Sequential có CNF nhỏ thứ 2 nhưng lại chậm với CaDiCaL/Glucose ⇒ **số mệnh đề không quyết định tất cả**.

**(4) ALO cột dư thừa nhưng rất có ích.** Giữ ALO cột thì nhanh hơn trong 28/36 trường hợp so sánh, có lúc nhanh hơn > 10 lần (product + CaDiCaL n=64: 0,35 s so với 8,26 s). Có 4 trường hợp chỉ bản có ALO cột giải kịp.
→ *Vì sao?* Suy ra "cột nào cũng có hậu" từ "mỗi hàng 1 hậu + mỗi cột ≤ 1" là lập luận **chuồng bồ câu**, thứ mà unit propagation không làm được, còn resolution thì rất kém (Haken 1985). Viết thẳng ra thì solver có ngay thông tin đó.

**(5) So với CP/MIP:**
* Gurobi/CPLEX: rất nhanh (≤ 0,05 s) nhưng bị license chặn ở n ≤ 44 / n ≤ 31. **Đây là giới hạn license, không phải của thuật toán.**
* CP-SAT 0-1: tới n=512 (10,2 s), timeout ở n=1000. CP-SAT nguyên (AllDifferent): timeout ở n=512, vì presolve "nở" n=256 thành 65.536 biến Boolean.
* SAT nhanh nhất từ n=64 trở đi và là phương pháp **duy nhất** giải được n=1000.
* CPLEX CP Optimizer: chưa chạy được vì thiếu file `cpoptimizer`. Báo cáo ghi rõ điều này.

**(6) Độ tin cậy số đo.** 40 cấu hình được chạy lại trong thí nghiệm `colalo` cho cùng kết quả 40/40 (SAT/TO). Với các lần chạy > 0,5 s, thời gian lệch trung vị 6,2% (tỉ lệ 0,72–1,28). ⇒ Chênh lệch dưới khoảng 2 lần thì không nên kết luận gì.

---

## 10. Câu hỏi vấn đáp có thể gặp (tự trả lời trước, rồi mới đọc gợi ý)

1. **Vì sao chỉ cần kiểm tra `r−c` và `r+c` cho đường chéo?**
   Gợi ý: hai ô (r1,c1), (r2,c2) cùng đường chéo ⟺ |r1−r2| = |c1−c2| ⟺ r1−c1 = r2−c2 hoặc r1+c1 = r2+c2.
2. **Có cần ALO cho cột không?** Không, xem lập luận chuồng bồ câu ở mục 1.2. Trong code vẫn giữ để hỗ trợ lan truyền; thí nghiệm `colalo` cho biết nó có thực sự giúp hay không.
3. **Vì sao sequential cần k−1 biến phụ mà vẫn tương đương pairwise?** s_i là OR tiền tố. Nghiệm của pairwise mở rộng được bằng cách gán s_i = x1∨…∨xi. Ngược lại, mọi nghiệm của sequential (chiếu lên x) đều có ≤ 1 literal đúng. Hai CNF tương đương **trên biến gốc** (equisatisfiable với cùng phép chiếu), không phải tương đương logic theo nghĩa hẹp vì có thêm biến.
4. **Binary encoding có lan truyền mạnh như pairwise không?** Khi một xi đúng: có, mọi xj khác bị ép sai (mục 2.7). Nhưng solver có thể quyết định trên bit phụ, và một bit sai chỉ loại bỏ một nửa số literal, nên nó "kém trực quan" hơn với heuristic.
5. **Vì sao thời gian phụ thuộc encoding dù tập nghiệm như nhau?** Kích thước CNF (bộ nhớ, tốc độ lan truyền), biến phụ thay đổi không gian quyết định và mệnh đề học được, và heuristic từng solver phản ứng khác nhau.
6. **Mô hình MIP dùng ràng buộc gì? Vì sao LP relaxation yếu?** Xem mục 4.1: x = 1/n luôn khả thi.
7. **Vì sao Gurobi/CPLEX chỉ chạy n nhỏ?** Do license, không phải do thuật toán. Cần nói rõ đây là giới hạn của bản miễn phí.
8. **Vì sao blocking clause chỉ chặn biến bàn cờ?** Nếu chặn cả biến phụ thì một bàn cờ có thể bị đếm nhiều lần khi biến phụ có nhiều giá trị hợp lệ.
9. **Tìm 1 nghiệm có công thức O(n), vậy làm SAT để làm gì?** Mục 5: benchmark encoding/solver; mở rộng sang N-Queens completion (NP-complete) chỉ cần thêm unit clause.
10. **Đóng góp của bạn so với bài báo tham khảo (Tran Ngoc Bach 2024)?** Gợi ý: (i) commander và product tự cài và kiểm chứng ngữ nghĩa vét cạn; (ii) so sánh với 6 encoding của PySAT trên 4 solver; (iii) so sánh với CP-SAT (2 mô hình), Gurobi, CPLEX dưới cùng giao thức 1 luồng; (iv) runner tái lập được, mọi số liệu truy về CSV.
