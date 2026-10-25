# Bộ kiểm thử cơ chế nâng cao — 25/10/2026

## 1. Đánh giá bộ test cũ

Kiểm kê thực thi toàn bộ 14 màn tại [ADVANCED_LEVEL_INVENTORY.md](ADVANCED_LEVEL_INVENTORY.md),
tọa độ từng ô đặc biệt, start/goal, đường đi và số node tại
[ADVANCED_LEVEL_EVIDENCE.json](ADVANCED_LEVEL_EVIDENCE.json).
Mọi màn đều load được và A* h=0 giải được. Với mọi màn cũ có effects công tắc,
bỏ effects vẫn có lời giải: activation witness của `test_level_links.py` chứng minh
kích hoạt có tác dụng, không chứng minh cần tác dụng đó để thắng. Màn 12 cần
split/merge, nhưng không cần SWITCH. Đây là kết quả chạy, không suy đoán từ grid.

Không có cơ sở xóa test ordinary: `test_foundation.py` bảo vệ đủ tư thế lăn,
ngoài biên, goal, snapshot, equality/hash, reset, cost và contract runner.
`test_rules.py` kiểm tra điều kiện kích hoạt/thứ tự tác động, không đơn thuần
đi tới ô. `test_level_links.py` phát lại witness thay vì tìm kiếm lặp lại trong
suite. GUI/input/visual có trách nhiệm khác. Tám test A* của thành viên khác giữ nguyên.
Hai demo 13/14 trùng đường thắng cơ bản nhưng kiểm tra OPEN/CLOSE và nhiều nhóm
cầu khác nhau; chưa chứng minh coverage tương đương để xóa.

## 2. Các luật nâng cao thực sự được hỗ trợ

Đã đọc `gameModel/rules.py`, `block.py`, `board.py`, `problem.py` và loader:

- Soft nhận cả tư thế nằm/đứng/cube; heavy chỉ nhận khối đầy đủ đứng.
- Bridge theo ID, cấu hình mở ban đầu, OPEN/CLOSE/TOGGLE; xử lý entry mới,
  effects có thứ tự, kiểm tra lại hỗ trợ, reset về đúng cấu hình màn.
- Đứng trên T tách và teleport hai cube tới targets cố định trong cùng một bước.
  Không có teleport độc lập hoặc dây chuyền; không tạo hạng mục giả cho chúng.
- SWITCH đổi active cube, không di chuyển/kích hoạt lại ô; hai cube kề cạnh
  tự merge. Cube đơn không thắng hoặc kích hoạt heavy/T.
- Fragile đỡ cube/nằm, vỡ khi khối đầy đủ đứng. VOID/ngoài biên gây rơi.

Các test cũ tiếp tục bảo vệ CLOSE, tái nhập switch, đóng cầu dưới cube bất động,
target teleport không hợp lệ và merge hai trục. Portfolio mới bổ sung sự cần thiết,
không thay các kiểm tra chi tiết này.

## 3. Bộ test mới được đề xuất và triển khai

Sáu JSON riêng tại `tests/fixtures/advanced/`, năm test method có subtest trong
`tests/test_advanced_portfolio.py`. Không đưa fixture vào chuỗi màn GUI.

| Test/Level | Mechanics tested | Mandatory or optional | Validation method | Result |
| --- | --- | --- | --- | --- |
| foundation/rules cũ | Lăn, rơi, goal, cost, copy/hash | Contract regression | Unit/subtest hiện có | Pass |
| soft_gate, 3×12 | Soft OPEN → qua cầu ban đầu đóng | Bắt buộc | A* đầy đủ + bỏ effects + replay cờ/ô cầu | solved / unsolvable |
| heavy_gate, 3×12 | Đứng heavy TOGGLE → qua cầu đóng | Bắt buộc | Như trên, không có switch khác | solved / unsolvable |
| split_control, 5×10 | Split/teleport, SWITCH, merge; fragile trên đảo đích | Ba cơ chế đầu bắt buộc | Cấm từng sự kiện riêng, replay lời giải | solved / 3 unsolvable |
| split_gate, 5×10 | Split → SWITCH → soft OPEN → merge → goal | Bốn cơ chế bắt buộc | Cấm từng cơ chế + kiểm tra thứ tự thực tế | solved / 4 unsolvable |
| optional_gate, 3×12 | Switch thực sự mở cầu ngoài đường đi | Tùy chọn | Đầy đủ và bỏ effects đều solved | Pass |
| dead_gate, 3×12 | Switch tới được, cầu mở nhưng vẫn thiếu sàn tới goal | Không có lời giải | Kiểm tra OPEN thực tế, cạn frontier từ đầu và sau OPEN | unsolvable |
| illegal_special_action | SWITCH khi chưa split, đi ra VOID | Âm | result=None, trạng thái/hash nguồn giữ nguyên | Pass |

## 4. Bằng chứng các luật nâng cao là bắt buộc

Mỗi fixture dương có lời giải được `validate_solution` phát lại kiểm tra cost và
goal. Test quan sát thay đổi bridgeState, tư thế split/merge, hành động SWITCH,
và việc khối thực sự đứng trên ô cầu. Không hardcode đường đi mong đợi.

`RestrictedProblem` chỉ nằm trong test. Với bridge, helper copy initial rồi bỏ
switchEffects, giữ nguyên ô switch và trạng thái cầu ban đầu: vẫn cho phép đi qua
công tắc. Chặn mọi bước chạm switch sẽ tạo bằng chứng bắt buộc giả; optional_gate
bảo vệ chính lỗi phương pháp đó. Với split/control/merge, helper gọi result thật
rồi bỏ cạnh chứa sự kiện mục tiêu, không sửa engine. Split/teleport được kiểm tra
như một chuyển tiếp nguyên tử. Đây là counterfactual tắt cơ chế, không tuyên bố
mọi mô hình hạn chế đều có cùng toàn bộ đồ thị với game gốc.

Chín truy vấn hạn chế cho bốn fixture bắt buộc đều cạn frontier:
soft_gate/heavy_gate: 3/3 node; split_control khi cấm split/control/merge:
2/7/22 node; split_gate khi cấm split/control/bridge/merge: 2/4/10/26 node.
Không kết luận unsolvable từ timeout hoặc node_limit: helper báo lỗi nếu gặp chúng.

## 5. Các test đã giữ, thêm, gộp hoặc loại bỏ

Giữ toàn bộ test và 14 màn hiện có. Thêm sáu fixture, năm method, một script audit
và ba tài liệu/bằng chứng. Gộp bốn fixture dương vào một test tham số hóa với
subtest từng màn/cơ chế để tránh lặp mã kiểm tra ordinary. Không xóa test/màn,
không giảm số method cũ vì chưa chứng minh trường hợp nào hoàn toàn dư thừa.
Mục tiêu nhỏ gọn áp dụng cho portfolio nâng cao mới; suite tổng vẫn tăng năm method.

## 6. Kết quả chạy test

Môi trường làm việc sau khi đối chiếu stash có 63 method cũ; thêm năm method mới:
**68 test, 186 lượt subtest, 0 failure, 0 error, 0 skip**. Số subtest bao gồm
subtest lồng, không phải 186 tình huống độc lập.

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_advanced_portfolio.py -v
.venv\Scripts\python.exe -B tests/audit_advanced_portfolio.py
.venv\Scripts\python.exe -B -m unittest discover -s tests -q
git diff --check
```

Đã chạy discovery toàn suite qua TextTestRunner tùy biến đếm addSubTest để lấy
186 lượt subtest; tất cả pass. Audit load và tìm kiếm lại 14 màn cũ, 6 fixture;
19 màn solved, dead_gate unsolvable. Các lời giải đều được phát lại. `git diff --check` pass.
Thông báo `Solver error: Illegal solution move at step 0` là nhánh âm có chủ đích
của test GUI kiểm tra từ chối lời giải lỗi, không phải failure của test runner.

## 7. Các giới hạn còn lại

Chỉ A* đăng ký hiện thực chạy được; BFS/DFS/UCS là stub NotImplementedError.
Không dùng solver tham khảo cũ để thay thế, không sửa solver/heuristic/registry.
Tất cả truy vấn dùng h=0; đây là audit đúng/sai, không phải benchmark.
Không có ảnh gameplay đính kèm có thể đọc trong lượt này, nên chỉ dựa yêu cầu
đảo/cầu và luật đã xác minh, không khẳng định sao chép bố cục ảnh.
Không nghiệm thu desktop thủ công hoặc sửa GUI/animation; working tree hiện khác
stash ở phần hoạt ảnh và được giữ nguyên theo phạm vi nhiệm vụ.

Stash mới nhất khi tiếp tục: `d198b60` (nhãn feature/classic-graphics), base `c237d10`.
Nó chứa bảy tệp portfolio bị thiếu; chỉ bảy tệp đó được lấy lại sau kiểm tra đường
dẫn chưa tồn tại. Không lấy `test_blender_model.py`/`view.py.visual-backup` không liên
quan, không ghi đè tệp hiện có. Stash cũ `Fix GUI` và stash luật trước đó vẫn giữ.
Nhánh làm việc vẫn feature/new-game-rules; không commit/push/stash apply/pop/drop.
