# Cài đặt và kiểm tra

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

- Unittest: 14 phương thức test OK: 12 chuyển tư thế, sao chép sâu cả dữ liệu lồng,
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

## Checklist thủ công trong GUI (chưa chạy)

- [ ] Start Game mở màn 1; WASD/mũi tên điều khiển được, nhả phím không lăn thêm.
- [ ] Lăn đứng, nằm ngang, nằm dọc đúng hình học; đối chiếu test_all_basic_rolls.
- [ ] Màn 1: RIGHT RIGHT thắng và sang màn kế; đi khỏi sàn thì rơi và restart.
- [ ] R restart đúng vị trí và board; P/menu pause đúng; kiểm tra không kích hoạt
  hai lần với sự kiện nhấn/nhả phím tiện ích của Ursina trên máy đang dùng.
- [ ] Chọn từng BFS/DFS/UCS/A*: thấy thông báo chưa triển khai, điều khiển mở lại.
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

## Tạo remote và chia nhánh

Hiện chỉ có local main và upstream; chưa có repository nhóm/origin.
Tạo repository **trống** trên GitHub bằng tài khoản nhóm, chọn tên và visibility
theo quyết định của nhóm, không khởi tạo README/license/gitignore. Sau khi có URL:

```powershell
git remote add origin https://github.com/TEAM/REPOSITORY.git
git remote -v
git status
git log --oneline -3
git push -u origin main
```

Thay TEAM/REPOSITORY bằng URL thực. Nếu remote đã có commit, fetch và review
trước khi tích hợp; không force-push hoặc dùng chuỗi lệnh trên để ghi đè.
URL trong lệnh Git phải là URL thuần như ví dụ, không bọc cú pháp link Markdown.

Sau khi main được review, kiểm tra GUI và push, từng thành viên chạy:

```powershell
git clone https://github.com/TEAM/REPOSITORY.git
cd REPOSITORY
git switch main
git pull --ff-only origin main
git switch -c feature/bfs
```

Tên nhánh tương ứng: `feature/bfs`, `feature/dfs`, `feature/ucs`,
`feature/astar`, `feature/heuristics`. Mỗi người chỉ sửa phần được giao;
State/Problem/contracts/runner/registry cần người duyệt chung. Không merge
nhánh khác vào main trước review và kiểm thử tích hợp.
