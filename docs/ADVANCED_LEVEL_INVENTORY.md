# Kiểm kê màn chơi — 25/10/2026

Kết quả chạy lại bằng `python -B tests/audit_advanced_portfolio.py`. Mỗi truy vấn dùng A* đăng ký hiện có, h=0; chỉ `unsolvable` sau cạn frontier mới là bằng chứng âm. Chi tiết tọa độ ô đặc biệt và đường đi nằm trong [ADVANCED_LEVEL_EVIDENCE.json](ADVANCED_LEVEL_EVIDENCE.json).

| Màn | Kích thước | Start (đứng) → goal | Ô đặc biệt (số lượng) | Đầy đủ | Khi bỏ cơ chế |
| --- | --- | --- | --- | --- | --- |
| level1 | [6, 10] | [1, 1] → [1, 4] | w:2, W:2, F:2, B:4 | solved, 2 bước | bridge: solved |
| level2 | [20, 20] | [1, 1] → [16, 16] | w:1, W:1, F:9, B:8 | solved, 22 bước | bridge: solved |
| level3 | [8, 8] | [1, 1] → [4, 6] | không | solved, 6 bước | không áp dụng |
| level4 | [10, 10] | [1, 1] → [7, 8] | F:3 | solved, 9 bước | không áp dụng |
| level5 | [10, 20] | [2, 1] → [1, 16] | w:1, W:1, F:2, B:4 | solved, 16 bước | bridge: solved |
| level6 | [12, 12] | [1, 1] → [8, 10] | w:1, W:1, F:5, B:3 | solved, 15 bước | bridge: solved |
| level7 | [10, 12] | [1, 1] → [4, 9] | w:1, B:3 | solved, 20 bước | bridge: solved |
| level8 | [12, 12] | [1, 1] → [9, 9] | w:2, W:1, B:6 | solved, 12 bước | bridge: solved |
| level9 | [15, 15] | [1, 1] → [12, 12] | w:1, F:5, B:4 | solved, 17 bước | bridge: solved |
| level10 | [15, 15] | [1, 1] → [3, 11] | w:1, F:5, B:4 | solved, 13 bước | bridge: solved |
| level11 | [18, 18] | [1, 1] → [14, 14] | w:1, W:1, F:7, B:8 | solved, 18 bước | bridge: solved |
| level12 | [3, 10] | [1, 1] → [1, 7] | T:1 | solved, 7 bước | split: unsolvable, control: solved, merge: unsolvable |
| level13 | [4, 10] | [1, 1] → [1, 7] | w:1, W:1, B:1 | solved, 4 bước | bridge: solved |
| level14 | [4, 10] | [1, 1] → [1, 7] | w:2, W:1, B:2 | solved, 4 bước | bridge: solved |
| soft_gate | [3, 12] | [1, 1] → [1, 10] | w:1, B:2 | solved, 6 bước | bridge: unsolvable |
| heavy_gate | [3, 12] | [1, 1] → [1, 10] | W:1, B:2 | solved, 6 bước | bridge: unsolvable |
| split_control | [5, 10] | [1, 1] → [3, 1] | T:1, F:1 | solved, 7 bước | split: unsolvable, control: unsolvable, merge: unsolvable |
| split_gate | [5, 10] | [1, 1] → [3, 1] | w:1, T:1, B:2 | solved, 7 bước | split: unsolvable, control: unsolvable, bridge: unsolvable, merge: unsolvable |
| optional_gate | [3, 12] | [1, 1] → [1, 10] | w:1, B:1 | solved, 6 bước | bridge: solved |
| dead_gate | [3, 12] | [1, 1] → [1, 10] | w:1, B:2 | unsolvable, 0 bước | bridge: unsolvable |

Bỏ bridge nghĩa là bỏ toàn bộ effects công tắc trên bản sao, không xóa ô công tắc và không cấm đi qua nó. Đây là chứng minh phụ thuộc tác động cầu nói chung, không chứng minh từng công tắc riêng đều bắt buộc. Split và teleport là một chuyển tiếp nguyên tử; không thể tuyên bố đã kiểm tra độc lập hai cơ chế.

Các màn cũ đều được giữ vì demo, GUI, witness/reset và quy trình tài liệu đang dùng. Các màn cùng có cơ chế không mặc nhiên tương đương về coverage. Chưa chứng minh tương đương trạng thái giữa các màn nên không xóa màn nào. Các màn cầu vẫn solved khi bỏ effects chỉ cung cấp coverage tùy chọn cho cơ chế đó.
