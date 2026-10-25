# Chuỗi 10 màn: nhiều công tắc và bẫy — 25/10/2026

Khi thắng: khối rơi vào goal, cả bàn rơi/co dần theo làn sóng, rồi đen 1 giây và tải màn
mới. Áp dụng cả chơi tay/replay, hủy được khi reset/đổi màn. Kết quả mới nhất:
85 test pass, 251 lượt subtest, 0 skip. Xem [WIN_TRANSITION.md](WIN_TRANSITION.md).

## Cập nhật: CLOSE gây thua, đếm ngược 5 giây

Sáu nút có `!` ở màn 5–10 được khai báo `fatal_close`: đóng cầu, khóa lượt,
đếm 5 giây, hiện YOU LOSE trong 1 giây rồi reset. Tám CLOSE thường vẫn có thể
khắc phục; ba split bẫy vẫn như cũ. Solver tự loại bước terminal qua result=None,
không sửa thuật toán/heuristic. Engine, metadata State và GUI được mở rộng theo
yêu cầu mới này. Chi tiết vị trí/schema/kiểm tra tại [FATAL_CLOSE.md](FATAL_CLOSE.md).
Các số liệu và mô tả bên dưới cần đọc cùng cập nhật này; witness fatal là loss,
không là lời giải thắng. Audit đúng/sai nay dùng solver trực tiếp không profiling.

Hiển thị mới: goal là **hốc tối viền xanh lá**, phân biệt VOID/khoảng khuyết
không có viền. Đề cho phép khoảng trống ngoài goal; dẫn chiếu chính xác trang 3,
§§2.4–2.5 và kiểm tra hiển thị tại [GOAL_PRESENTATION.md](GOAL_PRESENTATION.md).

Giữ 2 màn cơ bản, 2 fragile, 3 cầu và 3 split; chỉ tăng mật độ điều khiển ở
màn nâng cao để phần học cơ bản vẫn rõ. Xem [bản đồ 10 màn](CAMPAIGN_MAPS.svg).
Bố cục 1/2 khác nhau (sân lệch và bốn cánh quanh giếng); bố cục 8/9 khác nhau
(kênh ngang và chuỗi đảo dọc), có test loại trừ cả quay/lật/dịch chuyển.

## Vì sao có hai ô rời ngoài bàn chính?

Ở màn 8–10, hai ô [1,1] và [1,4] là đích của **điểm split bẫy**.
Khối đứng trên T đó sẽ tách thành hai cube ở hai ô không nối nhau. Trạng thái
vẫn hợp lệ nhưng không thể ghép hoặc tới goal; R để restart. Đây không phải
ô sót của loader. Các ô và bẫy được giữ có chủ đích, không thêm ô rời mới.

## Điều khiển hiện tại

Có **31 công tắc cầu + 6 điểm T = 37 witness kích hoạt thật**, tăng từ 19+6.
Màn 5–10 có lần lượt **5, 5, 7, 2, 5, 7 công tắc**. Mỗi màn 8–10 vẫn có
hai T: một điểm tới vùng giải đố và một điểm bẫy. OPEN là điều khiển mở,
CLOSE đóng lại cầu đã mở, TOGGLE có thể lợi hoặc hại tùy trạng thái.
Không bắt buộc kích hoạt mọi nút, nhưng mọi nút đều có tác dụng được kiểm chứng.

Màn 8 có thêm cầu landing đỡ một hàng của đảo đích. Phải mở từ đảo xuất phát
trước khi split; nếu chưa mở thì cube đáp mất hỗ trợ và thua. Nút CLOSE trên
đảo xuất phát có thể phá sự chuẩn bị đó. Đây là kết hợp mới của luật cầu và
split đã có, không đổi engine.

| Màn | Kích thước | Ô đỡ ban đầu | Công tắc / T | Bước / cost A* h=0 | Node mở rộng |
| --- | --- | --- | --- | --- | --- |
| 1 | 9×11 | 57 | 0 / 0 | 10 / 10 | 99 |
| 2 | 15×17 | 115 | 0 / 0 | 13 / 13 | 284 |
| 3 | 10×15 | 65 | 0 / 0 | 13 / 17 | 111 |
| 4 | 14×14 | 75 | 0 / 0 | 26 / 34 | 168 |
| 5 | 10×16 | 59 | 5 / 0 | 16 / 15,5 | 201 |
| 6 | 11×17 | 81 | 5 / 0 | 20 / 19,5 | 279 |
| 7 | 11×23 | 77 | 7 / 0 | 25 / 24,5 | 364 |
| 8 | 10×24 | 55 | 2 / 2 | 20 / 40 | 1188 |
| 9 | 17×17 | 58 | 5 / 2 | 19 / 18,5 | 1783 |
| 10 | 13×26 | 70 | 7 / 2 | 26 / 29 | 2467 |

Ô đỡ ban đầu không tính VOID/cầu đóng. Đường đi tối ưu chi phí TILE_COST của
A* h=0, không khẳng định tối ưu số bước. Điều khiển thay thế có thể làm đường
thắng tốt ngắn hơn dù có nhiều lựa chọn sai hơn; không dùng riêng số bước để
khẳng định độ khó. BFS/DFS/UCS chưa có triển khai nên chưa so sánh benchmark.

## Bẫy có bằng chứng

Có **14 công tắc CLOSE + 3 điểm split bẫy = 17 bẫy gắn nhãn**.
CLOSE thường có thể khắc phục bằng nút khác, không mặc định là thua ngay.
Split cô lập là vô nghiệm, đã được solver duyệt hết xác nhận.

| Màn | Công tắc CLOSE (tọa độ từ 0) | Split bẫy |
| --- | --- | --- |
| 5 | W[2,5], w[4,4] | Không |
| 6 | w[7,3], W[4,5], w[6,4] | Không |
| 7 | W[1,4], w[6,10], W[7,13] | Không |
| 8 | w[3,20] | T[1,22] |
| 9 | w[8,9], w[11,12] | T[15,5] |
| 10 | w[8,16], w[6,10], w[9,18] | T[1,24] |

Test phát witness qua controller, kiểm tra đóng cầu thật/tách thật rồi reset.
ActivationProblem không chấp nhận chạm nút mà không đổi cờ: CLOSE phải được
tìm sau lúc cầu mở, không phải chỉ đi đến nút khi cầu đã đóng sẵn.

## Bằng chứng cơ chế bắt buộc

Cả 10 màn solved; **27 truy vấn hạn chế** ở các màn nâng cao cạn frontier và
trả unsolvable. Tám nhóm cầu ban đầu đóng, từng bridge ID kiểm tra cần thiết riêng.
Bỏ effects trên bản sao initial để tắt cầu; chặn sự kiện split/SWITCH/merge
hoặc chuyển tiếp chiếm F để kiểm chứng cơ chế tương ứng. Không đổi production.
Split/teleport là một chuyển tiếp nguyên tử; không chứng minh độc lập hai luật.
Fragile bắt buộc đi qua an toàn, không bắt buộc làm vỡ vì đứng trên F là thua.

Replay kiểm tra cost, goal, sự kiện, controller parity và reset.
Chi tiết tại [ADVANCED_LEVEL_EVIDENCE.json](ADVANCED_LEVEL_EVIDENCE.json);
hash và 37 witness tại levels/validation.json. Fixture legacy giữ kiểm tra
phụ thuộc tọa độ cũ; fixture advanced nhỏ giữ trường hợp âm/tùy chọn.
Không sửa solver, heuristic, registry, engine, runner hoặc GUI/animation.
Di chuyển vẫn tức thời, replay nghỉ 0,5 giây.

## Kiểm thử và tái tạo

```powershell
.venv\Scripts\python.exe main.py
.venv\Scripts\python.exe -B tests/build_campaign.py --preview
.venv\Scripts\python.exe -B -m examples.audit_levels --write
.venv\Scripts\python.exe -B tests/audit_advanced_portfolio.py
.venv\Scripts\python.exe -B -m unittest discover -s tests -q
.venv\Scripts\python.exe -B -m examples.gui_smoke
git diff --check
```

Giới hạn mỗi query 60 giây/100000 node. Stage được đo qua runner, witness và
query đúng/sai dùng cùng solver từ registry/h=0 không tracemalloc. Không kết
luận unsolvable từ timeout. Generator --write tái tạo JSON, sau đó phải chạy
hai audit xong rồi mới chạy suite: một lượt test đọc manifest cũ khi audit còn
chạy đã báo thiếu witness; test bẫy chạy lại sau đồng bộ đã pass.
GUI offscreen phát đủ 10 màn, chưa nghiệm thu desktop thủ công.
Không commit/push trong lượt thêm công tắc này.

Lượt kiểm tra cuối sau khi đồng bộ manifest: **73 test pass, 236 lượt subtest,
0 failure, 0 error, 0 skip**. Smoke GUI đủ 10 màn và `git diff --check` pass.

## Bổ sung ở các màn đầu, giữ nguyên màn 1

Màn 2 thêm 2 ô F và 3 khoảng khuyết; F là chướng ngại làm quen, có thể tránh.
Màn 3 thêm 2 F và 2 khoảng khuyết (tổng 4 F); màn 4 thêm 2 F và 2 khoảng
khuyết (tổng 6 F). Màn 3/4 vẫn bắt buộc đi qua fragile ở tư thế an toàn.
Một vị trí khoét thử ở màn 4 làm vô nghiệm đã được đổi sang mép phòng.
Màn 1 và màn 5–10 giữ nguyên từng byte so với trước lượt sửa này.

Đã giải lại màn 2/3/4, verify cost/goal, phát qua controller và reset; kiểm tra
hạn chế fragile của màn 3/4 đều unsolvable. Cập nhật hash/witness/evidence và
bản đồ. Lượt kiểm tra dữ liệu mới: 41 test liên quan pass và smoke GUI đủ 10
màn pass. Không chạy lại toàn bộ 73 test trong lượt sửa dữ liệu nhỏ này;
số 73 phía trên là kết quả lượt trước. Không commit/push.
