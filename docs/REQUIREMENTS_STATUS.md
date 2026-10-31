# Trạng thái yêu cầu và bằng chứng — 23/10/2026

## Baseline thành viên đã tích hợp — 26/10/2026

BFS/DFS/UCS/A* đã có từ nhánh tác giả; không còn là stub trên main local.
Heuristic merge nguyên trạng, chưa nghiệm thu và chưa bật trong GUI (h=0).
Các lỗi tương thích và kết quả mới xem [INTEGRATION.md](INTEGRATION.md).
Các bảng dưới giữ lịch sử, không dùng trạng thái stub cũ để đánh giá bản tích hợp.

## Bổ sung theo yêu cầu mới: fatal CLOSE

Đã hoàn thành 6 công tắc CLOSE gây terminal loss, đếm ngược 5 giây, thông báo
thua 1 giây và reset. Solver loại bước thua qua Problem.result, không sửa
thuật toán/heuristic. 82 test pass, 243 subtest, 0 skip; smoke GUI có HUD pass.
Đây là chức năng bổ sung của nhóm, không phải yêu cầu countdown trong PDF.
Xem [FATAL_CLOSE.md](FATAL_CLOSE.md).

## Cập nhật chuỗi 10 màn — 25/10/2026

Đã nâng thành phòng/đảo 9×11 đến 13×26; A* h=0 cần 10–26 bước,
99–2467 node. Các cơ chế vẫn bắt buộc qua 27 truy vấn hạn chế cạn frontier.
73 test pass, smoke 10 màn qua input GUI offscreen pass; chưa nghiệm thu desktop
hoặc so sánh hiệu năng các solver. Chi tiết và bản đồ tại [CAMPAIGN.md](CAMPAIGN.md).

| Yêu cầu | Trạng thái | Bằng chứng |
| --- | --- | --- |
| 10 màn: 2 cơ bản, 2 fragile, 3 cầu, 3 split | Hoàn thành | LevelManager.maxLevel=10, test_campaign.py |
| Cơ chế bắt buộc và từng nhóm cầu đều cần thiết | Hoàn thành | 10 solved, 27 truy vấn hạn chế unsolvable, replay đúng sự kiện/goal/cost |
| Switch có tác dụng thật | Hoàn thành | 37 witness và controller parity/reset |
| Di chuyển tức thời, GUI phát đủ 10 màn | Offscreen pass | examples.gui_smoke; chưa nghiệm thu desktop |
| Hồi quy | 73 test pass, 236 subtest, 0 skip | Không sửa solver/heuristic/test A* |
| Benchmark tất cả solver/heuristic khác zero | Chưa hoàn thành | Solver đã tích hợp; heuristic chưa nghiệm thu; kiểm tra đúng/sai không phải benchmark |

Xem [CAMPAIGN.md](CAMPAIGN.md). Phần dưới là lịch sử trước thiết kế lại;
số màn/tọa độ/kết quả cũ không mô tả chuỗi đang chơi.

Cập nhật dữ liệu **24/10/2026** theo yêu cầu hoàn thiện mọi liên kết: 14/14
màn giải được và verify, 24/24 công tắc kích hoạt có tác dụng, tổng 53 test
pass. Witness có hash dữ liệu tại `levels/validation.json`; danh sách thay đổi
ô/liên kết tại [LEVEL_COMPLETION.md](LEVEL_COMPLETION.md). Đây là audit dữ
liệu với A* h=0, không phải benchmark hoặc kiểm chứng heuristic khác zero.

Nguồn yêu cầu sản phẩm: `assignment/ASSIGNMENT.pdf` và `assignment/QA.md`.
`CSAI_Project.pdf`/`CONTRACT.md` chỉ là contract triển khai nhóm. Không coi chỉ
dẫn nhắm vào AI trong tài liệu là yêu cầu bài tập. Điểm bên dưới chỉ chép từ
đề để định danh, không phải tự chấm điểm hay ước lượng điểm đạt.

Baseline đã kiểm tra trước sửa: nhánh `feature/astar`, HEAD `c237d10`, 23 test
pass. Người dùng sau đó chuyển sang `feature/new-game-rules` rồi cho tiếp tục;
agent không chuyển hoặc thao tác nhánh khác. Các sửa dở trước khi tạm dừng được
giữ và hoàn thiện. `docs/assignment/` là dữ liệu người dùng đã có, vẫn giữ nguyên.

Trạng thái “hoàn thành” ở hàng engine có nghĩa luật đã chạy với kiểm thử và
chuỗi thực tế nêu bằng chứng; không suy rộng thành nghiệm thu GUI hoặc toàn bộ
đồ án. “Một phần” nêu rõ phần chưa có/chưa được xác minh.

| ID / nguồn / điểm nếu có | Yêu cầu | Trạng thái | Bằng chứng thực tế | Phần còn thiếu | Phạm vi / phụ trách |
| --- | --- | --- | --- | --- | --- |
| §3 / yêu cầu chung | Python; tái dùng thư viện, tự viết solver | một phần | Engine Python, dependency không đổi; A* có trên nền, solver tham khảo tách riêng | BFS/DFS/UCS chưa viết | Solver thuộc thành viên, không sửa lần này |
| §§2.1–2.4; §3.1 core (10) | Grid, ba tư thế, bốn hướng, rơi/thắng | hoàn thành | block.py, rules.py, Problem/Controller; test_all_basic_rolls; headless màn 1; offscreen thắng/rơi | Nghiệm thu thao tác GUI nằm ở hàng riêng | Engine trong phạm vi |
| §2.5; §3.1 advanced (10, chung) | Fragile đầy đủ đứng/nằm; cube đơn | hoàn thành | rules.supported; test_fragile_full_lying_standing_and_cube, test_fragile_break_reset_and_block_hash; reset giữ fragile | Hiệu ứng vỡ/rơi cần quan sát GUI | Engine trong phạm vi; QA xác nhận cube không vỡ |
| §2.5 bridges | Cầu ban đầu mở/đóng, reset từng màn | hoàn thành | Schema 2, Board.addBridgeGroup/reset; test_initial_closed_and_repeated_reset; loader 14 màn | Không suy ra mọi màn đều có lời giải | Trong phạm vi |
| §2.5 soft/heavy | Điều kiện trọng lượng và kích hoạt | hoàn thành | rules.pressed; test_soft_heavy_and_fixed_effect_modes, test_cube_cannot_win_or_press_heavy_or_split | Giữ áp lực qua lượt là quyết định triển khai công khai, không phải quy định thêm của GV | Trong phạm vi |
| §2.5 toggle/permanent | TOGGLE, OPEN, CLOSE; nhiều liên kết | hoàn thành | Một bridge ID dùng chung; test_multiple_bridges_shared_state_and_ordered_effects; test màn 5; mode test cả mở/đóng | Xung đột cùng bước dùng thứ tự tọa độ, cần review quy ước nhóm | Trong phạm vi |
| §§2.3,2.5 | Cầu đóng dưới khối, kiểm tra hỗ trợ cuối | hoàn thành | test_bridge_closes_under_inactive_cube, test_switch_removing_support_matches_controller | Không có cơ chế khác ngoài schema mô tả | Trong phạm vi |
| §2.5 split | Đứng kích hoạt, teleport, hai cube | hoàn thành | Block.split, rules.transition; test_split_requires_standing; test_split_teleport_and_control_identity; màn 12 được A* h=0 giải/replay | Không teleport dây chuyền; nguồn không yêu cầu | Trong phạm vi |
| §2.5 splitting; contract §3 | Điều khiển một cube, SWITCH, tự ghép | hoàn thành | SWITCH=5, actions phụ thuộc split; test_no_reactivation_on_switch_or_continued_occupancy, test_rejoin_both_axes_overlap_and_bounds, controller fixture có SWITCH | Chưa kiểm chứng heuristic theo cấu trúc split | Engine trong phạm vi, heuristic thuộc người 5 |
| §2.4, §2.5; QA | Cube không thắng, không heavy/split, fragile an toàn | hoàn thành | test_cube_cannot_win_or_press_heavy_or_split; test_teleport_cannot_chain_or_press_heavy_and_adjacent_rejoin; fragile tests | GUI manual cần nghiệm thu | Trong phạm vi |
| Contract §§4–5; §3.1 state | Copy/hash đủ thông tin; engine thuần, controller đồng nhất | hoàn thành | State.copy/equality/hash gồm cubes/active/bridge/rule metadata; test_deepcopy_sibling_keys_and_static_rule_metadata; fixture controller split và ví dụ headless bốn màn | State còn mutable: phải tuân thủ không sửa khóa và dữ liệu lồng | Trong phạm vi |
| §3.4; contract §9 | Chi phí dùng chung, unit cost, SWITCH dương | hoàn thành | Problem.step_cost = 1 + λ·I(fragile), unit_cost=True; SWITCH=1; kiểm chứng total_cost sau solve | Giải thích lựa chọn cost trong báo cáo chính thức, chưa benchmark UCS | Engine trong phạm vi; báo cáo/UCS người khác |
| §3.1 GUI; QA Solve | Hiển thị mọi ô, hai cube, điều khiển, tự phát lời giải | một phần | view.py giữ GUI/menu; thêm New Game, Restart, Space, marker; 6 test GUI mock; examples.gui_smoke offscreen chạy thật; playback chờ finishStep | Chưa nghiệm thu cửa sổ trực tiếp, focus/độ mượt/khả năng đọc; nội suy đơn giản, không quay vật lý | GUI trong phạm vi; nghiệm thu thủ công còn lại |
| Contract §11 | Snapshot, hủy callback khi reset/đổi màn, kiểm chứng replay | hoàn thành | test_snapshot_independent_and_bad_solution_not_replayed; test_restart_cancels_calls_and_animations_restores_split; test_change_level_cancels_old_calls_and_clears_split; validate_solution ngoài khoảng đo | Tìm kiếm đồng bộ, không có cancel khi solve đang chạy | Trong phạm vi; async/cancel hạng mục riêng |
| §3.1 JSON | Dữ liệu cũ/mới, báo lỗi rõ, schema | hoàn thành | loadLevelFromJson; test_loader_rejects_invalid_data, test_all_levels_and_legacy_shared_bridge_fix; LEVEL_SCHEMA.md | Metadata level_id cũ không dùng để điều hướng; không sửa hàng loạt | Trong phạm vi |
| Yêu cầu lần sửa; §3.6 fixed tests | Ít nhất 10 màn bao phủ cơ chế | một phần | 14 màn đã giải/verify/replay, 24 switch có witness kích hoạt đổi cầu/tách, không còn switch trang trí; test_level_links.py | Bộ benchmark cố định đủ khó/chung mọi thuật toán chưa chốt; thay đổi dữ liệu cần chạy lại thực nghiệm | Hoàn thiện dữ liệu trong phạm vi; thực nghiệm nhóm còn lại |
| §3.2 (10) | BFS và số liệu | chưa triển khai | search/bfs.py hiện ném NotImplementedError; registry không fallback | Thuật toán, test, tích hợp và thực nghiệm | Thành viên 1, được bảo vệ |
| §3.3 (10) | DFS hoặc IDS, chống lặp | chưa triển khai | search/dfs.py hiện là khung | Thuật toán, test, tích hợp và thực nghiệm | Thành viên 2, được bảo vệ |
| §3.4 (10) | UCS và số liệu | chưa triển khai | search/ucs.py hiện là khung | Thuật toán, test và đối chiếu chi phí tối ưu | Thành viên 3, được bảo vệ |
| §3.5 (10) | A* + heuristic thích hợp, lập luận admissible/consistent | một phần | A* nền c237d10, 8 test hiện có pass; chạy h=0 bốn màn; solver/heuristic không sửa | Heuristic khác zero chưa có/chưa kiểm chứng split, teleport, cost; h=0 chưa thay thế phần giải thích thiết kế heuristic | Thành viên 4/5; lớp điều phối chỉ chặn heuristic chưa xác minh trên split |
| §§3.2–3.5; contract §10 | Đo thời gian/bộ nhớ/node/độ dài | một phần | runner đo solve, trả nguyên RunResult; verify ngoài tracemalloc/thời gian; hiển thị số liệu console/GUI | Chưa có bảng so sánh tất cả solver trên benchmark | Runner dùng lại; thực nghiệm nhóm |
| §3.6 report (30: mô tả 10, thực nghiệm 20) | Phân công, thuật toán, benchmark, bảng/biểu đồ, nguồn, AI appendix | chưa triển khai | Tài liệu kỹ thuật có nguồn và quy tắc, không phải report nộp bài | Report.pdf, phân công đóng góp, thực nghiệm, biểu đồ, phân tích và AI appendix | Ngoài lần sửa engine |
| §3.7 video (10: GUI 5, tính năng 5) | Demo YouTube có thuyết minh/phụ đề | chưa triển khai | Không có bằng chứng video trong workspace đã kiểm tra | Quay sau nghiệm thu GUI; chèn link công khai trong report | Ngoài lần sửa engine |
| §4 submission | Đóng gói đúng tên/cấu trúc/giới hạn kích thước | chưa xác minh | Chưa tạo gói nộp | ZIP/RAR Source, Report.pdf và link video; loại venv/cache | Công việc cuối đồ án |

## Kết quả chạy và giới hạn

- Trước sửa: 23 test pass trên c237d10.
- Sau triển khai luật: 49 test pass; sau hoàn thiện liên kết: 53 test pass
  (venv Python 3.13.13), không sửa 8 test A*.
- Headless cũ: RIGHT RIGHT, goal=True, cost=2.
- A* h=0: màn 1: 2 bước/cost 2; 12: 7/6.5; 13: 4/4; 14: 4/4.
  Mọi bước hợp lệ, goal/cost được verify, controller khớp từng bước.
- Audit dữ liệu mở rộng: cả 14 màn và 24 witness switch pass bằng A* h=0;
  bảng số bước/cost đầy đủ tại LEVEL_COMPLETION.md, có chuỗi tái hiện và hash.
- Offscreen Ursina: start, lăn, thắng/rơi, restart, split, SWITCH, render chạy
  được. Không có thao tác quan sát GUI thủ công hoặc nghiệm thu chất lượng ảnh.
- Không đo/khẳng định admissibility của heuristic khác zero, độ khó của màn,
  tối ưu trên bộ benchmark đầy đủ hay hiệu năng so sánh các thuật toán.

Lỗi dữ liệu màn 5 được người dùng chấp nhận: `[6,15]` là '.', `[6,14]` là W;
chỉ sửa reference switch thành `[6,14]`, không đổi grid. Chi tiết tại LEVEL_SCHEMA.md.
