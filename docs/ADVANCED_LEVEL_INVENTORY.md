# Kiểm kê màn chơi — 25/10/2026

Kết quả chạy lại bằng `python -B tests/audit_advanced_portfolio.py`. Mỗi truy vấn dùng A* đăng ký hiện có, h=0; chỉ `unsolvable` sau cạn frontier mới là bằng chứng âm. Chi tiết tọa độ ô đặc biệt và đường đi nằm trong [ADVANCED_LEVEL_EVIDENCE.json](ADVANCED_LEVEL_EVIDENCE.json).

| Màn | Kích thước | Start (đứng) → goal | Ô đặc biệt (số lượng) | Đầy đủ | Khi bỏ cơ chế |
| --- | --- | --- | --- | --- | --- |
| level1 | [9, 11] | [1, 1] → [7, 9] | không | solved, 10 bước | không áp dụng |
| level2 | [15, 17] | [1, 5] → [9, 15] | F:2 | solved, 13 bước | không áp dụng |
| level3 | [10, 15] | [1, 1] → [7, 13] | F:4 | solved, 13 bước | fragile: unsolvable |
| level4 | [14, 14] | [1, 1] → [12, 12] | F:6 | solved, 26 bước | fragile: unsolvable |
| level5 | [10, 16] | [1, 1] → [8, 14] | w:3, W:2, B:3 | solved, 16 bước | bridge: unsolvable, bridge:crossing: unsolvable |
| level6 | [11, 17] | [6, 1] → [2, 15] | w:2, W:3, B:3 | solved, 20 bước | bridge: unsolvable, bridge:crossing: unsolvable |
| level7 | [11, 23] | [1, 1] → [1, 21] | w:3, W:4, B:6 | solved, 25 bước | bridge: unsolvable, bridge:first: unsolvable, bridge:second: unsolvable |
| level8 | [10, 24] | [1, 18] → [8, 1] | w:2, T:2, F:5, B:4 | solved, 20 bước | split: unsolvable, control: unsolvable, merge: unsolvable, fragile: unsolvable, bridge: unsolvable, bridge:landing: unsolvable |
| level9 | [17, 17] | [14, 1] → [1, 13] | w:5, T:2, B:3 | solved, 19 bước | split: unsolvable, control: unsolvable, merge: unsolvable, bridge: unsolvable, bridge:gate: unsolvable |
| level10 | [13, 26] | [1, 20] → [10, 1] | w:7, T:2, F:1, B:6 | solved, 26 bước | split: unsolvable, control: unsolvable, merge: unsolvable, bridge: unsolvable, fragile: unsolvable, bridge:near: unsolvable, bridge:far: unsolvable |
| soft_gate | [3, 12] | [1, 1] → [1, 10] | w:1, B:2 | solved, 6 bước | bridge: unsolvable |
| heavy_gate | [3, 12] | [1, 1] → [1, 10] | W:1, B:2 | solved, 6 bước | bridge: unsolvable |
| split_control | [5, 10] | [1, 1] → [3, 1] | T:1, F:1 | solved, 7 bước | split: unsolvable, control: unsolvable, merge: unsolvable |
| split_gate | [5, 10] | [1, 1] → [3, 1] | w:1, T:1, B:2 | solved, 7 bước | split: unsolvable, control: unsolvable, bridge: unsolvable, merge: unsolvable |
| optional_gate | [3, 12] | [1, 1] → [1, 10] | w:1, B:1 | solved, 6 bước | bridge: solved |
| dead_gate | [3, 12] | [1, 1] → [1, 10] | w:1, B:2 | unsolvable, 0 bước | bridge: unsolvable |

Bỏ bridge nghĩa là bỏ toàn bộ effects công tắc trên bản sao, không xóa ô công tắc và không cấm đi qua nó. Đây là chứng minh phụ thuộc tác động cầu nói chung, không chứng minh từng công tắc riêng đều bắt buộc. Split và teleport là một chuyển tiếp nguyên tử; không thể tuyên bố đã kiểm tra độc lập hai cơ chế.

Chuỗi chơi hiện có đúng 10 màn. Sáu màn cũ cần cho hồi quy hình học/loader được giữ riêng trong tests/fixtures/legacy, không nằm trong LevelManager. Fragile bị cấm bằng cách bỏ mọi chuyển tiếp hợp lệ có chiếm ô F, chứng minh bắt buộc đi qua chứ không yêu cầu làm vỡ ô. Các truy vấn bridge:ID chỉ bỏ effects của một nhóm cầu, giữ các công tắc khác hoạt động.
