# Bloxorz Solver — CSC14003, Đồ án 1

Bản cài đặt trò chơi Bloxorz có giao diện đồ họa (Ursina) cùng các bộ giải tìm kiếm
**BFS, DFS, UCS và A\***, kèm bộ benchmark và kiểm thử tự động.

- Lớp 24_22 — Trường ĐH Khoa học Tự nhiên, ĐHQG-HCM
- Nhóm: 24120027 Lý Ngọc Châu, 24120046 Nguyễn Hà Minh Hiền, 24120058 Nguyễn Lưu Hương,
  24120085 Lê Nguyễn Thùy Linh, 24120423 Đỗ Ngọc Tường Quyên

## Tính năng

- Trò chơi đầy đủ: ô thường, ô trống, ô đích; khối đứng/nằm ngang/nằm dọc; phát hiện nước đi
  không hợp lệ và điều kiện thắng/thua.
- Ô nâng cao: ô dễ vỡ, cầu đóng/mở, công tắc mềm, công tắc nặng, công tắc tách
  (tách thành hai khối lập phương, đổi khối điều khiển bằng `Space`, tự ghép khi kề nhau).
- Bốn bộ giải dùng chung một luật chơi và một hàm chi phí; lời giải luôn được phát lại
  trên luật thật để kiểm chứng trước khi hiển thị.
- Bộ 10 màn chơi dạng JSON trong `levels/`: màn 1–2 cơ bản, 3–4 ô dễ vỡ,
  5–7 cầu/công tắc, 8–10 tách/ghép khối.

## Cài đặt và chạy

Yêu cầu Python 3.12 trở lên (nhóm đã chạy với 3.13 và 3.14).

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

pip install -r requirements.txt
python main.py
```

### Điều khiển

| Thao tác | Phím / nút |
|---|---|
| Lăn khối | `W A S D` hoặc phím mũi tên |
| Đổi khối đang điều khiển (khi đã tách) | `Space` |
| Mở/đóng menu | `P` hoặc nút `MENU` |
| Chơi lại màn | `R` hoặc nút `RESTART` |
| Màn mới | nút `NEW GAME` |
| Giải tự động | nút `SOLVER` rồi chọn BFS / DFS / UCS / A\* |

Khi chọn một solver, chương trình tìm lời giải ở luồng nền (giao diện không bị đứng), kiểm chứng
lời giải, hiển thị trạng thái, số bước, chi phí, thời gian, bộ nhớ đỉnh và số nút mở rộng,
rồi phát lại các nước đi. Chọn thuật toán khác sẽ hủy lời giải đang phát và tìm lại từ trạng
thái hiện tại.

## Kiểm thử

```bash
python -m unittest discover -s tests
```

Có 208 test. Các test GUI sẽ tự bỏ qua (skip) nếu chưa cài thư viện giao diện.

## Benchmark

Chạy từ thư mục gốc của mã nguồn:

```bash
python benchmarks/benchmark_all.py --repeats 5 --output-dir benchmark_full
python benchmarks/plot_benchmark.py benchmark_full
```

Tùy chọn: `--levels 1 5 8`, `--cost-mode tile|unit`, `--fragile-penalty 0.25`,
`--timeout 60`, `--max-expanded 1000000`. Kết quả đã dùng trong báo cáo nằm ở
`benchmarks/results/` (số liệu từng lượt: `runs.csv`, tổng hợp: `level_summary.csv`,
`overall_summary.csv`) và `benchmarks/report_analysis/`.

## Mô hình tìm kiếm

- **Trạng thái:** vị trí và tư thế khối (kể cả hai khối lập phương khi tách và khối đang điều khiển),
  địa hình và trạng thái đóng/mở của từng nhóm cầu. Hai trạng thái chỉ khác cấu hình cầu là
  hai trạng thái khác nhau.
- **Hành động:** `UP`, `DOWN`, `LEFT`, `RIGHT`, và `SWITCH` khi khối đang tách.
- **Chi phí:** mỗi hành động tốn 1, cộng thêm λ = 0,25 nếu khối chạm ô dễ vỡ sau hành động đó;
  `SWITCH` tốn 1. Đặt `UNIT_COST = True` trong `gameModel/problem.py` để dùng chi phí đơn vị.
- **Heuristic của A\*:** giao diện dùng `relaxed_split_distance` (bài toán nới lỏng: bỏ qua
  tác động đóng/mở cầu, giữ nguyên hình học khối, ô dễ vỡ, tách/ghép khối, `SWITCH`; tính
  bảng khoảng cách bằng Dijkstra ngược). Có thêm `zero`, `manhattan`, `relaxed`
  để so sánh trong benchmark (`search/heuristics.py`).
- **Trạng thái trùng:** BFS/DFS/UCS/A\* đều lưu tập trạng thái đã gặp (băm toàn bộ khối + bản đồ + cầu).

## Cấu trúc thư mục

```
main.py              điểm khởi chạy
view.py, menu.py     giao diện Ursina, menu, phát lại lời giải
gui_search.py        chạy tìm kiếm ở luồng nền, có thể hủy, kiểm chứng lời giải
runner.py            đo thời gian/bộ nhớ của solve(), validate_solution()
gameModel/           Block, Board, State, Problem, GameController, rules (luật chuyển trạng thái)
levels/              level1.json ... level10.json, bộ đọc và quản lý màn
search/              bfs.py, dfs.py, ucs.py, astar.py, heuristics.py, registry.py, contracts.py
benchmarks/          benchmark_all.py, plot_benchmark.py, kết quả và phân tích đã dùng trong báo cáo
tests/               208 test (luật chơi, solver, heuristic, chi phí, GUI)
examples/, scripts/  ví dụ chạy không giao diện, script sinh tài nguyên đồ họa/âm thanh
assets/              hình ảnh và âm thanh của giao diện
```

## Nguồn gốc mã

Mã nền được phát triển tiếp từ repository
[24127352/Bloxorz---CS-AI](https://github.com/24127352/Bloxorz---CS-AI)
(commit `5571989db4ba9b4b8017b8c9486e955d551ff269`); README gốc giữ trong `README.upstream.md`.
Các thuật toán tìm kiếm, heuristic, bộ chạy/đo/kiểm chứng, luật chuyển trạng thái mở rộng
(tách/ghép khối, công tắc), benchmark và test do nhóm tự viết. Chi tiết xem mục 3.2 của báo cáo.