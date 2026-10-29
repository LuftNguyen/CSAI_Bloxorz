# Đối chiếu và quyết định triển khai

Baseline main local ngày 26/10/2026 đã merge BFS/DFS/UCS/A* và heuristic từ
nhánh thành viên. Mã thuật toán giữ nguyên; heuristic chưa bật/nghiệm thu.
Trạng thái hiện tại tại [INTEGRATION.md](INTEGRATION.md); phần dưới là lịch sử.

Lượt hoàn thiện dữ liệu 24/10/2026 được người dùng cho phép sửa liên kết và
khoảng đỡ: xem LEVEL_COMPLETION.md. Cả 14 màn/24 công tắc đã có witness thực
tế; không còn switch trang trí trong bộ màn đang cung cấp. Các ghi nhận bảo
toàn layout của lượt ban đầu không áp dụng cho các ô đổi được liệt kê mới này.

Cập nhật luật ngày 23/10/2026 trên `feature/new-game-rules`, nền `c237d10`.
Nguồn sản phẩm mới: `assignment/ASSIGNMENT.pdf` và `assignment/QA.md`;
`CSAI_Project.pdf` vẫn chỉ là contract nhóm. Lịch sử bản nền ban đầu bên dưới
được cập nhật để không nhầm phần đã làm với TODO còn lại. Xem trạng thái và
bằng chứng đầy đủ ở [REQUIREMENTS_STATUS.md](REQUIREMENTS_STATUS.md).

Nguồn: https://github.com/24127352/Bloxorz---CS-AI tại commit
`5571989db4ba9b4b8017b8c9486e955d551ff269`. PDF `CSAI_Project.pdf` có tiêu đề
**CONTRACT V1**, mô tả giao diện triển khai và phân công nhóm; đây là contract
nhóm đã cung cấp trong yêu cầu, không phải tài liệu đề đồ án riêng.
`CONTRACT.md` chứa nguyên văn văn bản trích bằng `pdftotext -layout`.
Bản trích có ngắt trang, tên trường bị xuống dòng trong bảng và thụt dòng mã
không đồng nhất; không nên sao chép trực tiếp mã từ bản trích để chạy.
Xem [hướng dẫn đọc bố cục](CONTRACT_LAYOUT.md). PDF là bản đối chiếu khi bố cục
trích xuất gây mơ hồ; không có thay đổi nội dung hay giao diện contract.

| Thành phần | Quyết định |
| --- | --- |
| Direction, Block và quy tắc lăn | Dùng lại, giữ tên/giá trị enum; bổ sung orientation vào equality/hash |
| Board, bộ đọc JSON | Dùng lại; giữ chi phí TILE_COST hiện có |
| Board.reset | Khôi phục tiles và bản sao initialBridgeState đã lưu của màn; không gán mọi trạng thái cầu bằng True lúc reset |
| State.copy | Giữ deepcopy; equality/hash có cubes/active, bridgeState, bridgeGroups, switchEffects, splitTargets và kích thước board |
| Problem | Giữ 5 tên giao diện; kiểm tra khối đầy đủ tại đích; thêm tùy chọn unit_cost=False tương thích lời gọi cũ |
| GameController | Dùng cùng rules.transition với Problem; giữ con thua cho hiệu ứng rơi/vỡ |
| GUI/menu/phát lại | Giữ; đổi điểm gọi sang runner, snapshot độc lập, hiển thị solver chưa triển khai/lỗi, hủy callback phát lại khi restart/đổi màn |
| InputHandler | Sửa phân loại Direction/Utility: nguồn trả Direction từ processKeyUtility khiến GUI bỏ mọi bước đi; bỏ sự kiện nhả phím hướng |
| LevelManager | Đường dẫn tương đối module; 11 màn nguồn được hoàn thiện liên kết và thêm 3 demo riêng, trần hiện tại 14 |
| contracts, registry, runner | Bổ sung; exceptions được truyền lên, không đổi thành unsolvable |
| BFS/DFS/UCS/A* | Trên nền hiện tại A* đã có; BFS/DFS/UCS vẫn là khung. Lần sửa luật không sửa các solver |
| heuristic | Chỉ h=0 chuẩn; heuristic khác và kiểm chứng do người 5 phụ trách |
| search/solver.py, search/bfs/bfsa.py | Giữ nguyên mã tham khảo, GUI/registry mới không gọi |
| search/problem.py | Bản Problem cũ khác gameModel.problem, giữ để đối chiếu; nhóm chỉ import gameModel.problem.Problem |

## Các điểm contract chưa chốt

- Không có SearchStatus “chưa triển khai”: khung ném NotImplementedError, runner
  truyền exception, GUI hiển thị thông báo. Không thêm status vào contract.
- Contract phân công DFS, yêu cầu đầu bài nhắc DFS/IDS. DFS thường có xử lý
  trạng thái lặp dùng được trên không gian hữu hạn, không cần giới hạn độ sâu
  hoặc thay đổi giao diện. Chỉ quy định thêm nếu nhóm chọn DFS giới hạn độ sâu
  hoặc IDS; đây không phải điều kiện chặn người 2 bắt đầu viết DFS.
- Chưa nêu nơi khai báo RunResult: đặt tại runner.py, giữ nguyên ba trường.
- Cấu hình chi phí bằng 1 dùng keyword tùy chọn Problem(..., unit_cost=True),
  không thay tên hàm hay chi phí mặc định. UCS/A* phải dùng cùng Problem.
- Nhóm cần chỉ định người duyệt State/Problem và giao diện chung; chưa có tên.

## TODO luật nâng cao và nguồn tham khảo

- Đã thêm split/SWITCH/teleport/ghép theo đề và QA, giữ giá trị bốn hướng cũ.
  `rules.py` dùng chung cho Problem/Controller; GUI có hai cube, đánh dấu active.
- Schema 2 hỗ trợ cầu mở/đóng ban đầu, ID cầu dùng chung và TOGGLE/OPEN/CLOSE;
  schema cũ vẫn tải được. Quy tắc nhiều switch và teleport được ghi riêng tại
  GAME_RULES.md vì nguồn không xác định đầy đủ thứ tự tương tác.
- bridgeMap hiện không được engine đọc; nếu dùng cho luật mới phải đưa thông tin
  ảnh hưởng chuyển trạng thái vào equality/hash. initialTiles phục vụ reset,
  không tham gia một bước tìm kiếm. Không sửa state đã nằm trong set/dict.
- Hash hiện gồm toàn bộ tiles, bridgeState, bridgeGroups và kích thước. Dữ liệu
  tĩnh của màn trong khóa có thể làm tra set/dict tốn hơn; chưa tối ưu khi chưa
  có benchmark. State vẫn là đối tượng có thể thay đổi: sau khi lưu vào `set`
  hoặc dùng làm khóa `dict`, không sửa `state.block`, `state.board` hoặc các
  danh sách/từ điển mà equality/hash sử dụng, kể cả dữ liệu lồng bên trong.
  Quy tắc này áp dụng cả khi sửa qua một tham chiếu khác tới cùng dữ liệu.
  Thao tác trên bản copy độc lập để sinh trạng thái con.
- Heuristic Manhattan cũ tự ghi admissible nhưng chưa được kiểm chứng; không dùng
  làm mặc định. Solver cũ có khác biệt đếm node, chi phí và quản lý tracemalloc;
  không dùng số liệu cũ làm kết quả thực nghiệm nhóm.
- Nguồn có gitlink `Bloxorz---CS-AI` tại `252c682...` nhưng không có .gitmodules.
  Giữ nguyên để bảo toàn nguồn; không cần init submodule hoặc dùng thư mục đó.
- Không thấy LICENSE/COPYING hay thông báo cấp phép trong cây mã nguồn tại commit
  trên; không tự gán giấy phép. README nguồn được lưu ở README.upstream.md.
  Nhóm cần làm rõ quyền tái sử dụng/phát hành với chủ nguồn trước khi công bố.

## Trạng thái nghiệm thu

Python đã kiểm tra: 3.13.13 trên Windows. Engine/headless đã chạy một màn cơ bản,
RIGHT RIGHT tới đích, cost=2.0. Kiểm thử tự động xem TESTING.md.
Chưa kiểm tra GUI tương tác thủ công; chưa nghiệm thu phát lại trong cửa sổ.
Đủ nền giao diện để các thành viên viết solver độc lập, nhưng chưa thể đánh dấu
toàn bộ checklist trước chia nhánh hoàn tất cho đến khi người dùng kiểm tra GUI.
Đã bổ sung kiểm thử luật và headless A* h=0; offscreen GUI smoke chạy được.
Chưa thể xác nhận tính tối ưu/hiệu năng toàn bộ benchmark hay solver chưa viết.
