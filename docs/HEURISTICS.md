# Heuristic (search/heuristics.py)

Chữ ký theo contract: `heuristic(problem, state) -> float`, hữu hạn, không âm, bằng 0 tại đích, không sửa state, không gọi GUI.

| Tên | Công thức | Vai trò |
| --- | --- | --- |
| `zero` | h = 0 | Kiểm tra A* == UCS |
| `manhattan_lower_bound` | m · max(1, ⌈D/2⌉), 0 nếu đang đứng trên đích | Mốc so sánh trong báo cáo |
| `relaxed_distance` | Chi phí tối ưu còn lại trong bài toán nới lỏng R | **Heuristic chính** |

Trường đọc: `problem.unit_cost`, `problem.initial.board` (`tiles`, `bridgeGroups`, `rows`, `cols`), `state.block` (`r`, `c`, `dr`, `dc`, `orientation`).

## relaxed_distance

Bài toán nới lỏng R giữ nguyên: nút (r, c, dr, dc), hình học lăn (`Block.resultingState`), luật VOID/ngoài biên, luật FRAGILE (đứng thì rơi), điều kiện thắng (đứng trên GOAL) và công thức chi phí của `Problem.step_cost` (max `TILE_COST` các ô đang chiếm, hoặc 1.0 khi `unit_cost`).
R chỉ khác bài toán thật ở chỗ: mọi ô thuộc `bridgeGroups` luôn mở (xem như ô BRIDGE) và công tắc không còn tác dụng.

Cách tính: một lần cho mỗi `problem`, chạy Dijkstra ngược từ ô GOAL trên đồ thị khối của R, lưu bảng `(r, c, dr, dc) -> chi phí`. Mỗi lần gọi heuristic là một phép tra dict, O(1). Có thể gọi `precompute(problem)` trước khi đo thời gian.

**Admissible.** Mọi nước đi hợp lệ trong bài toán thật cũng là nước đi hợp lệ trong R với cùng chi phí: nước đi hợp lệ không bao giờ chiếm ô VOID, cầu đóng là VOID nên không bao giờ bị chiếm, còn cầu mở có chi phí `TILE_COST[BRIDGE]` đúng như R dùng. Vậy R có tập nước đi lớn hơn, nên chi phí tối ưu của R ≤ chi phí tối ưu thật.

**Consistent.** h là khoảng cách ngắn nhất thật trong R nên h(s) ≤ c(s, s') + h(s') với mọi cạnh của R, trong đó có mọi cạnh thật.

**Trạng thái chết.** Nếu R cũng không tới được đích thì trả hằng số hữu hạn `DEAD_H = 1e9`. Giá trị này vẫn admissible (chi phí thật là vô hạn) và consistent (tập trạng thái chết đóng dưới nước đi, cùng một giá trị).

**Phụ thuộc hàm chi phí.** Chi phí hiện tại: NORMAL/GOAL/BRIDGE = 1, switch = 0.5, FRAGILE = 5, cộng `unit_cost=True` là 1. Heuristic đọc đúng `TILE_COST` và `problem.unit_cost`. Nếu đổi chi phí thì chạy lại `tests/test_heuristics.py`.

## manhattan_lower_bound

D = khoảng cách Manhattan nhỏ nhất từ một ô khối đang chiếm tới ô đích. Một lần lăn giảm D tối đa 2 nên cần ít nhất ⌈D/2⌉ lần lăn; nếu D = 0 mà chưa đứng trên đích thì cần ít nhất 1 lần. m là chi phí nhỏ nhất của một nước: 1.0 khi `unit_cost`, ngược lại `min(TILE_COST)` = 0.5. Admissible và consistent vì ⌈D/2⌉ giảm tối đa 1 mỗi lần lăn còn mỗi lần lăn tốn ≥ m.

## Luật chưa hỗ trợ

Engine hiện chưa có split/teleport/SWITCH. Nếu state không có `block` với `r, c, dr, dc` (ví dụ khối tách đôi) thì trả 0.0 theo quy ước "h=0 cho cả màn". Khi thêm luật mới hoặc đổi chi phí phải kiểm chứng lại.

## Kiểm chứng (tests/test_heuristics.py)

Test duyệt toàn bộ không gian trạng thái đạt được của 11 màn (cả `unit_cost` True/False), tính h* chính xác bằng Dijkstra ngược (chỉ dùng làm oracle trong test, không phải solver của nhóm) rồi kiểm tra với cả ba heuristic: giá trị hữu hạn và không âm, h(đích) = 0, h ≤ h* ở mọi trạng thái còn tới được đích, và h(s) ≤ c + h(s') trên mọi cạnh.

Giá trị tại trạng thái đầu so với chi phí tối ưu h*(init):

| Màn | unit_cost | h* | manhattan | relaxed |
| --- | --- | --- | --- | --- |
| 1 | có / không | 2 / 2 | 2 / 1 | 2 / 2 |
| 2 | có / không | 22 / 22 | 15 / 7.5 | 22 / 22 |
| 3 | có / không | 6 / 6 | 4 / 2 | 6 / 6 |
| 4 | có / không | 9 / 9 | 7 / 3.5 | 9 / 9 |
| 5 | có / không | 16 / 16 | 8 / 4 | 15 / 15 |
| 6 | có / không | 15 / 23 | 8 / 4 | 15 / 23 |
| 7 | có / không | 20 / 20 | 6 / 3 | 20 / 20 |
| 8 | có / không | 12 / 12 | 8 / 4 | 12 / 12 |
| 9 | có / không | 17 / 17 | 11 / 5.5 | 17 / 17 |
| 10 | có / không | 13 / 13 | 6 / 3 | 13 / 13 |
| 11 | có / không | 18 / 18 | 13 / 6.5 | 18 / 18 |

`relaxed_distance` chính xác ở 10/11 màn và thấp hơn 1 ở màn 5, nơi cầu thật sự cản đường. Đây chỉ là số tại trạng thái đầu; số node mở rộng và thời gian cần đo khi A* hoàn thành.

## Việc còn lại cần phối hợp

- Khi `astar.py` xong: kiểm tra A* với `relaxed_distance` cùng chi phí tối ưu với UCS (contract §13) và so sánh số node, thời gian với h=0 và `manhattan`.
- `registry.py` hiện chưa có chỗ chọn heuristic; `HEURISTICS` trong `heuristics.py` là bảng tên → hàm để nối vào GUI/runner nếu nhóm đồng ý.
