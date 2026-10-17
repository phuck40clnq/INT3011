# Lộ trình 7 bước

> **Cập nhật 2026-10-16 (chế độ deadline):** các bước 1, 2, 3, 6, 7 đã được hoàn thành (code do Claude viết theo yêu cầu, giải thích trong `docs/LEARN.md`). Bước 4 (CDCL tự viết) và bước 5 (local search) nằm ngoài phạm vi đã chọn; có thể làm sau nếu muốn học thêm.

Mỗi bước có: **mục tiêu**, **sản phẩm**, **tiêu chí hoàn thành**, **câu hỏi kiểm tra hiểu**. Bước chỉ xong khi đạt cả tiêu chí và trả lời được câu hỏi.
Đánh dấu `[x]` khi hoàn thành.

## [x] Bước 1: Baseline và bộ kiểm chứng
- **Mục tiêu**: hiểu cấu trúc bài toán, có công cụ kiểm chứng dùng cho mọi bước sau
- **Sản phẩm**: `common.py` (verify, var, decode), `baselines/backtracking.py` (set rồi bitmask), `tests/test_baseline.py`
- **Hoàn thành khi**: số nghiệm n=1..10 khớp A000170; n=2,3 không có nghiệm; bitmask nhanh hơn bản set (có số đo)
- **Hỏi**: Vì sao chỉ cần kiểm tra `r−c` và `r+c`? Mask đường chéo dịch về phía nào khi sang hàng sau và vì sao?
- Stub: `docs/steps/step1_baseline.md`

## [x] Bước 2: AMO encoding tự cài
- **Mục tiêu**: hiểu đánh đổi số mệnh đề / số biến phụ / sức mạnh lan truyền
- **Sản phẩm**: `encodings/amo.py` (pairwise, sequential counter, binary, commander, product), `encodings/nqueens_cnf.py`
- **Hoàn thành khi**: với n nhỏ, mọi encoding cho cùng số nghiệm (92 với n=8); bảng số biến/mệnh đề khớp công thức lý thuyết
- **Hỏi**: Binary encoding có AMO "mạnh" bằng pairwise về unit propagation không? Vì sao sequential cần k−1 biến phụ?

## [x] Bước 3: Chạy qua PySAT
- **Mục tiêu**: dùng solver thật, đo đạc đúng cách
- **Sản phẩm**: `solvers/pysat_runner.py`; thử cadical153/195, glucose4, kissat404, minisat22
- **Hoàn thành khi**: mọi nghiệm qua `is_valid_solution`; có bảng thời gian theo (n, encoding, solver)
- **Hỏi**: Vì sao thời gian phụ thuộc vào encoding dù tập nghiệm như nhau?

## [ ] Bước 4: SAT solver tự viết
- **Mục tiêu**: hiểu DPLL → CDCL từ bên trong
- **Sản phẩm**: `solvers/my_cdcl.py`, tiến hóa theo từng mức: DPLL, unit propagation, 2-watched literals, 1UIP learning, VSIDS, restart
- **Hoàn thành khi**: giải đúng n nhỏ, cùng kết quả SAT/UNSAT với PySAT; có đồ thị so sánh theo từng mức cải tiến
- **Hỏi**: Vì sao 2-watched literals tránh phải duyệt toàn bộ mệnh đề? Mệnh đề học được giúp gì?

## [ ] Bước 5: Local search
- **Mục tiêu**: so sánh hướng tiếp cận "không đầy đủ"
- **Sản phẩm**: `baselines/local_search.py` (min-conflicts; tùy chọn WalkSAT trên CNF)
- **Hoàn thành khi**: giải n rất lớn (≥ 10^4 với min-conflicts), có số đo
- **Hỏi**: Vì sao min-conflicts với khởi tạo thông minh gần như không bị kẹt trên N-Queens?

## [x] Bước 6: Baseline chính xác và thực nghiệm
- **Mục tiêu**: so sánh SAT với ILP/CP theo yêu cầu đề
- **Sản phẩm**: `exact/*.py`, `experiments/run_benchmark.py`, CSV trong `results/`
- **Hoàn thành khi**: bảng đầy đủ (n, phương pháp, status, time); ghi rõ giới hạn community license
- **Hỏi**: Mô hình MIP của N-Queens dùng ràng buộc gì? Vì sao LP relaxation yếu?

## [x] Bước 7: Báo cáo
- **Mục tiêu**: trình bày như bài báo khoa học (mẫu `cas-sc`, Elsevier)
- **Sản phẩm**: `report/` (Abstract, Introduction, Background, Encodings, Experiments, Conclusion, Data Availability có link GitHub)
- **Hoàn thành khi**: mọi con số trong báo cáo truy được về CSV; repo công khai; có hướng dẫn tái lập
- **Hỏi**: Đóng góp của bạn so với bài báo tham khảo là gì?

## Nhật ký
Ghi ngày hoàn thành và ghi chú từng bước vào mục dưới đây.

| Bước | Ngày | Ghi chú |
|---|---|---|
| 1, 2, 3, 6, 7 | 2026-10-16 | chế độ deadline; xem docs/LEARN.md và report/ |
| 4, 5 | | ngoài phạm vi |
