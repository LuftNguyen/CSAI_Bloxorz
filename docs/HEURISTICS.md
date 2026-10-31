# Heuristic (search/heuristics.py)

Chữ ký theo contract: `heuristic(problem, state) -> float`, hữu hạn, không âm, bằng 0 tại đích, không sửa state, không gọi GUI.

| Tên | Công thức | Vai trò |
| --- | --- | --- |
| `zero` | h = 0 | Kiểm tra A* == UCS |
| `manhattan_lower_bound` | max(1, ⌈D/2⌉), 0 nếu đang đứng trên đích | Mốc so sánh trong báo cáo |
| `relaxed_distance` | Chi phí tối ưu còn lại trong bài toán nới lỏng R | **Heuristic chính** |

Trường đọc: `problem.unit_cost`, `problem.fragile_penalty`, `problem.initial.board` (`tiles`, `bridgeGroups`, `rows`, `cols`), `state.block` (`r`, `c`, `dr`, `dc`, `orientation`).

## Hàm chi phí mà heuristic phải khớp

Mỗi bước có chi phí `1 + λ·I(fragile)`, trong đó λ = `problem.fragile_penalty` (mặc định `FRAGILE_PENALTY` = 0,25 trong `gameModel/board.py`) và I = 1 nếu bước lăn có ít nhất một ô đang chiếm là ô fragile, ngược lại I = 0. Khi `unit_cost=True` mọi bước có chi phí 1. SWITCH có chi phí 1. Công tắc không có ưu đãi. Vì mọi bước tốn ít nhất 1 nên cận dưới theo số bước luôn dùng được.

## relaxed_distance

Bài toán nới lỏng R giữ nguyên: nút (r, c, dr, dc), hình học lăn (`Block.resultingState`), luật VOID/ngoài biên, luật FRAGILE (đứng thì rơi), điều kiện thắng (đứng trên GOAL) và công thức chi phí của `Problem.step_cost` ở trên (`1 + λ·I(fragile)`, hoặc 1.0 khi `unit_cost`).
R chỉ khác bài toán thật ở chỗ: mọi ô thuộc `bridgeGroups` luôn mở (xem như ô BRIDGE) và công tắc không còn tác dụng.

Cách tính: một lần cho mỗi `problem`, chạy Dijkstra ngược từ ô GOAL trên đồ thị khối của R, lưu bảng `(r, c, dr, dc) -> chi phí`. Mỗi lần gọi heuristic là một phép tra dict, O(1). Có thể gọi `precompute(problem)` trước khi đo thời gian.

**Admissible.** Mọi nước đi hợp lệ trong bài toán thật cũng là nước đi hợp lệ trong R với cùng chi phí: nước đi hợp lệ không bao giờ chiếm ô VOID, cầu đóng là VOID nên không bao giờ bị chiếm, còn cầu mở là ô thường (chi phí cơ sở 1) đúng như R dùng. Vậy R có tập nước đi lớn hơn, nên chi phí tối ưu của R ≤ chi phí tối ưu thật.

**Consistent.** h là khoảng cách ngắn nhất thật trong R nên h(s) ≤ c(s, s') + h(s') với mọi cạnh của R, trong đó có mọi cạnh thật.

**Trạng thái chết.** Nếu R cũng không tới được đích thì trả hằng số hữu hạn `DEAD_H = 1e9`. Giá trị này vẫn admissible (chi phí thật là vô hạn) và consistent (tập trạng thái chết đóng dưới nước đi, cùng một giá trị).

**Phụ thuộc hàm chi phí.** Bảng relaxed được cache theo từng đối tượng `Problem`, nên mỗi giá trị λ phải dùng một `Problem` mới (đừng đổi `fragile_penalty` trên `Problem` đã tạo). Nếu đổi hàm chi phí thì chạy lại `tests/test_heuristics.py`.

## manhattan_lower_bound

D = khoảng cách Manhattan nhỏ nhất từ một ô khối đang chiếm tới ô đích. Một lần lăn giảm D tối đa 2 nên cần ít nhất ⌈D/2⌉ lần lăn; nếu D = 0 mà chưa đứng trên đích thì cần ít nhất 1 lần. Mỗi lần lăn tốn ít nhất 1 (cả khi `unit_cost` bật lẫn tắt), nên h = max(1, ⌈D/2⌉). Admissible và consistent vì ⌈D/2⌉ giảm tối đa 1 mỗi lần lăn còn mỗi lần lăn tốn ≥ 1.

## Khối tách đôi

Khi khối đang ở trạng thái tách, cả hai heuristic trả 0.0 (h = 0). Với màn có split switch, bảng relaxed lấy cả ô GOAL và các ô split switch làm đích (đích trung gian), còn `manhattan_lower_bound` lấy giá trị nhỏ hơn giữa cận tới GOAL và cận tới split switch. Khi thêm luật mới hoặc đổi chi phí phải kiểm chứng lại.

## Kiểm chứng (tests/test_heuristics.py)

Test duyệt toàn bộ không gian trạng thái đạt được của các màn trong `levels/` (cả `unit_cost` True/False), tính h* chính xác bằng Dijkstra ngược (chỉ dùng làm oracle trong test, không phải solver của nhóm) rồi kiểm tra với cả ba heuristic: giá trị hữu hạn và không âm, h(đích) = 0, h ≤ h* ở mọi trạng thái còn tới được đích, và h(s) ≤ c + h(s') trên mọi cạnh.

Ngoài ra, `examples/sweep_lambda.py` chạy UCS và A* với `relaxed_distance` trên 10 màn với λ ∈ {0; 0,25; 0,5; 1; 3}: A* cho chi phí bằng UCS ở cả 50 cấu hình.

Giá trị tại trạng thái đầu, dạng chi phí tối ưu h* / manhattan / relaxed (cột phải dùng λ = 0,25):

| Màn | `unit_cost` | λ = 0,25 |
| --- | --- | --- |
| 1 | 10 / 7 / 10 | 10 / 7 / 10 |
| 2 | 13 / 9 / 13 | 13 / 9 / 13 |
| 3 | 13 / 9 / 13 | 13,25 / 9 / 13,25 |
| 4 | 23 / 11 / 23 | 24 / 11 / 24 |
| 5 | 16 / 10 / 16 | 16 / 10 / 16 |
| 6 | 20 / 9 / 14 | 20 / 9 / 14 |
| 7 | 25 / 10 / 20 | 25 / 10 / 20 |
| 8 | 20 / 2 / 4 | 21,25 / 2 / 4 |
| 9 | 19 / 3 / 4 | 19 / 3 / 4 |
| 10 | 26 / 2 / 4 | 26,25 / 2 / 4 |

`relaxed_distance` chính xác ở màn 1-5 (không có cầu cản đường hoặc cầu không làm tăng chi phí tại trạng thái đầu), thấp hơn ở các màn cầu/công tắc (6, 7) vì R coi cầu luôn mở, và rất thấp ở các màn split (8-10) vì đích trung gian là ô split switch. Đó là lý do ở các màn này A* gần như không mở ít node hơn UCS. Đây chỉ là số tại trạng thái đầu; số node mở rộng và thời gian lấy từ benchmark.