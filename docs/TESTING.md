# Cài đặt và kiểm tra

## Camera, split bẫy và chuyển cảnh nhanh — 26/10/2026

88 test pass, 254 subtest, 0 skip. Smoke kiểm tra 10 màn × 4 tỉ lệ lens và
resize refit, split bẫy đếm 5 giây/reset, wave nhanh và cancellation trên frame
thật. Xem [CAMERA_SPLIT_SPEED.md](CAMERA_SPLIT_SPEED.md). Số liệu dưới là lịch sử.

## Chuyển cảnh thắng màn — kết quả mới nhất

85 test pass, 251 lượt subtest, 0 skip. Goal fall thật, cả bàn rơi/co dần theo làn sóng,
blackout 1 giây rồi next level; dùng chung manual/replay và hủy được khi reset.
Smoke đo framebuffer đen và đã xem ảnh rơi/đen/màn mới.
Xem [WIN_TRANSITION.md](WIN_TRANSITION.md); số test thấp hơn dưới đây là lịch sử.

## Permanent CLOSE gây thua — kết quả mới nhất

82 test pass, 243 lượt subtest, 0 skip. Sáu nút có `!` gây thua ngay trong
model; GUI đếm 5 giây, báo YOU LOSE 1 giây rồi reset. Smoke frame clock và
ảnh HUD đã xác nhận. Xem [FATAL_CLOSE.md](FATAL_CLOSE.md). Các số test thấp
hơn trong phần dưới là lịch sử; solver/heuristic không sửa.

## Bộ 10 màn hiện hành

Đã mở rộng từ hành lang thành phòng/đảo nhiều nhánh: lời giải 10–26 bước,
99–2467 node A* h=0. Giới hạn audit tăng lên 60 giây/query; test đúng/sai dùng
solver từ registry không tracemalloc, audit manifest vẫn dùng runner đo bộ nhớ.
Xem [bản đồ 10 màn](CAMPAIGN_MAPS.svg). 73 test pass; smoke GUI đã xem ảnh màn 7/10.

Xem [CAMPAIGN.md](CAMPAIGN.md): 73 test pass, 236 lượt subtest, 0 skip;
10 lời giải, 37 witness kích hoạt, 27 truy vấn vô nghiệm chứng minh cơ chế bắt buộc.
`python -B -m examples.gui_smoke` phát đủ 10 màn qua input GUI offscreen,
giữ di chuyển tức thời và replay 0,5 giây. Chưa nghiệm thu desktop thủ công.
Các kết quả 14 màn/24 witness và số test trong phần dưới là lịch sử.

## Bản di chuyển tức thời 25/10/2026

Theo yêu cầu mới, ordinary move không còn nội suy hay chờ 0.4 giây; các kết
quả đồng bộ nội suy ở phần sau là lịch sử. Lượt hiện tại: 11 test visual sync,
6 test GUI rules và toàn bộ **64 test pass, 0 skip**. Smoke offscreen với
`--capture-dir (Join-Path $env:TEMP 'BloxorzInstantMoveReview')` cũng pass;
đã xem ảnh trước/sau bước mở cầu, chưa nghiệm thu desktop thủ công.
Xem [ANIMATION_SYNC.md](ANIMATION_SYNC.md) cho luồng mới, lệnh và giới hạn.

## Đồng bộ hoạt ảnh 25/10/2026

Đã khôi phục WIP 72d7016 trên feature/new-game-rules và sửa riêng phần trình
bày; stash được giữ. Baseline 53 pass, sau sửa **63 test pass, 0 skip**.
Có test với Sequence thật của Ursina 8.3.0, không chỉ gọi callback thủ công.
`python -m examples.gui_smoke` nay dùng frame clock và poll animator thật,
kiểm tra 1/60 và 0.1 giây/frame; không dùng finishStep() để bỏ qua thời lượng.
Xem [ANIMATION_SYNC.md](ANIMATION_SYNC.md) cho cơ chế, lệnh chạy và checklist.
Đã xem ảnh offscreen trước/sau arrival; chưa nghiệm thu chơi trực tiếp desktop.

## Hoàn thiện liên kết màn 24/10/2026

Đã chạy `python -m examples.audit_levels --write`: **14 màn có lời giải và
24 công tắc có witness kích hoạt làm đổi cầu/tách khối**, đã verify cost/goal
và controller replay. `levels/validation.json` gắn với hash từng JSON.
Unittest hiện **53 phương thức test pass**; bốn test mới trong
`tests/test_level_links.py` chỉ phát lại witness, không chạy thuật toán tìm kiếm.
Kết quả 49 test/bốn màn trong phần dưới là lịch sử lượt triển khai luật.

```powershell
.venv\Scripts\python.exe -m examples.audit_levels
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Sau khi sửa JSON màn, cập nhật witness bằng `python -m examples.audit_levels --write`
rồi chạy test. Không dùng witness cũ hoặc so benchmark giữa các phiên bản dữ
liệu khác nhau. Chi tiết những ô/liên kết đổi và cách thử màn 1:
[LEVEL_COMPLETION.md](LEVEL_COMPLETION.md). GUI offscreen smoke chạy lại pass;
GUI tương tác thủ công vẫn chưa nghiệm thu.

## Cập nhật luật 23/10/2026

Nền `c237d10`, nhánh làm việc `feature/new-game-rules`. Lần cập nhật này không
commit/push hoặc thao tác nhánh khác. Các kết quả 13–15 test ở phần lịch sử
bên dưới là của bản nền cũ, không phải số test hiện tại.

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m examples.headless
.venv\Scripts\python.exe -m examples.rules_headless
.venv\Scripts\python.exe -m examples.gui_smoke
```

Kết quả thực tế: **49 phương thức test pass**, gồm 8 test A* sẵn có giữ nguyên,
14 test nền, 1 input GUI, 6 test GUI orchestration mới và 20 test luật/loader/
replay mới. Các vòng lặp và subtest bao phủ nhiều hơn 49 tình huống.
Headless cũ vẫn thắng màn 1, cost=2.0. Headless luật mới gọi đúng A* hiện có,
h=0: màn 1 (2 bước, cost=2), màn 12 (7 bước, cost=6.5), màn 13/14 (4 bước,
cost=4). Mọi lời giải được kiểm chứng goal/cost và phát lại khớp controller.
Các con số này chỉ là kiểm tra kết nối, không phải benchmark so sánh thuật toán.

`examples.gui_smoke` tạo Ursina offscreen và chạy start, lăn, thắng/rơi, restart,
split, SWITCH, dựng cảnh. Đã chạy thành công, không mở cửa sổ thao tác trực tiếp.
Có cảnh báo framebuffer/color profile của Panda3D, không có lỗi runtime.
Test GUI còn lại dùng mock/timer giả; không chứng minh hình ảnh, độ mượt hoặc
keyboard focus trên mọi máy. `rules_headless` dùng thư viện chuẩn; hai kiểm tra
GUI cần requirements.txt như nguồn, không thêm dependency mới.

Chỉ sửa một kỳ vọng trong `test_foundation.py`: actions ở trạng thái chưa tách
phải là bốn hướng, không phải toàn bộ enum nữa vì enum đã thêm SWITCH. Đây là
thay đổi luật theo contract §3, không phải né test thuật toán. Không sửa
`tests/test_astar.py` hoặc solver/heuristic.

## Checklist thủ công bổ sung (chưa nghiệm thu)

- [ ] `main.py`: Start, lăn cả ba tư thế, New Game, R/P, menu Solver; A* giải
  màn 1 và tự phát tới đích; BFS/DFS/UCS vẫn báo chưa triển khai, không khóa game.
- [ ] Thử fragile: nằm được đỡ; đứng vỡ ô và rơi; restart khôi phục; cube đơn
  đứng fragile không vỡ theo QA.
- [ ] Next Level tới 12 (hoặc chọn currentLevel=12 trong phiên debug, không
  sửa dữ liệu benchmark): phải hai lần để split, Space đổi cube và đổi màu vàng;
  một cube đứng yên trên soft không bị kích hoạt lại; ghép kề cạnh đúng.
- [ ] Màn 13/14: cầu đóng hiển thị tấm mỏng tối màu, cầu mở nâu; soft o,
  heavy X, split ( ) phân biệt; quan sát tác động OPEN/CLOSE/TOGGLE.
- [ ] Restart/New Game/Next Level giữa hoạt ảnh hoặc phát lại không còn callback
  cũ tác động lên màn mới; hai cube ẩn sau reset/đổi màn.
- [ ] Đối chiếu snapshot/replay không lệch trạng thái game; không có lời giải
  sai được hiển thị solved. Tìm kiếm đồng bộ có thể đứng cửa sổ; chưa có cancel.

Chi tiết luật và schema: [GAME_RULES.md](GAME_RULES.md),
[LEVEL_SCHEMA.md](LEVEL_SCHEMA.md). Hạng mục còn thiếu và trách nhiệm:
[REQUIREMENTS_STATUS.md](REQUIREMENTS_STATUS.md).

## Lịch sử kiểm tra bản nền ban đầu

Chạy PowerShell tại thư mục repository. Đã kiểm tra Python 3.13.13 Windows.
Headless và unittest chỉ dùng thư viện chuẩn, không cần Ursina.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m examples.headless
.venv\Scripts\python.exe main.py
```

Dependency giữ nguyên bản ghim của nguồn. Không cần activate venv.
`python -m unittest discover -s tests -v` và `python -m examples.headless`
cũng chạy được với Python hệ thống mà không cài dependency GUI.

## Kết quả thực tế của bản nền

Ngày 20/10/2026: bản nền ban đầu chạy 13 phương thức test OK trên cả Python
hệ thống và venv Python 3.13.13. Sau bổ sung kiểm thử reset: 14 phương thức test,
gồm 27 lượt subtest tường minh (12 chuyển tư thế, 4 solver và 11 màn reset).
headless kết thúc ở goal, cost=2.0. Cài đủ requirements.txt thành công,
`pip check` báo `No broken requirements found`. Import `view` thành công;
compileall của engine/search/loader/GUI thành công. Một kiểm tra có mock không
mở cửa sổ đã xác nhận GUI adapter xử lý khung chưa triển khai, snapshot độc lập,
lên lịch lời giải, hủy phát lại và timeout. Đây không phải kiểm tra tương tác GUI.
Chưa chạy game bằng cửa sổ hoặc đánh dấu checklist thủ công bên dưới.

## Kết quả mong đợi

- Unittest: 15 phương thức test OK khi đã cài dependency GUI; nếu chưa cài,
  14 test nền pass và 1 test nối input GUI được skip. Bao gồm 12 chuyển tư thế, sao chép sâu cả dữ liệu lồng,
  nhánh độc lập, bridgeState khác khi tiles giống, equality/hash, goal đầy đủ,
  rơi sau switch, chi phí, replay/controller/reset, loader 11 màn, input,
  registry và đo runner (kể cả exception, trace có sẵn và gọi lồng).
  Số phương thức test không phải số tình huống: ngoài subtest còn có vòng lặp
  kiểm tra bốn status, ba giới hạn không hợp lệ và reset hai lần mỗi màn.
- Headless: thứ tự UP DOWN LEFT RIGHT; UP/LEFT trả None; DOWN/RIGHT hợp lệ,
  cost=1; `replay: RIGHT RIGHT; goal=True; cost=2.0`;
  `team solver: BFS chua trien khai (search/bfs.py)` là kết quả đúng của khung.
- Fake solver trong test chỉ xác minh truyền tham số, bốn status và cấu trúc đo;
  không chứng minh timeout hay thuật toán thực sự hoạt động.

Các tên test trong `tests/test_foundation.py`, cũng hiển thị khi chạy với `-v`:

| Lớp | Phương thức test |
| --- | --- |
| EngineTests | test_nested_copy_and_sibling_independence |
| EngineTests | test_equality_hash_dynamic_bridges_and_orientation |
| EngineTests | test_all_basic_rolls |
| EngineTests | test_invalid_moves_and_complete_goal |
| EngineTests | test_switch_removing_support_matches_controller |
| EngineTests | test_loader_replay_cost_and_reset |
| EngineTests | test_level_files_and_end |
| EngineTests | test_reset_restores_loaded_bridge_configuration |
| EngineTests | test_keyboard_routes |
| RunnerTests | test_registry_stubs_never_fallback |
| RunnerTests | test_runner_passes_contract_and_measures |
| RunnerTests | test_errors_cleanup_and_invalid_limits |
| RunnerTests | test_existing_trace_is_preserved_and_nested_run_rejected |
| RunnerTests | test_headless_does_not_import_ursina |
| GuiInputTests (test_gui_input.py) | test_dispatcher_preserved_and_entity_receives_press_once |

Sau sửa lỗi nhận phím: 15 test pass trong venv. Test GUI dùng mock, không mở
cửa sổ: xác nhận giữ nguyên Ursina.input, đăng ký Entity.input, phím nhấn di
chuyển một lần, nhả phím không di chuyển và P/R không kích hoạt hai lần.
Không gán đè app.input vì làm mất đường phân phối và chuẩn hóa sự kiện Ursina.

## Checklist thủ công trong GUI (chưa chạy)

- [ ] Start Game mở màn 1; WASD/mũi tên điều khiển được, nhả phím không lăn thêm.
- [ ] Lăn đứng, nằm ngang, nằm dọc đúng hình học; đối chiếu test_all_basic_rolls.
- [ ] Màn 1: RIGHT RIGHT thắng và sang màn kế; đi khỏi sàn thì rơi và restart.
- [ ] R restart đúng vị trí và board; P/menu pause đúng; kiểm tra không kích hoạt
  hai lần với sự kiện nhấn/nhả phím tiện ích của Ursina trên máy đang dùng.
- [ ] Chọn BFS/DFS/UCS: thấy thông báo chưa triển khai, điều khiển mở lại;
  A* hiện có phải tìm và phát lời giải hợp lệ.
- [ ] Khi solver thật tích hợp: phát từ đúng trạng thái lúc gọi, mỗi bước xong mới
  sang bước tiếp; đối chiếu goal và tổng step_cost với kết quả solver.
- [ ] Restart/Next Level khi phát lại hủy callback cũ, không đi thêm bước vào màn mới.
- [ ] Kiểm tra switch/bridge/fragile, thắng/rơi và reset sau thay đổi luật.

## Khoanh vùng lỗi

| Biểu hiện | Kiểm tra |
| --- | --- |
| Lăn/ô hợp lệ sai cả headless và GUI | gameModel/block.py, problem.py, gameController.py |
| Cha hoặc nhánh khác đổi theo, set nhận sai state | state.py copy/equality/hash và dữ liệu Board lồng |
| Màn không đọc được, kích thước sai | levels/levelLoader.py, JSON, levelManager.py |
| Sai status/đường đi/counters/timeout | solve() của thành viên và quy tắc contract §§7–10 |
| Sai thời gian/bộ nhớ, trace còn bật | runner.py; không đo đồng thời trong tiến trình |
| Headless đúng nhưng hình/phím/replay sai | view.py, inputHandler.py, menu.py |

Chưa thể xác nhận: tối ưu BFS/UCS với unit cost; UCS/A* cùng chi phí;
A* h=0 tương đương UCS; admissibility/consistency heuristic; timeout/node limit
thực của từng thuật toán; benchmark và luật nâng cao chưa có. Khi solver thật
được tích hợp, thêm kiểm thử các điều kiện nghiệm thu §13 của contract.

## Remote nhóm và chia nhánh

Repository nhóm Public: https://github.com/LuftNguyen/CSAI_Bloxorz.
Repo được tạo trống, không khởi tạo README/license/gitignore, sau đó nhận
lịch sử local main. `origin` là repo nhóm; `upstream` là repo nguồn.
Nếu cần cấu hình một bản local khác chưa có origin:

```powershell
git remote add origin https://github.com/LuftNguyen/CSAI_Bloxorz.git
git remote -v
git status
git log --oneline -3
git push -u origin main
```

Nếu remote đã có commit, fetch và review
trước khi tích hợp; không force-push hoặc dùng chuỗi lệnh trên để ghi đè.
URL trong lệnh Git phải là URL thuần như ví dụ, không bọc cú pháp link Markdown.

Sau khi main được review, kiểm tra GUI và push, từng thành viên chạy:

```powershell
git clone https://github.com/LuftNguyen/CSAI_Bloxorz.git
cd CSAI_Bloxorz
git switch main
git pull --ff-only origin main
git switch -c feature/bfs
```

Tên nhánh tương ứng: `feature/bfs`, `feature/dfs`, `feature/ucs`,
`feature/astar`, `feature/heuristics`. Mỗi người chỉ sửa phần được giao;
State/Problem/contracts/runner/registry cần người duyệt chung. Không merge
nhánh khác vào main trước review và kiểm thử tích hợp.
