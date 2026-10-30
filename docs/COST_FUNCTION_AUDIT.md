# Kiểm toán nguồn gốc, tính đúng và độ nhạy của hàm chi phí

Ngày: **30/10/2026**. Đã pull fast-forward `main` từ `13fbe98` lên **2edd0bd**.
Đối chiếu upstream gốc **5571989db4ba9b4b8017b8c9486e955d551ff269**;
`upstream/main` sau fetch hiện vẫn cùng commit này. Không so với baseline giả định.

Giữ tài liệu local chưa commit: bản sao trước pull tại
`.source-import/cost-audit-before-pull/`; khôi phục liên kết NEXT_PHASE_ACCEPTANCE
trên bản INTEGRATION mới, không thay nội dung cập nhật của remote. Không dùng stash.
Tệp NEXT_PHASE_ACCEPTANCE là tài liệu ngày 26/10, không dùng nó để mô tả kết quả
heuristic/GUI sau các cập nhật ngày 30/10.

## 1. Kết luận trước

**Không phải một hàm cost hoàn toàn do nhóm tự nghĩ ra.** Cách lấy **max chi phí
các ô khối chiếm sau bước đi** và các trọng số terrain đã có từ upstream.
Nhóm mở rộng cho luật mới và thay trọng số ngày 30/10:

| Thành phần | Upstream 5571989 | Main 2edd0bd | Nguồn thay đổi |
| --- | --- | --- | --- |
| NORMAL / GOAL / BRIDGE | 1 / 1 / 1 | 1 / 1 / 1 | Dùng lại |
| SOFT_SWITCH / HEAVY_SWITCH | 0,5 / 0,5 | 0,75 / 0,75 | Nhóm chỉnh trọng số |
| FRAGILE | 5 | 4 | Nhóm chỉnh trọng số |
| SPLIT_SWITCH | Chưa có | 0,75 | Nhóm thêm tile và cost |
| Lăn khối đầy đủ | max trên ô đích khối chiếm | Cùng nguyên tắc | Dùng lại công thức |
| Cube đang split di chuyển | Chưa có | Chỉ ô đích active cube | Nhóm thêm |
| Teleport/split/merge | Chưa có | max trên ô khối kết quả chiếm | Nhóm thêm |
| Hành động SWITCH đổi cube | Chưa có | 1 | Nhóm thêm, khác việc đè công tắc vật lý |
| `unit_cost=True` | Chưa có | Mọi action hợp lệ cost 1 | Nhóm thêm để đối chiếu |

**Đánh giá:** chính sách hiện tại nhất quán về toán học và dùng được để tối ưu
weighted cost. Chưa có cơ sở gọi bộ hệ số `4 / 0,75` là tốt nhất cho trải nghiệm,
số bước, độ an toàn hoặc hiệu năng. Nếu mục tiêu là ít thao tác nhất, nó không
trùng mục tiêu đó; dùng chế độ unit cost để đánh giá số bước.

## 2. Nguồn mã và lịch sử thực tế

- [gameModel/board.py](../gameModel/board.py): enum và `TILE_COST`.
- [gameModel/problem.py:21](../gameModel/problem.py#L21): `step_cost` đang dùng.
  Git `show 5571989:gameModel/problem.py` xác nhận upstream đã có max TILE_COST
  và kiểm tra VOID trước max.
- `5a31e23`: thêm tùy chọn `unit_cost`; `1ad25ae`: thêm ngữ nghĩa split/SWITCH.
- **d37bd16** (`feat(cost): change tile_cost`): chính commit đổi F=5 thành 4 và
  switch=0,5 thành 0,75, gồm cả split. **3b8d2de** cập nhật test/manifest theo số mới.
- Trong phạm vi diff, commit message, test và tài liệu đã đọc, **không tìm thấy
  thí nghiệm lựa chọn bộ trọng số hoặc hàm mục tiêu độc lập để biện minh nó tốt hơn**.
  Có regression chứng minh tính toán đúng theo trọng số và test weighted-vs-unit;
  việc sửa expected value cho khớp cost mới không phải kiểm chứng chọn hệ số tối ưu.
- Không thấy callable riêng tên `cost_function` trong luồng chính. API thật là
  `Problem.step_cost`. `search/problem.py` và `search/solver.py` là mã tham khảo cũ,
  không phải đường chạy GUI/registry hiện tại.

Các lệnh kiểm tra nguồn gồm:

```powershell
git fetch origin main
git pull --ff-only origin main
git fetch upstream main
git show 5571989:gameModel/board.py
git show 5571989:gameModel/problem.py
git diff 5571989..HEAD -- gameModel/problem.py gameModel/board.py
git log --oneline -- gameModel/problem.py gameModel/board.py
git show d37bd16 -- gameModel/board.py
git show 3b8d2de -- tests/test_ucs.py tests/test_heuristics.py levels/validation.json
```

## 3. Cost thực sự được dùng như thế nào?

### Định nghĩa

Với một chuyển tiếp **hợp lệ** `s --a--> s'`:

1. Nếu `unit_cost=True` hoặc `a == Direction.SWITCH`: trả `1.0`.
2. Nếu cả trước và sau đều split: tập ô tính tiền chỉ có active cube sau bước đi.
3. Các trường hợp khác: tập ô tính tiền là toàn bộ `s'.block.occupied()`.
4. Đọc tile từ **board của s'**, không phải tile nguồn. Có VOID thì trả infinity;
   ngược lại trả max trọng số trong tập. Solver thực tế không nhận cạnh rơi/thua
   vì `Problem.result` đã trả None; infinity không phải cost của một bước hợp lệ.

Do đó cost phụ thuộc action, orientation của state trước và block/board của state
sau; không cộng một khoản riêng cho việc mở cầu hoặc kích hoạt switch.

Ví dụ hiện tại: nằm trên NORMAL+NORMAL = 1 (không phải 2); SOFT+NORMAL = 1;
SOFT+SOFT = 0,75; FRAGILE+NORMAL hay FRAGILE+FRAGILE đều = 4. Khi split,
cube bất động đứng trên F không làm tăng cost của cube active đi trên N.
Đứng vào split pad rồi teleport tới một target F sẽ bị tính 4, không phải 0,75
của pad. Đổi active cube luôn 1, không đọc terrain.

### Call sites đã xác minh

- `view.py:224,611,758` tạo `Problem(...)` không truyền unit_cost: dùng **False**.
- `gui_search.py:13–15` tạo `SearchJob(Problem)` và giữ `problem.unit_cost`.
  Không có chuyển sang unit mode ngầm. `gui_search.py:35–38` truyền relaxed cho A*.
- `examples/headless.py`, `examples/check_astar_game.py`, `examples/audit_levels.py`
  dùng mặc định. `examples/benchmark_dfs.py` và test có chạy cả hai chế độ.
- BFS/DFS cộng step_cost để báo cáo nhưng không dùng nó làm ưu tiên; BFS tối ưu
  số action, DFS không bảo đảm số action hay weighted cost tối ưu.
- UCS dùng tổng `g`; A* dùng `g+h`. Cả hai gọi cùng `Problem.step_cost`.
  `runner.validate_solution` replay và tính lại tổng cost ngoài phần đo solver.

**Cập nhật so với báo cáo ngày 26/10:** heuristic đã được thành viên sửa; GUI
hiện chọn relaxed cho A*, runner cho phép heuristic đã đăng ký ở màn split.
Không áp dụng kết luận “GUI vẫn h=0” của baseline cũ cho main mới.

## 4. Vì sao chọn các hệ số này? Điều gì có thể chứng minh?

Không có giải thích đủ để quy kết ý định tác giả. Có thể diễn giải chính sách:
F đắt hơn N để ưu tiên tránh fragile; switch rẻ hơn N để ưu tiên các bước đáp
hoàn toàn lên switch; `max` tránh tự nhân đôi cost chỉ vì khối nằm chiếm hai ô.
**Đây là diễn giải mô hình, không phải bằng chứng tác giả đã tối ưu hệ số.**

So với upstream, F giảm 20%, switch tăng 50%: giảm chênh lệch giữa hai loại
terrain. Tỉ lệ F/switch giảm từ 10 xuống khoảng 5,33. Điều này chỉ cho biết thay
đổi mức ưu tiên; không tự suy ra đường đi hay hiệu năng tốt hơn.

### Bảo đảm hình thức của cost hiện tại

Với cạnh hợp lệ trong chế độ mặc định, mọi trọng số nằm trong [0,75;4], SWITCH=1.
Do max của các giá trị trong đoạn vẫn thuộc đoạn đó:

```text
0,75 <= c(s,a,s') <= 4
0,75 L <= cost(path gồm L action) <= 4 L
```

Không có cạnh 0/âm và không có chu trình âm; thêm một chu trình không thể tự
làm giảm cost của cùng đường đi. Với trạng thái hữu hạn, UCS có các điều kiện
chi phí để tìm đường tối ưu theo **chính hàm cost này**. A* còn cần heuristic
admissible và xử lý reopening nếu không consistent; positivity riêng không đủ.
Với unit cost, tổng cost = số action nên UCS/A* h=0 tối ưu số bước.

Các mệnh đề này không chứng minh 4 là mức phạt phù hợp tâm lý người chơi hoặc
0,75 là mức thưởng công tắc tối ưu. “Solver tối ưu theo cost” và “cost phản ánh
đúng mục tiêu thực tế” là hai câu hỏi khác nhau.

## 5. Kiểm chứng mới đã thực hiện

Mã tái chạy: [examples/audit_cost_models.py](../examples/audit_cost_models.py).
Dữ liệu đầy đủ: [COST_AUDIT_EVIDENCE.json](COST_AUDIT_EVIDENCE.json), gồm revision,
hash JSON màn, cấu hình, actions, cost, số bước, exposure, node và status từng run.

### Thiết kế trước khi chạy

- Giữ nguyên luật và board cho mọi cấu hình. 10 màn campaign + hai board nhỏ
  cố định có đường tắt qua fragile và đường vòng; không thay fixture giữa cấu hình.
- Bảy cấu hình: hiện tại (F4/S0,75), trọng số upstream mở rộng cho split (F5/S0,5),
  unit cost, F2/S0,75, F8/S0,75, F4/S0,5 và F4/S1. NORMAL/GOAL/BRIDGE giữ 1.
- “Upstream mở rộng” chỉ dùng **trọng số** nguồn trên **engine mới** để kiểm soát
  biến luật; không giả vờ engine upstream hỗ trợ split hoặc đã chạy nguyên game cũ.
- Mỗi case có BFS unit tìm số bước tối thiểu; UCS và A* relaxed trên từng cấu hình.
  Timeout 30 giây/lượt, max expanded 1.000.000. Chỉ so lượt solved; timeout không
  được đổi thành unsolvable hoặc kết luận optimality.
- Replay mọi lời giải; kiểm tra từng cạnh cost dương/hữu hạn, khớp biểu thức tham
  chiếu, goal/cost đúng và state nguồn không đổi. Không thay code solver/heuristic.
- Đổi mapping cost **chỉ trong tiến trình audit riêng**, context luôn restore kể
  cả exception. Cache heuristic gắn Problem mới cho mỗi cấu hình, không tái dùng
  bảng của cấu hình trước. Không chạy audio/GUI trong audit.

### Kết quả

**168/168 lượt UCS/A* solved**, replay pass; cost UCS bằng A* trong toàn bộ
84 cặp case/cấu hình. Thêm 12 lượt BFS unit làm chuẩn số bước. Đây là kiểm
chứng hữu hạn và phân tích độ nhạy, không phải chứng minh heuristic trên mọi màn
có thể tạo, không phải benchmark thời gian hoặc tìm bộ trọng số tốt nhất.

| Màn | Số bước tối thiểu | UCS hiện tại: bước / cost | UCS trọng số upstream: bước / cost |
| --- | --- | --- | --- |
| 1 | 10 | 10 / 10 | 10 / 10 |
| 2 | 13 | 13 / 13 | 13 / 13 |
| 3 | 13 | 13 / 16 | 13 / 17 |
| 4 | 23 | 26 / 32 | 26 / 34 |
| 5 | 16 | 16 / 15,75 | 16 / 15,5 |
| 6 | 20 | 20 / 19,75 | 20 / 19,5 |
| 7 | 25 | 25 / 24,75 | 25 / 24,5 |
| 8 | 20 | 20 / 35 | 20 / 40 |
| 9 | 19 | 19 / 18,75 | 19 / 18,5 |
| 10 | 26 | 26 / 28,5 | 26 / 29 |

Không so trực tiếp số cost giữa hai cột để kết luận tốt hơn: đơn vị/phạt đã đổi.
Trên cả 10 màn, **chuỗi actions UCS hiện tại giống hệt chuỗi chọn với trọng số
upstream** trong lượt chạy này. Vì vậy bộ campaign này chưa cho bằng chứng về
một cải thiện lựa chọn đường của 4/0,75 so với 5/0,5.

Một số đối chiếu có ý nghĩa:

- Màn 2: BFS unit tìm một đường 13 bước có cost **16** dưới cost hiện tại;
  UCS chọn đường khác cũng 13 bước nhưng cost **13**, không đáp F. Chứng minh
  bộ phạt có tác dụng phân biệt đường, không chứng minh duy nhất F=4 là đúng.
- Màn 4: đường unit 23 bước có 4 bước bị tính F, cost hiện tại **35**; UCS chọn
  26 bước, 2 lần F, cost **32**. Chấp nhận thêm 3 thao tác để bớt 2 lần đáp F.
  Khi F=2, UCS quay về 23 bước/cost 27: lựa chọn nhạy theo phạt như dự kiến.
- Board `two_fragile_tradeoff`: ngắn nhất 4 bước, 2 lần F; current chọn đường
  vòng **8 bước/cost 8**, thay vì đường ngắn **4 bước/cost 10**. Khi F=2, chọn
  4 bước/cost 6. Mức phạt là một đánh đổi, không phải điều kiện thắng.
- Board `one_fragile_tie`: đường 2 bước qua F và đường vòng 5 bước đều cost 5
  khi F=4; UCS chọn đường 2 bước trong lần chạy. Khi F=5, đường qua F cost 6,
  chọn đường vòng 5 bước/cost 5. Do đó F=4 **không bảo đảm** ưu tiên tránh F
  lúc hòa cost; `max` không thêm tiêu chí phụ về exposure hoặc số bước.
- Ở màn 10 current, A* relaxed mở rộng **2560** node, UCS **2466**. Heuristic
  có thể kém UCS về số expansion ở một màn; cost tối ưu vẫn khớp. Không suy ra
  thay đổi weights làm A* luôn nhanh hơn, và node không phải số giây đo thực tế.

### Unit/property test bổ sung

[tests/test_cost_policy_audit.py](../tests/test_cost_policy_audit.py) có 6 test:
max không phải sum; mixed switch không luôn được discount; active cube/SWITCH;
teleport tính target; restore mapping khi lỗi; duyệt mọi cạnh reachable của board
nhỏ dưới ba policy và đối chiếu oracle cost. Một test dựng đầy đủ đồ thị board nhỏ,
dùng Bellman–Ford độc lập để đối chiếu UCS optimal cost (không chỉ so hai heap solver).
Sáu test đều pass. Full regression cuối: **213 test pass**, Python subprocess
exit 0 (117,330 giây), gồm test heuristic mới nhất của nhóm và sáu test audit.
Lượt đầu trước khi thêm test audit cũng có 207 test pass; PowerShell bọc stderr
unittest thành NativeCommandError khi redirect, nên lượt cuối dùng subprocess
thu stdout/stderr và xác nhận exit code Python trực tiếp. Không coi dòng bọc
stderr đó là lỗi thuật toán. Log cuối ở `.source-import/cost-audit-regression-final.log`.

### Vì sao không dùng mạng neuron nhỏ?

Không có nhãn độc lập như mức ưa thích đường đi của người chơi, tỉ lệ thao tác lỗi,
thời gian chơi thật hoặc năng lượng. Train model dự đoán chính cost đang định
nghĩa chỉ học lại công thức, không xác nhận nó đúng mục tiêu. Game đang tất định,
fully observable; đồ thị nhỏ có oracle chính xác nên test/shortest path đáng tin
hơn một xấp xỉ ML cho câu hỏi này. Không huấn luyện model hoặc sửa thuật toán.

Nếu muốn học trọng số: chốt trước mục tiêu, thu nhãn độc lập, chia train/held-out
theo màn/nhóm bố cục, đánh giá chéo với unit/upstream/current và replay mọi lời
giải. Kết quả thử hữu hạn vẫn không phải chứng minh một hệ số tối ưu phổ quát.

## 6. Hạn chế của chính sách hiện tại

1. **Không tối ưu số bước:** ví dụ 23→26 ở campaign 4 hoặc 4→8 ở board nhỏ.
2. **Penalty không phải rủi ro xác suất:** nằm/cube trên F là hợp lệ và an toàn
   theo engine; đứng lên F bị loại bởi luật, không phải chỉ bị phạt. Chưa có mô
   hình nhiễu để suy ra phạt 4 từ xác suất thua. Đừng gọi cost là expected loss.
3. **Discount công tắc chỉ theo terrain, không theo công dụng:** đáp switch đã
   mở cầu từ trước vẫn có thể rẻ; mixed switch+N không rẻ. Không trực tiếp đo
   ích lợi mở đường, số nhóm cầu hoặc tính hữu ích của activation.
4. **Max mất thông tin:** một hay hai ô F đều 4, hai switch không cộng đôi;
   không biểu diễn tổng tiếp xúc/vật liệu/năng lượng. Đây là lựa chọn mô hình.
5. **Split/teleport/merge có quy ước riêng:** teleport tính target, không pad hoặc
   khoảng cách; inactive cube không bị tính thêm ở lượt active đi. Chưa có chi phí
   “khó điều khiển hai cube” ngoài mỗi SWITCH=1.
6. **Không phải thời gian:** cùng action có thể cùng thời lượng hoạt ảnh nhưng
   cost khác nhau; restart, thử sai và thời gian suy nghĩ người chơi không nằm trong g.
7. **Hòa weighted cost chưa tối ưu tiêu chí phụ:** không cam kết ít F/ít bước hơn;
   muốn lexicographic objective là thay đổi chính sách/solver cần tác giả review.
8. **Tổng quát hóa hạn chế:** 10 campaign cố định và hai board minh họa chưa đại
   diện mọi bố cục; chưa có nghiên cứu người chơi hoặc bộ kiểm thử ngoài mẫu.
9. **Chọn weights để tạo chênh lệch BFS/UCS là nguy cơ thiên lệch:** cần báo cáo
   trước policy và chạy trên bộ cố định, không đổi màn chỉ để giữ một kết luận.
10. **Tài liệu còn cũ:** HEURISTICS.md vẫn ghi F5/S0,5 và mô hình chưa cập nhật
    đầy đủ split; comment test fragile vẫn nói “fragile 5” dù expected là 5=4+1.
    Code mới là cơ sở audit, không dùng các số cũ đó làm chứng minh cho main mới.

## 7. Khuyến nghị, chưa áp dụng thay đổi production

- Nếu nhóm muốn mô phỏng mục tiêu “ít lần bấm nhất”: dùng unit cost làm bảng
  đánh giá chính; weighted cost là thí nghiệm phụ. Nếu muốn tránh F/cost terrain,
  giữ weighted và trình bày rõ lựa chọn mô hình, không gọi là tối ưu gameplay.
- Có thể giữ 4/0,75 như **tham số thiết kế tạm thời được nhóm thống nhất**; chưa
  có bằng chứng để đổi lại 5/0,5 hay chọn bộ khác chỉ từ audit này.
- Trước nghiệm thu, chốt objective và weights, cập nhật tài liệu/manifest,
  benchmark cùng baseline và công bố độ nhạy. Giao tác giả sửa phần solver/
  heuristic nếu cần; lượt này không sửa chúng hoặc config production.
- Đề trang 3 mô tả tính hợp lệ F/cầu/switch, không nêu các số 4/0,75 trong bản
  trích đã đọc. Contract §9 yêu cầu dùng chung cost, có unit mode, rà soát và
  giải thích trước thực nghiệm; đây là nghĩa vụ nhóm cần hoàn thiện trong report.

## 8. Tái chạy và phạm vi thay đổi

```powershell
.venv\Scripts\python.exe -B -m examples.audit_cost_models --output docs/COST_AUDIT_EVIDENCE.json
.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_cost_policy_audit.py -v
.venv\Scripts\python.exe -B -m unittest discover -s tests -q
git diff --check
```

Python kiểm chứng: 3.13.13 trên Windows. `git diff --check` pass; liên kết tài
liệu và JSON evidence đã kiểm tra. Chưa đánh giá desktop/audio hoặc học trọng số.

Chỉ thêm script audit, test cost, evidence JSON và tài liệu; giữ nguyên production
TILE_COST/Problem/solver/heuristic sau pull. Không commit hoặc push. Hai tài liệu
nghiệm thu local cũ được bảo toàn.
