# DFS: kiểm thử và số liệu campaign — 27/10/2026

Tài liệu dành cho thành viên phụ trách DFS và người tích hợp. Mục đích là mô tả
xử lý lỗi cost, cách chạy kiểm thử và số liệu DFS trên 10 màn hiện hành.

## Hiện thực và xử lý lỗi

`search/dfs.py` đã triển khai DFS, không còn là stub. Solver dùng stack LIFO,
đẩy successor ngược thứ tự `Problem.actions()` và đánh dấu visited khi mở rộng.
Node trùng bị bỏ qua; goal được xét khi pop, trước timeout và node limit.
DFS bỏ qua heuristic, truy vết actions và tính tổng `Problem.step_cost()`.

Cost của successor được đưa vào stack phải dương và hữu hạn. Cost không hợp lệ
gây `ValueError("Step cost must be positive and finite")`. Nếu tổng cost bị tràn,
solver gây `ValueError("Accumulated cost must be finite")`. Ví dụ hai bước có
cost `1e308` không còn trả `solved` với `total_cost=inf`. Runner truyền exception
cho bên gọi, không chuyển lỗi dữ liệu/số học thành `unsolvable`.

DFS thường có chống lặp không cần depth limit trên không gian trạng thái hữu hạn.
Không thay giao diện solver, luật game hoặc thêm IDS. DFS không bảo đảm lời giải
ngắn nhất hay chi phí thấp nhất.

## Kiểm thử

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_dfs.py -v
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_foundation.py -v
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_solver_integration.py -v
```

**PASS:** 41 test trong ba module trên (24 DFS, 14 foundation, 3 integration),
chạy cùng một suite trên nền `ba82f78` với bản sửa DFS. Integration giải và
replay đủ 10 màn bằng bốn solver. **NOT RUN:** discovery toàn bộ test và GUI
thủ công trong lần kiểm tra DFS này.

24 test DFS bao phủ thứ tự duyệt, chống lặp, backtrack, truy vết/cost, trạng thái
cầu động, không sửa state ban đầu, timeout, node limit và các lỗi từ engine.
Các case bổ sung kiểm tra cost vô hạn/NaN/không dương, tràn tổng cost, initial
goal trước timeout và timeout sau successor cuối không hợp lệ. Không dùng sleep
để kiểm tra timeout; đồng hồ được mock.

## Số liệu đo riêng DFS

```powershell
.venv\Scripts\python.exe -B -m examples.benchmark_dfs --output docs/DFS_BENCHMARK.json
```

Lệnh ghi lại [dữ liệu thô](DFS_BENCHMARK.json), gồm revision nền, SHA-256 của mã
nguồn/màn, môi trường, giới hạn và từng lượt đo. Dữ liệu hiện tại dùng nền
`262cf81ef91d9750009110f0fd1c21c569bd499d` cùng bản sửa DFS trong working tree tại thời điểm đo;
SHA-256 xác định nội dung mã thực tế, không coi revision nền là bản đã chứa sửa lỗi.

Môi trường đo: Python 3.12.6, Windows 11 build 22621. Mỗi màn chạy ba lần với
cost mặc định (`tile`), rồi ba lần với `unit_cost=True` (`unit`); không warm-up
riêng. Mỗi lượt tải problem mới. Giới hạn 60 giây và 1.000.000 expanded nodes.
Runner đo toàn bộ `solve()`, gồm truy vết, bằng `perf_counter` và `tracemalloc`.
Đọc JSON, replay kiểm tra goal/cost và đối chiếu state nguồn nằm ngoài thời gian đo.

**PASS:** 60/60 lượt solved, replay hợp lệ và giữ nguyên state ban đầu.
Actions, cost và counters ổn định trong từng nhóm ba lượt. Hai chế độ cost cho
cùng actions và counters; DFS không dùng cost để sắp thứ tự duyệt.

Thời gian và peak memory trong bảng là trung vị ba lượt theo từng chế độ.
Bộ nhớ là đỉnh cấp phát Python do `tracemalloc` ghi nhận, đổi sang MiB
(`1 MiB = 1.048.576 byte`), không phải RSS. Bước gồm cả `SWITCH`; số lần lăn
riêng và từng giá trị byte có trong dữ liệu thô.

| Màn | Bước | Cost tile / unit | Expanded / generated | Giây tile / unit | MiB tile / unit |
| --- | --- | --- | --- | --- | --- |
| 1 | 99 | 99 / 99 | 132 / 374 | 0.244 / 0.239 | 1.06 / 1.06 |
| 2 | 169 | 193 / 169 | 222 / 631 | 0.890 / 0.803 | 3.14 / 3.17 |
| 3 | 87 | 119 / 87 | 147 / 373 | 0.378 / 0.343 | 1.06 / 1.06 |
| 4 | 100 | 128 / 100 | 123 / 323 | 0.393 / 0.359 | 1.30 / 1.30 |
| 5 | 122 | 120 / 122 | 140 / 375 | 0.454 / 0.450 | 1.29 / 1.32 |
| 6 | 187 | 185.5 / 187 | 227 / 642 | 0.827 / 0.835 | 2.79 / 2.77 |
| 7 | 130 | 127.5 / 130 | 387 / 968 | 1.753 / 1.840 | 3.60 / 3.60 |
| 8 | 153 | 172.5 / 153 | 161 / 588 | 0.847 / 0.824 | 2.70 / 2.70 |
| 9 | 207 | 201.5 / 207 | 233 / 806 | 1.406 / 1.397 | 5.53 / 5.62 |
| 10 | 446 | 504.5 / 446 | 460 / 1806 | 3.345 / 3.430 | 12.31 / 12.35 |

Đây là số liệu riêng DFS trên một máy, có overhead của `tracemalloc`, không
chứng minh thuật toán nhanh hơn solver khác. Không so thời gian với các lượt
audit gọi solver trực tiếp hoặc dữ liệu màn khác phiên bản. Chưa có benchmark
so sánh tất cả solver trong cùng điều kiện hoặc nghiệm thu GUI thủ công.

Nguồn đối chiếu: `search/dfs.py`, `tests/test_dfs.py`, `runner.py`,
`gameModel/problem.py`, `tests/test_solver_integration.py`,
[contract §§8–10](CONTRACT.md) và `examples/benchmark_dfs.py`.
