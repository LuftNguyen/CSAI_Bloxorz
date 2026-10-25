# Luật và thứ tự xử lý một bước

## Bẫy permanent CLOSE bổ sung

Switch có `fatal_close: true` chỉ dùng CLOSE, kích hoạt sẽ chốt terminal loss
và không thể mở lại/đi tiếp trong lượt đó. Soft/heavy vẫn giữ điều kiện trọng
lượng và entry activation. Solver nhận result=None, GUI giữ successor để đếm
5 giây, báo thua 1 giây rồi reset. Board.fatalSwitch tham gia equality/hash;
reset xóa marker. OPEN/CLOSE không có cờ vẫn theo quy tắc phía dưới.
Đây là yêu cầu mới của người dùng, không phải timeout bắt buộc trong assignment.
Chi tiết và bằng chứng: [FATAL_CLOSE.md](FATAL_CLOSE.md).

Nguồn sản phẩm: `assignment/ASSIGNMENT.pdf` §§2.1–2.5, 3.1 và
`assignment/QA.md`. Giao diện tích hợp: `CONTRACT.md` và `CONTRACT_LAYOUT.md`.
Đề/QA không quy định hết thứ tự đồng thời; các quyết định dưới đây được công
khai để nhóm review, không được trình bày như lời giảng viên.

## Biểu diễn và hành động

Giữ `State(board, block)` và năm hàm Problem. Direction cũ giữ nguyên giá trị
UP=1, DOWN=2, LEFT=3, RIGHT=4; bổ sung SWITCH=5 theo contract §3.
SWITCH chỉ được Problem.actions trả ra khi split. Chi phí SWITCH=1.0 dương,
hữu hạn: đổi quyền điều khiển là một quyết định của agent, có tính vào độ dài
lời giải; `unit_cost=True` vẫn đặt mọi hành động bằng 1.

Khối đầy đủ giữ ba tư thế cũ. `Orientation.SPLIT` bổ sung hai tọa độ
`block.cubes` có thứ tự ổn định và `block.active` (0 hoặc 1). Khi split, r/c
phản ánh khối đang điều khiển, dr=dc=0. Mỗi khối đơn đi đúng một ô theo hướng.
Không tự tráo nhãn cube khi đổi quyền. Equality/hash gồm cả vị trí hai khối,
quyền điều khiển, tiles, trạng thái cầu và metadata luật của màn.

State vẫn mutable: không sửa block, board hoặc dữ liệu lồng tham gia khóa
trong thời gian state nằm trong set/dict. Tạo con bằng copy/result. State.copy
sao chép sâu toàn bộ Board. Không đưa Entity, animation hay thời gian vào state.

## Thứ tự chuyển trạng thái

`gameModel/rules.py:transition` là logic chung duy nhất cho result và executeMove.

1. Sao chép trạng thái. SWITCH trên khối đầy đủ bị từ chối; trên khối tách chỉ
   đổi active, không di chuyển, không kích hoạt switch hay tự ghép.
2. Lăn khối đầy đủ hoặc dịch cube đang điều khiển một ô.
3. Kiểm tra mọi ô của cả hai cube: ngoài biên, VOID, chồng ô đều rơi/thua.
   Khối đầy đủ đứng làm fragile thành VOID và rơi; nằm được đỡ. Theo QA,
   cube đơn được fragile đỡ, không làm vỡ ô.
4. Tính các công tắc **mới bắt đầu được đè đủ điều kiện**: tập pressed mới trừ
   pressed cũ. Soft nhận mọi tư thế/cube; heavy/split chỉ khối đầy đủ đứng.
   Một cube đứng yên trên soft không bị kích hoạt lại khi cube kia đi hoặc
   SWITCH. Rời ô rồi quay lại sẽ kích hoạt lại. Đây là quyết định triển khai;
   nguồn chưa quy định chính xác cách giữ áp lực qua nhiều lượt.
5. Xử lý switch theo tọa độ (hàng, cột) tăng dần; effects của cùng switch theo
   thứ tự khai báo. TOGGLE đảo, OPEN đặt mở, CLOSE đặt đóng. Mọi switch trỏ
   cùng bridge ID cùng sửa **một cờ cầu**. Tác động sau cùng quyết định nếu
   xung đột; không phụ thuộc thứ tự dict. Kiểm tra lại hỗ trợ của cả hai cube.
6. Nếu khối đầy đủ đứng mới kích hoạt split: teleport hai cube tới targets
   (cube 0 được điều khiển trước). Kiểm tra hỗ trợ cả hai trước tác động đích.
   Đích soft kích hoạt đúng một lần theo thứ tự tọa độ; fragile không vỡ;
   heavy/split không kích hoạt và cube trên goal chưa thắng. Không teleport
   dây chuyền. Cầu đích có thể được mở trước bởi bước khác; tới cầu đang đóng
   thì thua, không được dùng soft để cứu một cube đã mất hỗ trợ.
7. Hai cube cách nhau Manhattan đúng 1 tự ghép thành khối đầy đủ nằm theo
   trục tương ứng; không ghép chéo. Tác động khi còn cube đã xử lý xong, không
   kích hoạt thêm switch do ghép. Targets kề nhau cũng ghép ngay trong lượt
   teleport. Kiểm tra hỗ trợ cuối, rồi goal chỉ khi khối đầy đủ đứng tại G.

Problem trả None cho con thua, không sửa cha. Controller giữ con thất bại để
GUI thấy ô fragile đã mất và animate rơi. Game đang thua/thắng từ chối di chuyển
tiếp. Reset khôi phục tiles/cầu ban đầu và khối đầy đủ tại start.

## Chi phí và solver

Giữ TILE_COST gốc: normal/goal/bridge=1, soft/heavy=0.5, fragile=5.
Split switch dùng 0.5 như hai switch còn lại. Với khối đầy đủ, tính max các ô
đích; với cube di chuyển, tính ô cube đang điều khiển; lượt teleport/ghép tính
max các ô kết quả. Không đổi công thức heuristic của thành viên.

Nhánh hiện tại có A*, mặc định heuristic=None tức h=0. Runner chặn heuristic
khác zero trên board có splitTargets vì chưa được kiểm chứng với teleport;
BFS/DFS/UCS vẫn báo chưa triển khai, không gọi solver tham khảo thay thế.

`runner.validate_solution` chạy **sau** thời gian/đỉnh bộ nhớ solve: copy initial,
kiểm tra từng Direction/nước đi, cộng chi phí, kiểm tra goal và total_cost với
rel_tol=abs_tol=1e-9. GUI chỉ phát lại sau khi kiểm chứng thành công. Lỗi hiển
thị là lỗi solver/dữ liệu, không bị đổi thành unsolvable hoặc solved hợp lệ.

GUI đặt khối tức thời vào pose cuối, rồi render board kết quả trong cùng
lượt xử lý; không nội suy position/scale hoặc chờ 0.4 giây cho bước thường.
Split/teleport/SWITCH/merge hiển thị ngay kết quả logic. Chỉ fall còn hoạt ảnh
và barrier chờ animator thật; generation guard và cancelReplay vô hiệu fall,
timer hoặc replay cũ khi reset/đổi màn/New Game. Replay nghỉ replayInterval=0.5
giây giữa hai bước, không đổi thứ tự hoặc chi phí lời giải; chơi tay vẫn tức thời.
Chi tiết kiểm chứng và giới hạn: ANIMATION_SYNC.md. Tìm kiếm hiện vẫn đồng bộ
trên GUI: có thể đứng cửa sổ tối đa đến giới hạn solver. Thread/process và nút
hủy tìm kiếm là hạng mục riêng, chưa triển khai trong lần này.
