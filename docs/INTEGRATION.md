# Baseline tích hợp thành viên

Tích hợp trực tiếp trên `main` local theo yêu cầu. Không push trong lượt tích hợp.
Lịch sử merge giữ nguyên commit và tác giả của từng nhánh:

| Phần | Nhánh / commit nguồn |
| --- | --- |
| Luật, 10 màn, GUI cổ điển, âm thanh | feature/new-game-rules-classic-graphics / 66f1b54 |
| BFS | chau/bfs / 4b3cb35 |
| DFS | quyen/dfs / f76ca39 |
| UCS | feature/ucs / 9be103c |
| A* (đã có trong nền) | feature/astar / c237d10 |
| Heuristic | huong/heuristics / 283ec5f |

Không sửa `search/{bfs,dfs,ucs,astar,heuristics}.py`. Các tệp này được đối chiếu
bằng `git diff` với commit nguồn, không có khác biệt. Không thao tác stash hoặc
merge/push nhánh `feature/classic-graphics` cũ.

## Chỉnh sửa thuộc trách nhiệm tích hợp

- Xung đột của BFS/DFS/UCS đều ở test registry trong `tests/test_foundation.py`.
  Thay kiểm tra stub bằng kiểm tra đúng solver thành viên, alias A*, kết quả
  initial-goal và giải phóng tracemalloc. Giữ các test nền/luật đã cập nhật.
- Test UCS `test_level_one_loaded_solution_replays` vẫn kỳ vọng 2 bước/cost 2;
  chuyển đường dẫn sang `tests/fixtures/legacy/level1.json`. Không đổi kỳ vọng
  hoặc cách cài UCS. Campaign 1 mới có bố cục và lời giải khác.
- Thêm `tests/test_solver_integration.py`: replay bốn solver trên 10 màn,
  so chi phí UCS/A* h=0, kiểm tra state nguồn không đổi, kiểm tra A* với `manhattan` và `relaxed` trên màn 8, 9 cho chi phí bằng UCS, và runner chấp nhận zero trên split.
- Cập nhật README và báo cáo này; không thay thuật toán hoặc contract.

## Heuristic

Bốn lỗi từng ghi ở đây (SWITCH khi dựng relaxed, fallback không nhận `Block.split()`,
Manhattan không consistent với teleport, test viết cho engine cũ) đã được sửa trong
commit `dbd9ca9` và các commit heuristic trước đó.

- `tests/test_heuristics.py` pass trên 10 màn, cả `unit_cost` True/False: heuristic
  admissible và consistent so với h* tính bằng duyệt toàn bộ không gian trạng thái.
- Chi phí tối ưu từ A* với `manhattan` và `relaxed` bằng UCS trên màn 8 (40.0) và
  màn 9 (18.5); test nằm ở `tests/test_solver_integration.py`.
- Runner chỉ chặn heuristic không có trong `search.heuristics.HEURISTICS` trên màn có
  splitTargets. Lời gọi trực tiếp solver vẫn là trách nhiệm của bên gọi.
- GUI tiếp tục truyền `heuristic=None` (h=0).

## Kiểm tra

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_solver_integration.py -v
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_heuristics.py -v
.venv\Scripts\python.exe -B -m examples.classic_preview
git diff --check
python -B -m unittest discover -s tests -v
```

Chưa nghiệm thu desktop hoặc benchmark. Thành viên nên tạo nhánh sửa của mình
từ baseline main đã tích hợp, không lấy lại nguyên test nền cũ khi merge lần sau.

Toàn suite: `Ran <N> tests in <T>s`, OK (skipped=<K>). Giới hạn số trạng thái trong test:
`STATE_CAP = 50_000` (tests/test_heuristics.py) và `max_expanded_nodes=30_000`
(tests/test_advanced_portfolio.py). Chưa nghiệm thu GUI thủ công hoặc benchmark.