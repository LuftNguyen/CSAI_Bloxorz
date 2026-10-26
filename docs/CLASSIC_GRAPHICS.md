# Đồ họa cổ điển trên nền luật mới

Âm thanh: sàn đá, cầu kim loại, fragile/vỡ, công tắc, split/merge,
đổi cube, rơi, thắng và bẫy có cue riêng. Menu tạm dừng có SOUND ON/OFF.
Âm thanh được tổng hợp thành WAV bằng thư viện chuẩn; chỉ gọi từ view,
không phát trong engine/solver. Restart/đổi màn dừng tiếng cũ.
Smoke offscreen dùng audio null nên xác minh tích hợp, không xác nhận chất
lượng nghe thực tế. Cần nghe thử trên máy bằng main.py để đánh giá âm lượng.

Nhánh `feature/new-game-rules-classic-graphics` được tạo từ
`feature/new-game-rules`, commit `1e86deb`. Không áp dụng stash.
Bản đồ họa trên nền cũ được sao lưu tại `.source-import/classic-graphics-backup`
(thư mục được Git bỏ qua). Hai nhánh nguồn không có commit mới.

Chuyển phần trình bày từ bản đồ họa trước sang: nền đỏ cam có mây tối,
sàn đá cạnh vát và bóng mềm, khối kim loại gỉ, nút/menu màu đồng.
Fragile có vết nứt, công tắc nhẹ hình tròn, nặng hình X, split hai vạch tím.
Bẫy giữ dấu cảnh báo đỏ. Hốc đích tối có viền đồng. Texture tự sinh,
không trích từ ảnh tham khảo.

Giữ 10 màn, luật split/merge/SWITCH, cầu và bẫy, đếm ngược thua,
hiệu ứng thắng rơi/sàn biến mất, blackout 1 giây, replay 0,5 giây và
 di chuyển tức thời. Không sửa engine, dữ liệu màn, solver, heuristic hoặc
`animation_sync.py`. Camera giữ kiểm tra lens theo giới hạn cũ, đổi góc nhìn.

Hai test trình bày trong `tests/test_gui_rules.py` được cập nhật theo theme:
vạch split vật lý thay ký tự, viền hốc đồng thay xanh. Vẫn kiểm tra cầu
đóng, đúng một hốc đích, VOID không tạo sàn và board không bị sửa bởi render.

Chạy:

```powershell
.venv\Scripts\python.exe main.py
```

Kiểm tra:

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -q
.venv\Scripts\python.exe -B -m examples.gui_smoke
.venv\Scripts\python.exe -B -m examples.classic_preview --capture-dir (Join-Path $env:TEMP 'BloxorzClassicReview')
git diff --check
```

Smoke theme kiểm tra renderer offscreen thật, menu, di chuyển, HUD, reset và
A* phát lại tới màn sau. Ảnh đã được xem ở màn 5 và 8 của campaign mới.
Kết quả: 88 test pass; sau khi tăng độ chặt assertion cầu đóng, chạy lại
7 test GUI cũng pass. Smoke GUI thật qua 10 màn, camera 4 tỷ lệ và resize,
split/merge, OPEN/CLOSE, fragile/rơi/reset, A* replay, hủy callback cũ,
bẫy CLOSE/split đếm ngược thua, thắng rơi/sàn biến mất/blackout 1 giây.
`git diff --check` pass. Chưa nghiệm thu chơi desktop thủ công hoặc FPS.
