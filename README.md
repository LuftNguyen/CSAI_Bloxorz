# Đồ án Bloxorz — nền tích hợp thuật toán

Nhóm 5 người tự phát triển BFS, DFS/IDS, UCS, A*, heuristic và thực nghiệm.
Bốn solver nhóm hiện **chưa triển khai**; GUI/runner báo rõ, không gọi solver
cũ thay thế. Chưa bổ sung luật nâng cao.

Nguồn: [24127352/Bloxorz---CS-AI](https://github.com/24127352/Bloxorz---CS-AI),
commit [5571989db4ba9b4b8017b8c9486e955d551ff269](https://github.com/24127352/Bloxorz---CS-AI/commit/5571989db4ba9b4b8017b8c9486e955d551ff269).
Giữ lịch sử Git nguồn, remote `upstream`, nhánh tích hợp `main`.
Repository nhóm chưa tạo; chưa có `origin`, chưa push.

Dùng lại Block/Direction, Board, State, Problem, GameController, bộ đọc màn,
11 màn JSON, GUI/menu và cơ chế phát lại. `search/solver.py`,
`search/bfs/bfsa.py`, node và `search/problem.py` cũ là **mã tham khảo của
nguồn**, không phải thuật toán nhóm tự cài. Heuristic cũ chưa được mặc định
coi là admissible. Nhóm dùng `gameModel.problem.Problem` làm giao diện chung.

Không tìm thấy LICENSE/COPYING trong cây nguồn tại commit trên; không tự gán
MIT hay giấy phép khác. README nguồn giữ nguyên tại
[README.upstream.md](README.upstream.md). Nhóm cần làm rõ quyền tái sử dụng/phát
hành với chủ nguồn trước khi công bố; các nội dung nguồn khác được giữ lại.

## Chạy nhanh

Đã kiểm tra Python **3.13.13** trên Windows. Headless/test chỉ dùng thư viện chuẩn:

```powershell
python -m unittest discover -s tests -v
python -m examples.headless
```

Ví dụ tải màn 1, thử bốn hướng, phát fixture RIGHT RIGHT tới đích với cost=2.0.
Đây là chuỗi kiểm tra kết nối, không phải solver được viết thay thành viên.

Chạy game từ thư mục gốc repository:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

Dependency giữ nguyên bản ghim nguồn. WASD/mũi tên để lăn, P để pause,
R để restart. Solver nhóm hiển thị chưa triển khai cho đến khi được tích hợp.
Đã kiểm tra engine tự động; chưa kiểm tra GUI tương tác thủ công.

## Tài liệu và phân công

- **Contract gốc:** [CSAI_Project.pdf](CSAI_Project.pdf).
- **Bản trích:** [CONTRACT.md](docs/CONTRACT.md).
- **Hướng dẫn đọc bố cục:** [CONTRACT_LAYOUT.md](docs/CONTRACT_LAYOUT.md).
- [Đối chiếu nguồn, sửa tối thiểu và TODO](docs/BASELINE.md).
- [Cài đặt, test, checklist GUI, tạo remote và nhánh](docs/TESTING.md).
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
