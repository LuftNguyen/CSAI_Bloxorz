# Thắng màn: rơi vào goal rồi chuyển cảnh — 25/10/2026

Áp dụng chung cho chơi tay và replay solver, chỉ khi engine xác nhận hasWon:

1. Khối rơi thẳng xuống hốc bằng animate_y tới -3.5, duration danh nghĩa
   0,6 giây, curve.in_cubic. Không quay khối hoặc nội suy bước di chuyển thường.
2. Rơi xong mới cho **tất cả ô bàn** rơi và co dần, thay cho ẩn tức thời chỉ
   các ô đặc biệt. Cả sàn thường, cầu, fragile, switch và hốc goal tham gia.
   Độ trễ 0–0,65 giây theo khoảng cách Manhattan từ goal tạo làn sóng lan ra
   ngoài; mỗi ô rơi 6 đơn vị và co còn 5% trong 0,45 giây, curve.in_quad.
3. AnimationCompletion chờ mọi handle y/scale và setter cuối của ô xa nhất,
   rồi ẩn các Entity. Quad đen phủ toàn bộ board lẫn HUD, giữ **1 giây**
   tính từ lúc toàn bộ làn sóng hoàn tất, không bắt đầu sớm theo timer giả.
4. Hết blackout mới load màn tiếp theo; bỏ quad và hiển thị lại đầy đủ màn mới.
   Ở màn 10, hiện All levels completed thay vì tải tệp level11 không tồn tại.

Trong cả ba pha, input di chuyển và replay bị khóa. R/Restart hoặc đổi màn
hủy handle, clear countdown, tắt quad, phục hồi visibility/position/scale; callback
cũ có generation guard. Blackout chỉ là presentation state, không dùng làm
search state hoặc thay đổi timing/cost/goal của solver.

Màn cuối khôi phục khung cảnh goal có thông báo hoàn thành; New Game/Restart
vẫn dùng được. Phím di chuyển không ghi đè thông báo bằng lỗi invalid move.

## Kiểm chứng

- Sửa test GUI/visual cũ: không còn kỳ vọng timer chờ 2 giây hoặc replay nhảy
  màn ngay khi hết actions. Cả hai phải chờ rơi thật và đủ blackout.
- 3 test mới: cùng luồng manual/replay, không coi finished khi setter chưa chạy,
  engine state không đổi, độ trễ gần/xa, chờ cả scale setter, blackout đủ 1 giây;
  restart/đổi màn giữa fall/collapse/blackout với callback cũ, phục hồi pose;
  màn cuối không tải level11.
- Smoke frame clock thật: actual A* hai bước tới goal và sang màn; manual màn 7
  có mesh y âm khi đang rơi, rồi cùng lúc có ô đã rơi/co và ô xa chưa chuyển
  động; đã chụp ảnh làn sóng. Framebuffer đen có average gray
  dưới 0,001, giữ ít nhất nửa giây vẫn ở màn 7, rồi mới sang màn 8.
- Đã xem ảnh đang rơi, toàn màn đen và màn mới. Các ảnh ở thư mục tạm,
  không thêm ảnh sinh ra vào repository. Fatal CLOSE 5 giây/reset vẫn được
  smoke chạy lại trong cùng phiên. Chưa nghiệm thu desktop thủ công.
- Đã restart giữa làn sóng với Sequence/Entity thật, chạy thêm 180 frame:
  không chuyển màn ngoài ý muốn, mọi ô mới giữ nguyên position/scale/visibility.

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_win_transition.py -v
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_gui_rules.py -q
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_visual_sync.py -q
.venv\Scripts\python.exe -B -m examples.gui_smoke
.venv\Scripts\python.exe -B -m unittest discover -s tests -q
git diff --check
```

Không sửa engine, solver/heuristic, chi phí hoặc JSON màn trong lượt này.
Giữ kiểu di chuyển thường tức thời và khoảng nghỉ replay 0,5 giây.
Không commit/push, không đổi nhánh hoặc thao tác stash.

Kết quả toàn suite: **85 test pass, 251 lượt subtest, 0 failure/error/skip**.
