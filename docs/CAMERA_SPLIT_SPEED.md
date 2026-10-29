# Camera, split bẫy và chuyển cảnh nhanh — 26/10/2026

## Camera không cắt bàn

Thay công thức khoảng cách theo max(rows, cols) bằng fit phép chiếu lens thật.
Bounds lấy các ô initial khác VOID và mọi ô cầu (kể cả đang đóng), thêm biên
ô và chiều cao đứng 2,1. Căn giữa phần có nội dung rồi lùi camera tới khi cả
8 góc bounding box nằm trong vùng có lề cho HUD. Tính lại khi aspect ratio đổi.

Smoke dùng Panda/Ursina thật kiểm tra cả 10 màn ở 16:9, 4:3, 9:16, 21:9
(40 trường hợp), cùng trường hợp thay aspect rồi tự refit ở lượt update.
Đã xem ảnh màn rộng sau fit. Đây là kiểm tra lens/offscreen, chưa nghiệm thu
thao tác resize cửa sổ desktop bằng người.

## Split bẫy cũng đếm 5 giây rồi reset

Ba split bẫy có sẵn ở màn 8/9/10 được khai báo `fatal_split: true` trong splits.
Khi đứng kích hoạt, vẫn teleport và hiện hai cube tại targets; sau đó chốt
terminal loss. GUI hiện `Split trap!`, khóa input, đếm 5 giây, hiện YOU LOSE
1 giây rồi reset. Restart/đổi màn vẫn hủy callback cũ như bẫy CLOSE.

Chỉ các split được khai báo là bẫy mới áp dụng; không chạy tìm kiếm vô nghiệm
sau mọi bước chơi. Split thường, các target khác và điều kiện khối đứng không đổi.
Loader yêu cầu boolean, mặc định false. State equality/hash thêm metadata
fatalSplitSwitches, dùng lại marker động fatalSwitch; reset xóa marker.
Solver không cần sửa: result trả None cho bước gây thua.

Manifest có 37 witness: **9 loss** (6 CLOSE + 3 split), **28 effect**.
Audit chỉ cho phép successor terminal làm mục tiêu chứng minh bẫy tương ứng,
không nhầm nó là lời giải thắng. Cả 10 màn vẫn có lời giải tránh bẫy.

## Tăng tốc biến mất

Làn sóng giảm delay tối đa từ 0,65 xuống 0,32 giây. Mỗi ô rơi trong 0,28 giây,
co trong 0,16 giây và bắt đầu co muộn 0,1 giây để tránh cảm giác đứng chờ.
Resolution y=10, scale=6 thay vì mặc định 27 mỗi kênh: giảm từ 56 xuống 18
lượt setter/ô. Pha bàn rơi/co khoảng 0,6–0,7 giây thay vì khoảng 1,1 giây.
Không khẳng định FPS trên mọi máy; vẫn giữ barrier chờ mọi setter thật.
Goal fall 0,6 giây và blackout 1 giây không đổi. Di chuyển thường vẫn tức thời.

## Kiểm chứng

3 test mới kiểm tra terminal split/controller parity/reset, metadata hash,
schema boolean/backward compatibility và GUI countdown với hai cube hiện rõ.
Đã chạy lại toàn suite: **88 test pass, 254 subtest, 0 lỗi/skip**.
Audit 10 lời giải, 37 witness và 27 truy vấn hạn chế đã cập nhật.
Smoke kiểm tra camera, chơi đủ 10 màn, wave nhanh, blackout, restart giữa wave,
fatal CLOSE và split trap qua input/frame clock thật. Các ảnh ở temp.

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_split_trap.py -v
.venv\Scripts\python.exe -B -m examples.audit_levels --write
.venv\Scripts\python.exe -B tests/audit_advanced_portfolio.py
.venv\Scripts\python.exe -B -m unittest discover -s tests -q
.venv\Scripts\python.exe -B -m examples.gui_smoke
git diff --check
```

Không sửa solver/heuristic/registry hay chi phí; không commit/push/đổi nhánh.
