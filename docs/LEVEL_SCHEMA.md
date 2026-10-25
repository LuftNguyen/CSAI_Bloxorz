# Schema màn và dữ liệu demo

`levels/levelLoader.py:loadLevelFromJson(path, isDebug=True)` giữ giao diện cũ,
trả Board/Block. Lỗi JSON/schema trả ValueError kèm tên tệp, không biến ký tự lạ
thành VOID. File thiếu vẫn báo OSError/FileNotFoundError từ hệ điều hành.

Các trường chung: rows/cols nguyên dương, grid đúng số hàng/cột, đúng một G,
start `{r,c}` trên sàn thường. S không bắt buộc, nhưng nếu có phải duy nhất và
khớp start (màn 3 cũ không có S). Tọa độ bắt đầu từ 0.

| Ký tự | Ô |
| --- | --- |
| X | Void |
| . hoặc S | Sàn thường / điểm xuất phát |
| G | Đích |
| F | Fragile |
| w | Soft switch |
| W | Heavy switch |
| B | Ô cầu (được thay bằng B/VOID theo trạng thái ban đầu) |
| T | Split switch, chỉ schema 2 |

## Legacy / schema_version=1

Giữ `bridges: [{switch: [r,c], tiles: [[r,c], ...]}]`. Cầu ban đầu mở và
switch TOGGLE. Các switch trang trí không có liên kết vẫn được giữ như nguồn.
Các nhóm có đúng cùng tập ô được gộp thành một ID nội bộ: switch đầu tiên làm
ID, switch còn lại trỏ cùng cờ. Nhóm chồng một phần bị từ chối vì mơ hồ.
Mọi tọa độ switch khai báo phải là w/W, tiles phải là B. Không dùng switches,
splits hoặc T mới mà không khai báo schema_version=2.

**Lỗi dữ liệu được xác minh và chấp nhận sửa:** `level5.json` khai báo switch
`[6,15]` nhưng `grid[6][15] == '.'`; `grid[6][14] == 'W'`. Chỉ đổi liên kết
thành `[6,14]`, giữ nguyên grid. Hai switch của màn này cùng điều khiển đúng
một nhóm cầu vật lý. Test `test_all_levels_and_legacy_shared_bridge_fix` kiểm
tra cả tọa độ và cờ cầu dùng chung. Lượt triển khai luật ban đầu giữ layout;
lượt hoàn thiện dữ liệu được cho phép ngày 24/10 sửa một số ô và liên kết,
liệt kê cụ thể trong [LEVEL_COMPLETION.md](LEVEL_COMPLETION.md).

## schema_version=2

Ví dụ cấu trúc (một phần; grid/start xem các tệp demo đầy đủ):

```json
{
  "schema_version": 2,
  "bridges": [
    {"id": "crossing", "initial_open": false, "tiles": [[2,4]]}
  ],
  "switches": [
    {"position": [1,2], "effects": [{"bridge": "crossing", "mode": "OPEN"}]},
    {"position": [2,2], "effects": [{"bridge": "crossing", "mode": "CLOSE"}]}
  ],
  "splits": [
    {"position": [1,4], "targets": [[1,1], [1,6]]}
  ]
}
```

Bridge ID là chuỗi không rỗng, duy nhất. initial_open bắt buộc là boolean.
Tiles không rỗng, duy nhất, không chồng nhóm khác; grid tại đó phải là B/X.
Mỗi B cần một bridge definition. Mọi w/W cần một khai báo effects không rỗng,
tham chiếu ID hợp lệ, mode đúng TOGGLE/OPEN/CLOSE. Một switch có thể có nhiều
effect tới các ID khác nhau; nhiều switch có thể trỏ cùng ID. Cấm lặp ID trong
cùng một switch; xung đột giữa switch xử lý theo GAME_RULES.md.

Mọi T cần đúng một split definition. Targets đúng hai tọa độ khác nhau, trong
biên và có sàn hoặc nằm trong nhóm cầu. Cho phép ô đặc biệt/ban đầu đóng;
engine kiểm tra hỗ trợ ở thời điểm thực sự teleport. Void vĩnh viễn bị từ chối.
Split definition có thể thêm `fatal_split: true` (boolean, mặc định false):
teleport rồi chốt thua, GUI đếm 5 giây/reset; solver loại bước thua.
Reset dùng tiles và trạng thái ban đầu đã lưu, không mặc định tất cả cầu mở.

## Phân loại màn hiện hành

Schema 2 có cờ tùy chọn `fatal_close: true` trên switch có toàn bộ effects
CLOSE. Cờ mặc định false, bắt buộc boolean. Đây là bẫy bổ sung theo yêu cầu
mới: gây thua ngay, GUI đếm 5 giây rồi thông báo/reset; không phải quy định
đếm ngược trong đề. Xem [FATAL_CLOSE.md](FATAL_CLOSE.md).

LevelManager tải đúng 10 màn: 1–2 cơ bản, 3–4 fragile, 5–7 cầu/công tắc,
8–10 split và kết hợp. Chi tiết tại [CAMPAIGN.md](CAMPAIGN.md).
`levels/validation.json` lưu 10 lời giải và 37 activation witness.
Các fixture cũ cần cho hồi quy nằm tại `tests/fixtures/legacy/`.

## Phân loại màn cũ — lịch sử, không còn là chuỗi GUI

- `level1.json`–`level11.json`: bộ nguồn đã được hoàn thiện liên kết (màn 1,8),
  sửa khoảng đỡ màn 6, reference màn 5 và metadata màn 2. Cả 11 màn đã giải
  được bằng A* h=0 và verify/controller replay; đây là phiên bản dữ liệu mới,
  chưa phải benchmark chính thức cho tất cả solver.
- `level12.json`: demo split, chọn cube, ghép; corridor nhỏ để kiểm tra dễ.
- `level13.json`: demo cầu ban đầu đóng, OPEN/CLOSE dùng chung một bridge ID.
- `level14.json`: demo TOGGLE, OPEN/CLOSE và một switch điều khiển nhiều cầu.
- Fixture biên/fragile/teleport nguy hiểm nằm trong `tests/test_rules.py`, không
  được dùng để tuyên bố độ khó hay hiệu năng thực nghiệm.

LevelManager cho chơi tiếp 14 màn theo số tệp. Việc thêm ba demo không thay
toàn bộ bộ benchmark để solver dễ giải. `levels/validation.json` lưu hash dữ
liệu, lời giải 14 màn và 24 witness kích hoạt công tắc. Nhóm vẫn cần chốt bộ
benchmark cố định và chạy cùng dữ liệu/limits cho tất cả thuật toán; kiểm
chứng dữ liệu không thay thế thực nghiệm so sánh hiệu năng.
