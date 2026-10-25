# Permanent CLOSE gây thua — 25/10/2026

Theo yêu cầu mới, một số công tắc CLOSE được đánh dấu `fatal_close: true`.
Đây là luật bẫy bổ sung của nhóm: đề §2.5 có toggle/permanent, nhưng không
quy định tự động thua hoặc đếm ngược 5 giây. CLOSE không có cờ vẫn giữ hành
vi cũ, có thể mở lại bằng công tắc khác.

## Hành vi

1. Khi mới đè đủ điều kiện lên nút có `!`, cầu liên kết đóng và lượt chơi
   chốt thua ngay. Khối được đặt vào vị trí mới, không có nội suy di chuyển.
2. GUI khóa di chuyển, dừng replay, hiện `Permanent CLOSE! Loss in 5 s`;
   đếm 5 → 4 → 3 → 2 → 1 theo thời gian frame.
3. Sau đủ 5 giây, hiện `YOU LOSE / Restarting...` trong 1 giây cho dễ đọc,
   rồi reset màn về cấu hình ban đầu, xóa thông báo và mở input.
4. R/Restart, New Game hoặc đổi màn hủy bộ đếm/thông báo và callback cũ.

Heavy có `!` vẫn chỉ kích hoạt khi khối đầy đủ đứng; nằm/cube không kích hoạt.
Soft có `!` nhận mọi tư thế. Đích teleport là soft có cờ cũng gây thua.
Bẫy vẫn gây thua nếu cầu đã đóng từ trước. Nó là hậu quả của việc kích hoạt
nút này, không phải phép tìm kiếm tổng quát để đoán mọi trạng thái vô nghiệm.

| Màn | Nút gây thua (tọa độ từ 0) | Cầu đóng |
| --- | --- | --- |
| 5 | W[2,5] | crossing |
| 6 | W[4,5] | crossing |
| 7 | W[7,13] | second |
| 8 | w[3,20] | landing |
| 9 | w[11,12] | gate |
| 10 | w[9,18] | near |

Có 6 nút gây thua, 8 CLOSE thường và 3 split bẫy cô lập trong bộ 10 màn.
Dấu `!` xuất hiện trên marker GUI và bản đồ SVG. Mỗi màn vẫn có đường thắng
né nút này; các cơ chế khác vẫn bắt buộc theo audit.

## Engine, solver và schema

Ví dụ schema 2:

```json
{"position": [3,20], "fatal_close": true,
 "effects": [{"bridge": "landing", "mode": "CLOSE"}]}
```

Cờ tùy chọn mặc định false, bắt buộc boolean, chỉ được đi với toàn bộ effects
là CLOSE. Loader từ chối cờ sai kiểu hoặc ghép OPEN/TOGGLE.

Board giữ `fatalCloseSwitches` cố định và `fatalSwitch` động; State so sánh/hash
bao gồm cả hai. Transition fatal trả successor đã đóng cầu, valid=false,
loss=true. Problem.result trả None, nên A* và các solver tuân thủ interface
hiện tại loại bước thua trước khi tính cost. Không thêm time vào search state,
không sửa solver, heuristic, registry, SearchResult hoặc runner.

Controller giữ successor để trình bày, isGameOver=true, hasWon=false.
Sau thua, transition/executeMove không cho đi tiếp; applySwitch/toggleBridge
không mở lại cầu. Reset xóa marker động và khôi phục bridge/tiles ban đầu.
Fatal được xử lý trước các switch sau đó trong cùng bước, nên OPEN đồng thời
không cứu được lượt đã thua.

ActivationProblem chỉ là mục tiêu audit: có thể chấp nhận successor fatal để
chứng minh bẫy tới được. Manifest ghi `outcome: loss` cho 6 witness đó; không
nhầm với lời giải thắng màn. 31 witness còn lại là `effect`.

## Kiểm tra

8 test mới kiểm tra soft/heavy, teleport, no-op CLOSE vẫn terminal, không thể
mở lại, simultaneous OPEN, copy/hash/reset, schema và GUI timing/cancellation.
Smoke Ursina dùng frame clock thật xác nhận 5 giây, notice 1 giây, reset và
manual cancellation; đã xem ảnh có chữ đếm ngược/thua rõ trên HUD.
Offscreen helper thiết lập UI lens giống resize của cửa sổ thật để ảnh không
bỏ mất HUD. Chưa nghiệm thu desktop thủ công.

Test nền headless được sửa dùng tiến trình Python sạch: test cũ chỉ nhìn
sys.modules chung nên thất bại khi GUI test mới import Ursina trước nó.
Mục tiêu bảo vệ không đổi: chạy headless không import GUI, bất kể thứ tự test.

Audit đã tìm 10 lời giải né fatal và 37 witness (6 loss); bộ đối chứng giữ
27 truy vấn hạn chế. Đo riêng A* h=0 màn 10 qua runner có tracemalloc: solved
trong khoảng 47 giây trên máy này, trong giới hạn 60 giây. Lượt chạy song song
trước đó timeout không được coi là unsolvable. Audit đúng/sai hiện gọi solver
đăng ký trực tiếp, không đo tracemalloc lặp lại; benchmark vẫn dùng runner.

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_fatal_close.py -v
.venv\Scripts\python.exe -B -m examples.audit_levels --write
.venv\Scripts\python.exe -B tests/audit_advanced_portfolio.py
.venv\Scripts\python.exe -B -m unittest discover -s tests -q
.venv\Scripts\python.exe -B -m examples.gui_smoke
git diff --check
```

Giữ nhánh feature/new-game-rules, không commit/push hoặc đụng stash.

Kết quả cuối: **82 test pass, 243 lượt subtest, 0 failure/error/skip**.
27 truy vấn hạn chế cạn frontier; 10 lời giải và 37 witness đã tái tạo.
Smoke GUI với HUD nhìn thấy xác nhận countdown/notice/reset; đã xem cả hai ảnh.
