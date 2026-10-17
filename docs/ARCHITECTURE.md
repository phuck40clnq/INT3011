# Kiến trúc dự án N-Queens SAT

## 1. Cấu trúc thư mục

```
sat_solver/
├── CLAUDE.md                     # luật tối cao + môi trường
├── .claude/
│   ├── settings.json             # permissions (deny ghi vào mã nguồn)
│   └── rules/                    # tutor-mode.md, code-conventions.md
├── docs/
│   ├── ARCHITECTURE.md           # file này
│   ├── ROADMAP.md                # 7 bước + tiêu chí hoàn thành
│   └── steps/                    # stub + gợi ý từng bước (sinh viên chép sang nqueens/)
├── nqueens/                      # MÃ NGUỒN (chỉ sinh viên viết)
│   ├── common.py                 # verify, var(), decode_model(), SolveResult
│   ├── baselines/
│   │   ├── backtracking.py       # bước 1
│   │   └── local_search.py       # bước 5 (min-conflicts / WalkSAT)
│   ├── encodings/
│   │   ├── amo.py                # bước 2: pairwise, sequential, binary, commander, product
│   │   └── nqueens_cnf.py        # ghép ALO/EXO hàng-cột + AMO đường chéo
│   ├── solvers/
│   │   ├── pysat_runner.py       # bước 3
│   │   └── my_cdcl.py            # bước 4: DPLL → CDCL
│   ├── exact/
│   │   ├── cpsat.py              # bước 6
│   │   ├── gurobi_mip.py
│   │   ├── cplex_mip.py
│   │   └── cplex_cp.py
│   └── experiments/
│       └── run_benchmark.py      # bước 6/7: lưới (n, encoding, solver) → results/*.csv
├── tests/                        # unittest
├── results/                      # CSV, biểu đồ
├── report/                       # LaTeX (hoặc Overleaf)
└── *.pdf                         # đề bài, mẫu báo cáo, bài báo tham khảo
```

Các thư mục rỗng `nqueens/tests/` do bước dựng môi trường tạo ra; thư mục kiểm thử chính thức là `tests/` ở gốc.

## 2. Mô hình hóa

Biến `x[r][c]` = "có hậu ở ô (r, c)", DIMACS: `var(r, c, n) = r*n + c + 1`.

| Ràng buộc | Dạng CNF | Ghi chú |
|---|---|---|
| Mỗi hàng ≥ 1 hậu (ALO) | 1 mệnh đề độ dài n mỗi hàng | |
| Mỗi hàng ≤ 1 hậu (AMO) | encoding tùy chọn | nhóm n biến |
| Mỗi cột ≥ 1 (ALO) và ≤ 1 (AMO) | tương tự | |
| Mỗi đường chéo ≤ 1 (AMO) | encoding tùy chọn | chỉ AMO, đường chéo có thể rỗng hoặc ngắn |

Lựa chọn thiết kế mở (sinh viên quyết định và ghi vào báo cáo):
- Có cần ALO cho hàng **và** cột không, hay chỉ cần một trong hai? (Gợi ý: đếm số hậu cần đặt.)
- Có nên bỏ qua AMO cho đường chéo độ dài 1 không?

## 3. Giao diện (xem chi tiết `.claude/rules/code-conventions.md`)

- **AMO encoding**: `(lits, next_var) -> (clauses, next_var)`. Thay thế nhau bằng một tham số.
- **Ghép CNF**: `build_cnf(n, amo_encoder) -> (clauses, num_vars)`.
- **Solver**: nhận CNF + n, trả `SolveResult(status, cols, time_s, num_vars, num_clauses)`.
- **Kiểm chứng**: mọi nghiệm đi qua `is_valid_solution` trước khi ghi nhận.

Nhờ tách "mô hình" khỏi "solver", cùng một CNF dùng chung cho PySAT và solver tự viết để đối chiếu.

## 4. Luồng dữ liệu

```
n, amo_encoder ──► build_cnf ──► CNF ──► solver (PySAT | my_cdcl) ──► model
                                                                     │
                                          is_valid_solution ◄── decode_model
                                                  │
                                         results/*.csv ──► biểu đồ ──► report
```

## 5. Thực nghiệm (cho báo cáo)

- Lưới: n ∈ {8, 16, 32, 64, 100, 200, ...} × encoding × solver, time limit cố định (ví dụ 300 s)
- Số liệu ghi: status, time_s, num_vars, num_clauses, seed
- Hai chế độ: tìm **một** nghiệm và **đếm toàn bộ** nghiệm (n nhỏ)
- Gurobi / CPLEX community: giới hạn n nhỏ, ghi rõ trong báo cáo
- Mỗi cấu hình lặp lại nếu có yếu tố ngẫu nhiên; báo cáo trung bình + độ lệch chuẩn
