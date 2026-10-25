# Hoàn thiện công dụng các ô và liên kết màn — 24/10/2026

Phạm vi này được người dùng cho phép sau phần triển khai luật: hoàn thiện dữ
liệu màn để công tắc thật sự hoạt động. Không sửa solver/heuristic, không đổi
contract hay luật engine, không commit/push hoặc thao tác nhánh khác.
Đây là phiên bản dữ liệu màn mới; không trộn kết quả benchmark cũ/mới.

## Sửa dữ liệu có chủ đích

Tọa độ dưới đây tính từ 0, dạng [hàng, cột].

| Màn | Vấn đề trước sửa | Thay đổi |
| --- | --- | --- |
| 1 | Bốn w/W không có cầu hoặc liên kết | Chuyển schema 2; thêm cầu `upper_practice` ở [3,5], [3,6] và `lower_practice` ở [5,5], [5,6], đều ban đầu đóng. W[3,3]/w[5,3] TOGGLE cầu trên; W[3,4]/w[5,4] TOGGLE cầu dưới. Bốn ô X thành B, không đổi start/goal hay các ô cũ khác |
| 2 | Tệp level2 nhưng level_id=12, tên Stage 12 | Đổi metadata thành level_id=2, tên Stage 2: Final Trial; giữ nguyên grid và liên kết |
| 5 | Reference [6,15] trỏ sàn, W thực ở [6,14] | Giữ bản sửa đã được chấp nhận: [6,14]. Hai switch cùng một nhóm cầu vật lý |
| 6 | W[4,2] có liên kết nhưng không thể tiếp cận khi đứng | X[2,2] thành sàn; khối có thể đi DOWN RIGHT DOWN từ start để đứng W, nằm qua F[3,2] mà không vỡ. Giữ các cầu/liên kết cũ |
| 8 | W[3,7] không có liên kết | Chuyển schema 2, giữ grid và hai cầu cũ ban đầu mở. W[3,7] TOGGLE cả `crossbar` [5,5..7] và `side_crossing` [6..8,9]; hai soft giữ tác động TOGGLE cầu tương ứng |
| 13 | W[2,2] không thể đứng do thiếu chỗ lăn | X[3,1], X[3,2] thành sàn. OPEN/CLOSE và cầu ban đầu đóng giữ nguyên |
| 14 | W[2,2] không thể đứng do thiếu chỗ lăn | X[3,1], X[3,2] thành sàn. Giữ các mode và nhóm cầu |
| 3,4,7,9,10,11,12 | Không phát hiện công tắc thiếu liên kết | Không đổi dữ liệu trong lượt hoàn thiện này |

Không nối cầu tự động theo màu hoặc khoảng cách: mỗi tác động được khai báo
cụ thể trong JSON. Màn không có công tắc (3,4) vẫn là màn cơ bản/fragile hợp lệ,
không cần tự thêm công tắc. Công tắc loại nào cũng cần đúng điều kiện kích hoạt
của engine: w nhận khối nằm/đứng/cube; W chỉ khối đầy đủ đứng; T teleport/split.

## Thử trực tiếp màn 1

- Đường thắng cũ vẫn là RIGHT RIGHT; các cầu tập luyện là nhánh tùy chọn,
  không ép người chơi vòng xa để qua màn giới thiệu.
- Từ start, RIGHT DOWN DOWN RIGHT để đứng W[3,4]: cầu dưới bên phải mở.
- Restart, DOWN LEFT DOWN RIGHT UP RIGHT để đứng W[3,3]: cầu trên bên phải mở.
- Soft ở hàng 5 cũng đảo đúng các cầu trên; xem chuỗi đầy đủ trong
  `levels/validation.json` nếu cần tái hiện mọi công tắc.
- Cầu đóng là tấm mỏng tối màu, không đỡ khối; mở là cầu nâu, có thể đi qua.
  Khi đã ở đích và thắng, phải restart trước khi thử tiếp các công tắc.

## Bằng chứng kiểm chứng

`python -m examples.audit_levels --write` dùng **A* đã có**, h=0, giới hạn
10 giây/100000 node cho mỗi lần gọi. Không thêm thuật toán tìm kiếm.

1. Giải mục tiêu thật của 14 màn, verify goal/chi phí ngoài khoảng đo,
   phát lại qua controller và đối chiếu trạng thái cuối.
2. Tìm đường kích hoạt riêng từng switch bằng một goal kiểm tra dữ liệu
   (`ActivationProblem`), không tuyên bố đó là lời giải thắng màn. Cấm tiếp tục
   đi sau khi đã thắng. Kiểm tra thực sự đổi cờ cầu hoặc teleport/tách, không
   chỉ có một bản ghi JSON. Mọi bước phát lại khớp controller.
3. Lưu chuỗi hành động/cost và hash nội dung từng JSON trong
   `levels/validation.json`. Đây là witness kiểm thử, không phải số liệu benchmark.
4. `tests/test_level_links.py` phát lại các witness mà không chạy tìm kiếm,
   kiểm tra reset, cost, hash dữ liệu, tất cả w/W/T/B có liên kết hợp lệ.

| Màn | Số bước lời giải A* h=0 | Cost | Công tắc đã kích hoạt kiểm chứng |
| --- | --- | --- | --- |
| 1 | 2 | 2 | 4 |
| 2 | 22 | 22 | 2 |
| 3 | 6 | 6 | 0 |
| 4 | 9 | 9 | 0 |
| 5 | 16 | 16 | 2 |
| 6 | 15 | 23 | 2 |
| 7 | 20 | 20 | 1 |
| 8 | 12 | 12 | 3 |
| 9 | 17 | 17 | 1 |
| 10 | 13 | 13 | 1 |
| 11 | 18 | 18 | 2 |
| 12 | 7 | 6.5 | 1 |
| 13 | 4 | 4 | 2 |
| 14 | 4 | 4 | 3 |

Kết quả: **14 lời giải thắng và 24 witness kích hoạt hợp lệ**, **53 test pass**;
GUI offscreen smoke cũng pass. Chưa nghiệm thu hình ảnh/điều khiển GUI thủ công;
chưa benchmark so sánh các solver hoặc kiểm chứng heuristic khác zero.

Chạy lại audit không ghi tệp: `python -m examples.audit_levels`.
Khi chỉnh dữ liệu, chạy `python -m examples.audit_levels --write` rồi unittest;
test sẽ báo nếu witness không còn khớp hash màn. Không tự sửa witness để né
một lỗi luật hoặc liên kết không có đường kích hoạt.
