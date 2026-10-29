# Đồ án Bloxorz — nền tích hợp thuật toán

Nhóm 5 người tự phát triển BFS, DFS/IDS, UCS, A*, heuristic và thực nghiệm.
BFS/DFS/UCS/A* đã tích hợp từ các nhánh thành viên, không dùng solver cũ thay thế.
Heuristic `manhattan` và `relaxed` chạy được trên cả màn split; A* với hai heuristic
này cho chi phí bằng UCS trên màn 8 và 9. GUI vẫn dùng h=0 (`heuristic=None`).
Chi tiết tại [INTEGRATION.md](docs/INTEGRATION.md).
Engine hỗ trợ fragile, cầu và
soft/heavy/split, teleport, SWITCH và ghép; xem trạng thái nghiệm thu thực tế
trong [REQUIREMENTS_STATUS.md](docs/REQUIREMENTS_STATUS.md).

Nguồn: [24127352/Bloxorz---CS-AI](https://github.com/24127352/Bloxorz---CS-AI),
commit [5571989db4ba9b4b8017b8c9486e955d551ff269](https://github.com/24127352/Bloxorz---CS-AI/commit/5571989db4ba9b4b8017b8c9486e955d551ff269).
Giữ lịch sử Git nguồn, remote `upstream`, nhánh tích hợp `main`.
Repository nhóm Public: [LuftNguyen/CSAI_Bloxorz](https://github.com/LuftNguyen/CSAI_Bloxorz).
Remote `origin` trỏ tới repository nhóm; `upstream` giữ repository nguồn.

Dùng lại Block/Direction, Board, State, Problem, GameController, bộ đọc màn,
GUI/menu và cơ chế phát lại; chuỗi chơi có đúng 10 màn: 2 cơ bản, 2 fragile,
3 cầu/công tắc và 3 split với bằng chứng cơ chế bắt buộc. `search/solver.py`,
`search/bfs/bfsa.py`, node và `search/problem.py` cũ là **mã tham khảo của
nguồn**, không phải thuật toán nhóm tự cài. Heuristic cũ chưa được mặc định
coi là admissible. Nhóm dùng `gameModel.problem.Problem` làm giao diện chung.

Bộ 10 màn đã mở rộng thành phòng và đảo nối cầu, 10–26 bước với A* h=0;
xem [bản đồ](docs/CAMPAIGN_MAPS.svg) và [kết quả kiểm chứng](docs/CAMPAIGN.md).

Không tìm thấy LICENSE/COPYING trong cây nguồn tại commit trên; không tự gán
MIT hay giấy phép khác. README nguồn giữ nguyên tại
[README.upstream.md](README.upstream.md). Nhóm cần làm rõ quyền tái sử dụng/phát
hành với chủ nguồn trước khi công bố; các nội dung nguồn khác được giữ lại.

## Chạy nhanh

Đã kiểm tra Python **3.13.13** trên Windows. Headless/test chỉ dùng thư viện chuẩn:

```powershell
python -m unittest discover -s tests -v
python -m examples.headless
python -m examples.rules_headless
python -m examples.audit_levels
```

Ví dụ tải màn 1, thử bốn hướng, phát fixture RIGHT RIGHT tới đích với cost=2.0.
Đây là chuỗi kiểm tra kết nối, không phải solver được viết thay thành viên.

Chạy game từ thư mục gốc repository:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

Dependency giữ nguyên bản ghim nguồn. WASD/mũi tên để lăn, Space đổi cube khi
tách, P để pause, R để restart. Nút SOLVER trên màn hình chơi mở bảng chọn
BFS/DFS/UCS/A*; chọn BACK TO GAME hoặc nhấn P để quay lại. Cầu đóng biến mất
hoàn toàn, chỉ hiện khi công tắc mở cầu. Khối xoay 90° quanh cạnh khi lăn
(0,22 giây/bước); công tắc và hiệu ứng cập nhật khi tiếp đất. Có New Game/Restart. A* mặc định
h=0; lời giải phải qua kiểm chứng trước khi phát lại. Tìm kiếm chạy nền để giao diện
vẫn nhận nút bấm. MENU/P và SOLVER tạm dừng chuyển động, kể cả giữa cú lăn;
BACK TO GAME/P tiếp tục replay. Chọn thuật toán khác hủy lời giải cũ và tìm từ
trạng thái hiện tại (hoàn tất cú lăn đang dở trước khi tìm). Khi mở panel, tìm kiếm
nền có thể hoàn tất nhưng replay chỉ chạy khi tiếp tục game. Đã kiểm tra engine, mock GUI và offscreen;
chưa nghiệm thu GUI tương tác thủ công. Đây chưa phải kết quả benchmark.

## Tài liệu và phân công

- **Contract gốc:** [CSAI_Project.pdf](CSAI_Project.pdf).
- **Bản trích:** [CONTRACT.md](docs/CONTRACT.md).
- **Hướng dẫn đọc bố cục:** [CONTRACT_LAYOUT.md](docs/CONTRACT_LAYOUT.md).
- [Đối chiếu nguồn, sửa tối thiểu và TODO](docs/BASELINE.md).
- [Cài đặt, test, checklist GUI, tạo remote và nhánh](docs/TESTING.md).
- [Luật và thứ tự tương tác](docs/GAME_RULES.md), [schema màn](docs/LEVEL_SCHEMA.md).
- [Yêu cầu và bằng chứng](docs/REQUIREMENTS_STATUS.md), [bàn giao luật mới](docs/RULES_HANDOFF.md).
- [Các liên kết màn đã hoàn thiện và cách thử](docs/LEVEL_COMPLETION.md):
  tài liệu lịch sử; bộ hiện hành tại [Chuỗi 10 màn](docs/CAMPAIGN.md).
- Người 1: `search/bfs.py`; người 2: `search/dfs.py`; người 3: `search/ucs.py`;
  người 4: `search/astar.py`; người 5: `search/heuristics.py`, kiểm chứng A*.
- Giao diện chung: `search/contracts.py`, `search/registry.py`, `runner.py`.
  Mọi solver có `solve(problem, limits, heuristic=None) -> SearchResult`.
  Runner đo toàn bộ solve bằng perf_counter/tracemalloc, trả RunResult;
  lỗi chương trình/dữ liệu truyền lên dạng exception.

`State` vẫn có thể thay đổi. Sau khi lưu trạng thái vào `set` hoặc dùng làm khóa
`dict`, không sửa `state.block`, `state.board` hoặc các danh sách/từ điển mà
equality/hash sử dụng, kể cả dữ liệu lồng bên trong. Sinh trạng thái con trên
bản sao độc lập bằng `State.copy()` hoặc qua `Problem.result()`.

Cần chỉ định người duyệt giao diện chung. DFS thường không cần giới hạn độ sâu;
chỉ quy định thêm nếu chọn DFS giới hạn độ sâu hoặc IDS, giữ giao diện hiện tại.
