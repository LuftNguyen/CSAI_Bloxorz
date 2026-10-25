# Bàn giao phần luật mới — 23/10/2026

**Bổ sung hoàn thiện dữ liệu 24/10/2026:** theo yêu cầu tiếp theo, đã nối đủ
công tắc màn 1/8, sửa khoảng đỡ màn 6/13/14 và metadata màn 2. Có 14 lời giải
thắng và 24 witness kích hoạt tác dụng thực tế bằng A* h=0; 53 test pass.
Xem [LEVEL_COMPLETION.md](LEVEL_COMPLETION.md) và `levels/validation.json`.
Các con số 49 test/bốn màn và giới hạn dữ liệu phía dưới là lịch sử trước
lượt hoàn thiện này; solver/heuristic vẫn không sửa, không commit/push.

Rà soát cuối ngày **24/10/2026**: vẫn trên feature/new-game-rules, HEAD c237d10;
GUI offscreen chạy lại thành công. `git diff --check` không lỗi, index trống;
`git diff --exit-code HEAD -- search tests/test_astar.py docs/CONTRACT.md CSAI_Project.pdf`
trả 0. Solver/heuristic, test A* và contract gốc không thay đổi. Các kết quả
49 test/headless bên dưới là lần chạy cuối của phần triển khai, không chạy
lại toàn bộ chỉ vì đổi ngày; không có thay đổi mã mới trong lượt rà soát này.

## Nền và phạm vi

HEAD nền `c237d10` (A* reopening). Baseline trước sửa trên feature/astar có
23 test pass. Sau khi người dùng chủ động đổi nhánh và yêu cầu tiếp tục, mọi
việc thực hiện trên **feature/new-game-rules**, không chuyển nhánh bằng agent.
Không commit, push, merge, rebase, cherry-pick, fetch/pull, reset/restore/clean
hoặc đổi remote. Các thay đổi đang ở working tree để review.

Giữ nguyên docs/assignment/ASSIGNMENT.pdf và QA.md người dùng cung cấp; không
nhầm CSAI_Project.pdf (contract nhóm) với đề. Mọi thay đổi dở lúc tạm dừng được
giữ và tiếp tục, không khôi phục về bản cũ.

## Đã triển khai

- `gameModel/block.py`, `state.py`: giữ các lớp và bốn giá trị hướng; thêm
  SPLIT, SWITCH=5, hai tọa độ cube và active; copy/equality/hash đủ metadata.
- `gameModel/rules.py`: logic chung thuần Python cho Problem và Controller,
  fragile, tác động cầu, entry activation, split/teleport/SWITCH/ghép, kiểm tra
  hỗ trợ trước/sau tương tác. Controller giữ trạng thái thua cho hình ảnh.
- `gameModel/board.py`: ID cầu tách switch, một cờ cầu cho nhiều switch,
  TOGGLE/OPEN/CLOSE và cấu hình ban đầu; reset khôi phục đúng tiles/cờ cầu.
- `problem.py`, `gameController.py`: dùng chung transition, giữ năm giao diện
  Problem; cost cũ và unit_cost còn nguyên, thêm SWITCH=1.
- `levels/levelLoader.py`: legacy/schema 2, kiểm tra dữ liệu và báo lỗi rõ;
  nhóm cầu legacy có cùng tập tiles dùng chung cờ. `levelManager.py` giữ đường
  dẫn module, thêm 12–14 là demo riêng. Không thay bộ benchmark cũ bằng demo.
- `view.py`, `inputHandler.py`: Space điều khiển cube, hai cube và active màu
  vàng; phân biệt switch/cầu đóng; New Game/Restart/menu Solver; nội suy đơn
  giản và chờ finishStep; hủy timer/animation khi reset/đổi màn; snapshot độc lập.
- `runner.py`: verify lời giải ngoài phần đo solve; chặn heuristic chưa kiểm
  chứng với split/teleport, GUI dùng None=h=0. Không đổi RunResult/SearchResult/
  SearchLimits hoặc sửa công thức heuristic.
- `tests/test_rules.py`, `test_gui_rules.py`: test luật/loader/replay/GUI mới.
  Một dòng test nền đổi từ list(Direction) thành bốn hướng ở state chưa split;
  lý do: contract chỉ cho SWITCH sau khi tách. Không sửa test thuật toán.
- `examples/rules_headless.py`, `gui_smoke.py`: tái hiện kiểm tra tích hợp và
  offscreen. `.gitignore` bổ sung cache Panda3D phát sinh trong smoke test.

**Lỗi màn 5 đã được người dùng xác minh và chấp nhận:**
`grid[6][14] == 'W'`, `grid[6][15] == '.'`. Reference switch cũ `[6,15]` trỏ sàn;
đã sửa thành `[6,14]`. Không đổi grid. Có test kiểm tra trực tiếp hai ký tự và
hai switch cùng trỏ một cờ cầu. Đây là sửa dữ liệu, không đổi luật/độ khó màn.

Quyết định cho chỗ nguồn chưa nêu: switch mới được đè mới kích hoạt, thứ tự
tác động đồng thời theo tọa độ, soft tại đích teleport kích hoạt một lần,
không heavy/split dây chuyền. Chi tiết và cơ sở tại GAME_RULES.md; schema và
ví dụ tại LEVEL_SCHEMA.md. Các quy ước này cần review nhóm, không được diễn
giải như giảng viên đã chốt chi tiết đó.

## Kiểm tra đã chạy

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m examples.headless
.venv\Scripts\python.exe -m examples.rules_headless
.venv\Scripts\python.exe -m examples.gui_smoke
.venv\Scripts\python.exe -m compileall -q gameModel levels runner.py view.py inputHandler.py examples tests
git diff --check
git status --short
```

- Tự động: **49 phương thức test pass**, có subtest/vòng lặp. 8 test A* của
  thành viên giữ nguyên, không có lỗi solver/stub cần né hoặc sửa test thuật toán.
- Headless cũ: màn 1 RIGHT RIGHT, goal=True, cost=2.
- A* thật trên nhánh hiện tại, heuristic=None (h=0), verify rồi controller replay:

| Màn | Số hành động | Tổng chi phí | Kết quả |
| --- | --- | --- | --- |
| 1 | 2 | 2.0 | goal/cost/controller khớp |
| 12 (split demo) | 7 | 6.5 | goal/cost/controller khớp |
| 13 (closed/OPEN/CLOSE demo) | 4 | 4.0 | goal/cost/controller khớp |
| 14 (TOGGLE/multiple bridges demo) | 4 | 4.0 | goal/cost/controller khớp |

SWITCH được kiểm riêng bằng fixture controller và GUI, không tuyên bố các lời
giải A* trên bắt buộc dùng SWITCH. Không tự viết solver hoặc lấy mã nhánh khác.

- Ursina thật **offscreen** chạy được: Start, di chuyển, thắng/rơi, restart,
  split/SWITCH và dựng cảnh. Cảnh báo framebuffer/color profile không làm lỗi.
- **Chưa chạy GUI thủ công** bằng người quan sát, chưa nghiệm thu focus bàn
  phím, màu/marker, độ mượt, trải nghiệm New Game/menu trên cửa sổ. Mock và
  offscreen không thay thế checklist tại TESTING.md.

## Phần còn lại và thứ tự đề nghị

1. Review quy tắc tương tác/chi phí/schema mới, rồi người dùng kiểm tra GUI
   trực tiếp (fragile/cầu/tách/ghép/Space/restart giữa phát lại). Hoạt ảnh hiện
   chỉ nội suy position/scale, không quay khối chính xác vật lý.
2. Engine/GUI: tìm kiếm còn đồng bộ, chưa có cancel trong solve; thiết kế
   thread/process nếu nhóm cần là hạng mục riêng. Kiểm tra đầy đủ mọi màn nguồn
   có lời giải; các demo mới không chứng minh điều đó.
3. Thành viên tiếp tục BFS/DFS/UCS và heuristic. A* hiện chạy h=0 trên luật mới;
   heuristic khác zero cần người phụ trách kiểm chứng lại với split/teleport/cost.
4. Chốt bộ benchmark cố định >=10 màn bao phủ cơ chế, cùng chi phí/limits;
   kiểm tra lời giải tất cả solver rồi đo/bảng/biểu đồ. Không coi bốn màn ví dụ
   hoặc 49 test là benchmark hay điểm nghiệm thu đồ án.
5. Viết Report.pdf, đóng góp/phân công, phân tích thuật toán/heuristic, nguồn và
   AI appendix; quay video có thuyết minh/phụ đề, link YouTube; đóng gói theo đề.

Phân loại từng yêu cầu, điểm nguồn và bằng chứng ở REQUIREMENTS_STATUS.md.
Git cuối: thay đổi mã/tài liệu và tệp mới còn unstaged; docs/assignment/ vẫn
untracked như lúc bắt đầu. Không sửa search/bfs.py, dfs.py, ucs.py, astar.py,
heuristics.py, solver.py, thuật toán tham khảo hoặc tests/test_astar.py.
