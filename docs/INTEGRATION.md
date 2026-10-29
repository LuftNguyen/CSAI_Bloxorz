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
  so chi phí UCS/A* h=0, kiểm tra state nguồn không đổi, kiểm tra runner chặn
  heuristic chưa xác minh cho split và chấp nhận zero.
- Cập nhật README và báo cáo này; không thay thuật toán hoặc contract.

## Heuristic chưa nghiệm thu — giao lại người phụ trách

Mã và `tests/test_heuristics.py` của thành viên giữ nguyên, không skip, không sửa
assertion để làm xanh test. Discovery toàn suite có thể thất bại ở phần này:

1. Vòng dựng relaxed duyệt `Direction.SWITCH` cho khối chưa split gây ValueError.
2. Fallback kiểm tra tồn tại r/c/dr/dc không nhận diện `Block.split()` thật.
3. Manhattan và relaxed chưa bảo đảm admissible/consistent với teleport.
   Đã tái hiện Manhattan không consistent ở campaign 8–10; trên một màn teleport
   kiểm chứng riêng, cost tối ưu 5 nhưng Manhattan trả 12,5.
4. Test heuristic được viết cho engine/11 màn cũ; cần người phụ trách cập nhật
   phạm vi chứng minh và kiểm thử theo engine/campaign mới.

GUI tiếp tục truyền `heuristic=None` (h=0). Runner giữ chặn heuristic khác zero
trên màn có splitTargets. Không bỏ chặn hoặc thay heuristic bằng một bản tự viết.
Giới hạn còn lại: lời gọi trực tiếp solver hoặc truyền heuristic trên màn không
split vẫn là trách nhiệm bên gọi; relaxed hiện chưa dùng được với enum mới.

## Kiểm tra

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_solver_integration.py -v
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_heuristics.py -v
.venv\Scripts\python.exe -B -m examples.classic_preview
git diff --check
```

Chưa nghiệm thu desktop hoặc benchmark. Thành viên nên tạo nhánh sửa của mình
từ baseline main đã tích hợp, không lấy lại nguyên test nền cũ khi merge lần sau.

Kết quả sau merge: 155 test ngoài `test_heuristics.py` pass trong một lần
discovery chọn riêng phạm vi tích hợp. Bao gồm cả ba test tích hợp mới, bốn
solver giải/replay đủ 10 màn, UCS/A* h=0 cùng cost. Đây không phải tuyên bố
toàn suite xanh: test heuristic được chạy riêng, giữ nguyên mọi assertion.
Smoke `examples.classic_preview` pass menu, âm thanh ON/OFF, input/restart và
A* replay sang màn; `git diff --check` pass. Không chạy desktop thủ công.

Nhóm heuristic giữ nguyên chạy đủ 12 test trong 290 giây: 6 failure, 43 error
(bao gồm subtest, không phải 49 test method). Cả 43 error là ValueError khi
dựng relaxed gặp SWITCH; sáu failure là Manhattan không consistent tại campaign
8/9/10 trong hai chế độ cost. Log thô ở `.source-import/heuristic-integration-review.log`
chỉ lưu local, không commit. Chạy riêng không bỏ qua hoặc sửa test heuristic.
Vì vậy baseline tích hợp chơi được với h=0 nhưng toàn suite CHƯA xanh.
