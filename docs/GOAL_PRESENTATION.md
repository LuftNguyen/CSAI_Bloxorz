# Goal hole và dẫn chiếu đề — 25/10/2026

Nguồn: [ASSIGNMENT.pdf](assignment/ASSIGNMENT.pdf), trang in số 3.
PDF không đánh số dòng; các số dưới đây thuộc bản trích trang 3 bằng
pdftotext -layout: [ASSIGNMENT_PAGE3.txt](assignment/ASSIGNMENT_PAGE3.txt).
Không sửa PDF nguồn.

- §2.4 Victory, dòng 6–7 bản trích: thắng khi khối đứng thẳng ở goal hole;
  nằm ngang qua goal không thắng.
- §2.5 Advanced tiles, Bridges, dòng 18–20: cầu đóng như empty space, cầu mở
  như sàn. Vì vậy đề có khoảng trống gây rơi ngoài goal hole; không yêu cầu
  mọi ô khuyết đều là đích hoặc phải xóa chúng.
- §2.5, đoạn ngay sau danh sách soft/heavy/split và trước Block splitting,
  dòng 33–35: toggle đảo mở/đóng theo mỗi activation; permanent đặt trạng thái
  cố định. OPEN/CLOSE là cách triển khai permanent, không phải tên nguyên văn.

## Hiển thị mới

GOAL trước đây là tấm tím đặc, nay là root chứa bốn cạnh viền xanh lá và đáy
tối thấp hơn mặt sàn. Không có tấm sàn đặc che miệng. VOID giữ khoảng trống,
cầu đóng giữ tấm tối, split giữ tím; mỗi màn vẫn chỉ có đúng một G theo loader.
Root sở hữu toàn bộ phần con nên redraw/reset/đổi màn xóa cả hốc và viền.

Chỉ đổi view và palette sơ đồ; không đổi goal_test, luật hỗ trợ/chi phí/solver,
không lấp VOID, không đổi chuyển động tức thời hoặc replay 0,5 giây. Đây là
hốc mô phỏng trình bày. Theo yêu cầu tiếp theo, đã thêm khối rơi vào đích,
cả bàn rơi/co dần theo làn sóng và blackout 1 giây trước khi sang màn: [WIN_TRANSITION.md](WIN_TRANSITION.md).

Đã chạy 7 test GUI rules, 11 visual sync, 14 foundation: **32 pass**;
smoke GUI offscreen phát đủ 10 màn pass và đã xem ảnh màn 7 có hốc viền xanh.
Chưa nghiệm thu desktop thủ công; không chạy lại toàn bộ suite trong lượt này.
Không commit/push.
