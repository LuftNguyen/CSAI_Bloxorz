# Trình bày bước đi — 25/10/2026

## Hiện tại: di chuyển tức thời, giữ nguyên luật mới

Cập nhật nhịp phát lại theo phản hồi tiếp theo: `view.replayInterval = 0.5`
giây giữa hai action. Khoảng nghỉ chỉ thuộc trình bày replay, không làm chậm
solve hoặc chơi tay; bước đi vẫn snap ngay, không tạo animator position/scale.
Cooldown được tính theo frame delta, reset/đổi màn xóa cooldown và replay cũ.
Test kiểm tra 0.49 giây chưa đi bước kế, đủ 0.5 giây mới đi; 64 test và smoke
Ursina đều pass. Có thể tăng replayInterval lên 0.8 hoặc 1.0 nếu muốn chậm hơn.

Theo yêu cầu tiếp theo, bỏ nội suy position/scale và khoảng chờ 0.4 giây cho
bước đi thường. Phần ghi chép bản nội suy ở bên dưới chỉ là **lịch sử đã được
thay thế**, không mô tả hành vi hiện tại.

Lúc bắt đầu lượt này, đang đúng feature/new-game-rules nhưng mã mới lại nằm
trong stash `d72e0ef` (Fix GUI), không có trên đĩa. Sau khi xác minh HEAD trùng
base, tracked/index sạch và các đường dẫn untracked không tồn tại, đã khôi
phục có kiểm tra 21 tệp tracked + 21 tệp untracked từ snapshot này. Không trộn
với stash cũ, không pop/drop/clear stash. Cả d72e0ef và 72d7016 được giữ nguyên.
Baseline sau khôi phục: **63 test pass**; nhánh không đổi, HEAD vẫn c237d10.

Luồng hiện tại:

1. `beginMove` gọi `GameController.executeMove` đúng một lần; không tính thêm
   landing hoặc gọi lại transition chỉ để hiển thị.
2. `finishStep` đặt mesh trực tiếp theo block kết quả rồi render board mới ngay
   trong cùng lượt xử lý. Soft/heavy, cầu, fragile, teleport, split/SWITCH/merge
   giữ nguyên logic; hiển thị ngay hình dạng và tọa độ cuối, không qua pose giữa.
3. Bước thường không tạo animator, barrier rỗng hoặc timer di chuyển; input mở
   lại ngay. `_presentingMove` chỉ chống xử lý outcome hai lần trong hàm đồng bộ.
4. Replay được đánh dấu sẵn sàng và xử lý tối đa một action mỗi lượt
   `updateAnimations`, sau khoảng nghỉ replayInterval=0.5 giây. Không đệ quy
   toàn bộ lời giải, không có barrier di chuyển. Giữ startup delay 0.5 giây;
   khoảng nghỉ replay không thuộc thời gian solve hoặc đổi thứ tự hành động.
5. Win thủ công giữ chờ 2 giây. Replay thắng hoàn tất/sang màn ở lượt update
   tiếp. Fall bắt đầu ngay từ pose đích, vẫn chờ toàn bộ animator rơi/xoay rồi
   nghỉ 0.1 giây và restart. Trong fall/win hold, input vẫn bị khóa.

`animation_sync.py` **không bị xóa hoặc sửa**: barrier và test Sequence thật
vẫn cần cho fall. `watchAnimations`, generation guard và cancelReplay giữ
việc hủy fall/timer cũ và xóa replay đã xếp khi restart/đổi màn.

### Kiểm chứng lượt di chuyển tức thời

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p test_visual_sync.py -v
.venv\Scripts\python.exe -m unittest discover -s tests -p test_gui_rules.py -v
.venv\Scripts\python.exe -m unittest discover -s tests -q
.venv\Scripts\python.exe -m examples.gui_smoke --capture-dir (Join-Path $env:TEMP 'BloxorzInstantMoveReview')
.venv\Scripts\python.exe -m py_compile view.py animation_sync.py examples/gui_smoke.py tests/test_gui_rules.py tests/test_visual_sync.py
git diff --check
```

- Test tập trung: **11 visual sync + 6 GUI rules pass**. Toàn bộ: **64 pass,
  0 skip**. Kỳ vọng nội suy cũ được đổi sang assert pose cuối ngay, không gọi
  animate_position/animate_scale, logic một lần; không mock cả pipeline để né test.
- Smoke offscreen pass: pose tức thời, zero position/scale animators, OPEN/CLOSE,
  fragile/fall/reset, split/SWITCH/merge, A* replay và hủy fall/replay cũ.
- Đã xem hai ảnh render trước/sau bước mở cầu trong thư mục tạm; không phải
  nghiệm thu điều khiển desktop bằng người. Không thêm screenshot vào repo.
- Engine/gameModel, levels, runner, inputHandler, search và test A* trùng bản
  đã khôi phục; không sửa chi phí/heuristic/contract. Không stage/commit/push.
- Diff mới chỉ gồm view.py, hai test GUI, smoke script và cập nhật tài liệu.

Giới hạn: không có hoạt ảnh quay lăn; nhịp replay được cấu hình riêng, không
phụ thuộc việc nội suy mesh. Tìm kiếm vẫn đồng bộ; bàn phím/focus trên desktop
cần người dùng thử trực tiếp. Đây đều không phải lý do đổi luật hoặc solver.

---

## Lịch sử bản đồng bộ nội suy (đã thay thế)

## Git và baseline

Bắt đầu tại feature/astar, HEAD c237d10. Cả hai nhánh local feature/astar và
feature/new-game-rules cùng trỏ c237d10; phần luật mới nằm trong stash
72d7016 (WIP: new game rules before Astar GUI comparison).

Đã xác minh working tree/index không có thay đổi tracked, cache Panda3D là
untracked; base của stash trùng HEAD/nhánh đích. Sau khi chuyển đúng nhánh,
khôi phục có kiểm tra từng đường dẫn: 21 snapshot tracked và 18 tệp untracked
chưa tồn tại (từ parent thứ ba của stash). Không ghi đè thay đổi khác, không
pop/drop/clear stash, không stage/commit/push. Baseline khôi phục: **53 test pass**.
Diff với HEAD vì vậy bao gồm cả WIP đã có; diff của lần sửa này phải so với
snapshot stash, không nhầm các luật/màn khôi phục thành thay đổi hoạt ảnh mới.

## Nguyên nhân

- view.stepDuration=0.25, replay gọi bước kế khi timer 0.25 hết.
- Trong Ursina 8.3.0 cài tại venv, Entity.animate dùng resolution+1 lần Wait;
  duration=0.25 cho sequence dài khoảng 0.2667. Timer không phải hoàn tất.
- animate_position trả tuple ba Sequence, animate_scale trả một Sequence.
  finished chỉ dựa t>=duration; phải chờ cả setter cuối được chạy.
- GUI render board mới ngay sau executeMove rồi mới kéo mesh từ vị trí cũ;
  cầu xuất hiện/biến mất trong lúc khối chưa tới ô kích hoạt.
- Bật/tắt mesh split/merge trước di chuyển khiến mesh cũ bị bỏ qua; nhánh
  thắng/thua thủ công cũng bỏ qua bước di chuyển tới đích.

Không sửa cách engine tính switch hoặc solver; vấn đề nằm ở trình bày.

## Cơ chế mới

`animation_sync.AnimationCompletion` nhận toàn bộ handle, được poll sau vòng
cập nhật Sequence của Ursina. Chỉ gọi callback đúng một lần khi mọi handle có
finished=True **và** tất cả func_finished_statuses=True. Không gọi finish()
để ép animator tới đích, không dùng invoke(duration) làm tín hiệu hoàn tất.
Không có Parallel trong bản Ursina đang cài; helper nhỏ thay cho việc giả định
một timer có thể chờ nhiều animation song song.

- Ordinary move dùng một cấu hình `stepDuration=0.4`, curve.linear. Ursina có
  thể hoàn tất muộn hơn danh nghĩa khoảng một mẫu; barrier chờ đúng hoàn tất.
- `beginMove` tính hình học landing bằng Block.resultingState (không áp dụng
  tương tác ô) và gọi GameController.executeMove **một lần**. Snapshot kết quả
  được giữ riêng, board Entity cũ vẫn hiển thị trong lúc đi.
- `finishStep` chỉ nhận completion hợp lệ, vẽ board từ snapshot đã tính và
  chốt mesh về pose chính xác, rồi mới thả input/replay hoặc xử lý win/fall.
- Replay tiếp bước sau arrival; input bị khóa trong cả movement/effect/fall.
  SWITCH không tạo animator nếu pose không đổi; đổi highlight ở lượt update
  kế, không gán một delay chuyển động giả và không tái kích hoạt switch.
- Split/teleport: khối đầy đủ đi tới ô split trước, sau đó hiện hai cube tại
  đích đã tính. Merge: cube di chuyển tới cạnh cube kia rồi mới đổi mesh đầy đủ.
  Đây là phân pha hình ảnh, không thêm luật hoặc teleport dây chuyền.
- Fragile/cầu mất hỗ trợ: tới đích, cập nhật board rồi rơi. Fall chờ cả y và
  rotation animator thực hoàn tất, sau đó nghỉ 0.1 giây rồi restart. Win thủ
  công giữ khoảng chờ 2 giây; replay thắng sang màn sau arrival như luồng cũ.
- `cancelReplay` tăng generation, hủy barrier, timer và mesh animator; xóa kết
  quả pending. Mọi callback có generation guard, kể cả đã được giữ tham chiếu
  trước reset. Entity cũ được giữ enabled trong pha cần animate, không dựa vào
  việc disable/destroy sẽ tự hủy Sequence (Ursina không bảo đảm điều đó).

## Tệp sửa thêm so với WIP

- `view.py`: barrier, trình tự arrival/effect/outcome, shared manual/replay và
  generation guard. `run()` đăng ký Entity.update để poll sau Sequence update.
- `animation_sync.py`: helper hoàn tất/hủy hoạt ảnh, không phụ thuộc game model.
- `tests/test_gui_rules.py`: fake handle có trạng thái thật; không còn coi gọi
  finishStep thủ công là bằng chứng animator hoàn tất.
- `tests/test_visual_sync.py`: 10 test mới (3 completion, 7 presentation), có
  Entity/Sequence thật kiểm tra duration và final setter; các test khác kiểm
  tra ordering, consecutive replay, OPEN/CLOSE, fragile/fall/win, split/SWITCH/
  merge, input lock và callback cũ sau reset/đổi màn.
- `examples/gui_smoke.py`: bước qua frame thật, không gọi finishStep thủ công;
  đi qua StartMenu thật để ẩn overlay; kiểm tra actual A* replay/cancellation.
- Tài liệu này, cập nhật ngắn GAME_RULES.md/TESTING.md cho cơ chế mới.

Không sửa gameModel, levels, runner, inputHandler hay solver so với bản WIP
khôi phục. Search code và tests/test_astar.py vẫn trùng HEAD.

## Kiểm tra đã chạy

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p test_visual_sync.py -v
.venv\Scripts\python.exe -m unittest discover -s tests -q
.venv\Scripts\python.exe -m examples.gui_smoke --capture-dir (Join-Path $env:TEMP 'BloxorzAnimReview')
.venv\Scripts\python.exe -m py_compile view.py animation_sync.py examples/gui_smoke.py tests/test_gui_rules.py tests/test_visual_sync.py
git diff --check
```

- Baseline 53 pass; giai đoạn barrier 56 pass; cuối cùng **63 test pass, 0 skip**.
- Smoke offscreen chạy thật ở frame clock 1/60 và 0.1 giây: ordinary movement,
  cầu OPEN/CLOSE, rơi/reset, split/SWITCH/merge, A* hai bước tới goal và đổi màn,
  reset/đổi màn giữa Sequence chưa hoàn tất đều pass.
- Cũng chạy smoke với `--capture-dir` trỏ thư mục tạm và xem ảnh: lúc đang đi
  cầu vẫn tối/đóng; sau arrival khối nằm trên soft và cầu mở. Ảnh ở temp, không
  thêm ảnh sinh ra vào repository. Capture dùng PNMImage/StringStream và kiểm
  tra ghi thành công; không coi một đường dẫn ảnh rỗng là bằng chứng hiển thị.
- Test mock gọi một callback hoàn tất cũ sau reset chỉ kiểm tra generation,
  không được dùng để khẳng định animator thực đã chạy xong.

## Giới hạn và checklist thủ công

Chưa có phiên điều khiển desktop bằng người: ảnh offscreen và kiểm tra frame
clock không thay thế đánh giá cảm giác chuyển động, focus bàn phím hoặc FPS
trên máy khác. Cần thử trực tiếp main.py: manual/replay nhiều bước liên tiếp,
switch/cầu, fragile, split/merge và restart/Next Level giữa bước. Bước 0.4 giây
là giá trị khởi đầu, chưa phải kết luận đã đạt cảm giác người dùng mong muốn.

Hoạt ảnh vẫn là nội suy position/scale, chưa phải quay khối thật quanh cạnh.
Teleport/split/merge đổi hình dạng sau arrival, chưa thêm hiệu ứng riêng phức
tạp. Tìm kiếm vẫn đồng bộ với GUI; không đổi thuật toán, thứ tự tìm kiếm,
chi phí, lời giải, heuristic hoặc contract để sửa phần trình bày.
