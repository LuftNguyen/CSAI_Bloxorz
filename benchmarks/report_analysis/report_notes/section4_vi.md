# Section 4 — Experimental Results and Self-Evaluation

Trạng thái: READY WITH CAVEATS. Đây là bản nháp học thuật dựa trên dữ liệu đã kiểm tra; đường dẫn dưới đây tương đối với `benchmarks/report_analysis/`. Không có thuật toán hoặc luật game nào được sửa để tạo kết quả. Các điều kiện giới hạn trong 4.5 phải đi cùng các bảng/biểu đồ khi sử dụng trong báo cáo.

## 4.1. Experimental Setup

Thực nghiệm chính tái sử dụng 350 runs: 10 level × 7 cấu hình × 5 repetitions. Dữ liệu nằm trong `main_comparison/raw/upstream_weighted/`. Môi trường gốc: macOS-26.5.1-arm64-arm-64bit-Mach-O, CPU được ghi là arm với 10 logical CPUs, Python 3.14.8. Metadata gốc không lưu tên CPU chi tiết và dependency freeze; không suy diễn chúng từ máy Windows hoặc requirements hiện tại. Revision ghi trong metadata là c7fac1a090177ebf47bfe339b49c69c2ef61b3d0, worktree dirty; toàn bộ source hash được đối chiếu với blob c4cc318 và source hiện tại sau chuẩn hóa CRLF/LF. Các file level cũng khớp hash. Chi tiết: `metadata/historical_validation.json`.

Thí nghiệm bổ sung dùng một cohort Windows độc lập: Windows-11-10.0.26300-SP0; CPU 13th Gen Intel(R) Core(TM) i7-13620H; Python 3.12.14 (main, Aug 25 2026, 14:01:42) [MSC v.1944 64 bit (AMD64)]. Revision, merge parent nếu có, raw/LF hashes, executable, toàn bộ package versions nằm trong `metadata/supplement_environment.json`. Không gộp time/memory Windows với macOS trong bất kỳ median nào.

Bảy cấu hình chính gồm BFS, DFS, UCS, A* Zero, A* Manhattan, A* Relaxed và A* Relaxed Split. Level 1–2 thuộc nhóm basic, 3–4 fragile, 5–7 bridge/switch, 8–10 split/merge. Đây là nhóm chức năng, không phải phân loại tuyệt đối: level 2 có 2 ô fragile. Đặc điểm từng màn: `main_comparison/summary/levels.csv`.

Cost chính thức trong factory GUI là weighted cost λ=0.25. Constructor `Problem(...)` mặc định unit cost, khác `make_problem(...)`; mọi phép đo mới truyền `unit_cost=False` và λ tường minh. Với mỗi action hợp lệ, c=1+λI_F, ngoại trừ SWITCH luôn có c=1. I_F được xác định bởi `Problem.step_cost` sau transition: footprint đích của khối đầy đủ; cube active khi trước/sau đều split; footprint kết quả khi teleport hoặc ghép. Không cộng phạt theo số ô fragile. Tổng C=N+λF, N gồm SWITCH. Luật chỉ cho cube/nằm được đỡ trên fragile; full-block đứng trên fragile là invalid.

Mọi solver có timeout 60 s và node limit 1,000,000. Benchmark gốc shuffle jobs tuần tự bằng `random.Random(20261030)`; không chạy song song tracemalloc. Mỗi run dùng Problem mới, không reuse bảng heuristic qua run. Survey mới có 140 tổ hợp, một observation/tổ hợp; case studies có 3 trials/tổ hợp, reuse trial 1 BFS/UCS của survey rồi chạy phần còn thiếu. Timing của survey chỉ có tính mô tả. Main historical được tái hiện các cấu hình duy nhất để kiểm tra N/C/expanded/generated/rolls và replay; việc này không thay thế hoặc làm mới các số đo thời gian lịch sử.

## 4.2. Evaluation Metrics

- Search time: thời gian `solve()` qua runner, bao gồm truy vết. Với Relaxed/Relaxed Split, bảng heuristic đã được precompute trước khoảng đo này. Với Zero/Manhattan không có pha precompute riêng; các cache nhỏ được khởi tạo trong solve.
- Precompute time: thời gian dựng bảng heuristic riêng cho Problem mới. Zero, Manhattan, BFS, DFS, UCS có giá trị 0 theo thiết kế benchmark.
- Total time: precompute + search, không gồm load level, replay, vẽ biểu đồ hoặc game animation. Đây là cold heuristic-table setup + search, không phải cold process startup. Median(total) không nhất thiết bằng median(precompute)+median(search).
- Search/precompute peak: hai peak Python allocations của hai phiên tracemalloc tách biệt, MB=10^6 bytes. Không cộng hoặc lấy max để gọi là peak tổng; không phải process RSS/RAM. Bộ nhớ bảng dựng trước không được tính đầy đủ trong search-phase peak.
- Expanded: số lần bắt đầu sinh successor, không gồm node đích và stale entries. Generated: successor hợp lệ trước duplicate filtering. Không đếm graph states dựng trong precompute vào expanded/generated của search.
- Solution length N: số search actions, bao gồm SWITCH. `roll_count` loại SWITCH, gồm cả bước di chuyển cube; không nên gọi toàn bộ là số lần lăn vật lý của khối đầy đủ.
- F: số action chịu penalty, đo bằng replay với `step_cost` thật và λ=1 để lấy chỉ báo nhị phân, kể cả khi run gốc có λ=0; không suy ra đơn thuần từ (C−N)/λ.
- Cost gap: C−C_UCS trên cùng level, λ và mode. UCS là baseline optimal cost dựa trên positive edge costs, best_g và minimum-g goal pop; A* được đối chiếu với baseline và các tests heuristic. BFS chỉ tối ưu N; DFS không bảo đảm N hoặc C tối ưu.
- Success rate: solved/trials; failure không được thay bằng 0. Bảng lịch sử tổng hợp median trong từng level/config rồi median giữa các level với trọng số level bằng nhau. N/C chỉ dùng solved runs; thời gian/node/memory trong code gốc dùng mọi run có số đo. Ở bộ hiện tại tất cả đều solved nên không phát sinh sai khác do lọc failure.

## 4.3. Experimental Results

### 4.3.1. Main Algorithm Comparison

350/350 historical runs solved và ghi replay verified. Các kết quả cấu trúc của 70 level/config được đối chiếu lại trực tiếp với source hiện tại; 350/350 dòng khớp. Đây là tái hiện lời giải deterministic, không chứng minh chuỗi actions gốc vì CSV gốc không lưu chuỗi đó. Dữ liệu đối chứng unit cost 350 runs và sweep cũ 360 runs được audit riêng; không đưa vào median chính.

| Cấu hình | Search (s) | Precompute (s) | Total (s) | Search peak (MB) | Expanded | Generated | Actions | Cost | Success |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BFS | 0.112311 | 0 | 0.112311 | 2.40041 | 282 | 780.5 | 19.5 | 19.5 | 1.0 |
| DFS | 0.0988217 | 0 | 0.0988217 | 2.77508 | 191.5 | 609.5 | 141.5 | 142.125 | 1.0 |
| UCS | 0.138815 | 0 | 0.138815 | 2.41489 | 282.5 | 781 | 19.5 | 19.5 | 1.0 |
| A* Zero | 0.139601 | 0 | 0.139601 | 2.41676 | 282.5 | 781 | 19.5 | 19.5 | 1.0 |
| A* Manhattan | 0.0907884 | 0 | 0.0907884 | 1.83576 | 170.5 | 484.5 | 19.5 | 19.5 | 1.0 |
| A* Relaxed | 0.0297312 | 0.00253471 | 0.0334001 | 0.610288 | 56.5 | 156.5 | 19.5 | 19.5 | 1.0 |
| A* Relaxed Split | 0.020927 | 0.00467462 | 0.0353721 | 0.474528 | 29.5 | 102 | 19.5 | 19.5 | 1.0 |

Nguồn: `main_comparison/summary/overall.csv`. Mỗi ô là median của per-level medians, không phải kết quả của một level điển hình; median N/C bằng nhau có thể che khác biệt level 2. Peak ở bảng chỉ là search-phase traced peak.

Actions / cost theo màn:

| Level | BFS | DFS | UCS | A* Zero | A* Manhattan | A* Relaxed | A* Relaxed Split |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 10 / 10 | 99 / 99 | 10 / 10 | 10 / 10 | 10 / 10 | 10 / 10 | 10 / 10 |
| 2 | 13 / 13.25 | 169 / 170.5 | 13 / 13 | 13 / 13 | 13 / 13 | 13 / 13 | 13 / 13 |
| 3 | 13 / 13.25 | 87 / 89 | 13 / 13.25 | 13 / 13.25 | 13 / 13.25 | 13 / 13.25 | 13 / 13.25 |
| 4 | 23 / 24 | 100 / 101.75 | 23 / 24 | 23 / 24 | 23 / 24 | 23 / 24 | 23 / 24 |
| 5 | 16 / 16 | 122 / 122 | 16 / 16 | 16 / 16 | 16 / 16 | 16 / 16 | 16 / 16 |
| 6 | 20 / 20 | 187 / 187 | 20 / 20 | 20 / 20 | 20 / 20 | 20 / 20 | 20 / 20 |
| 7 | 25 / 25 | 130 / 130 | 25 / 25 | 25 / 25 | 25 / 25 | 25 / 25 | 25 / 25 |
| 8 | 20 / 21.25 | 153 / 154.25 | 20 / 21.25 | 20 / 21.25 | 20 / 21.25 | 20 / 21.25 | 20 / 21.25 |
| 9 | 19 / 19 | 207 / 207 | 19 / 19 | 19 / 19 | 19 / 19 | 19 / 19 | 19 / 19 |
| 10 | 26 / 26.25 | 446 / 450.75 | 26 / 26.25 | 26 / 26.25 | 26 / 26.25 | 26 / 26.25 | 26 / 26.25 |

Nguồn chi tiết tất cả time/memory/nodes/cost/success/gap: `main_comparison/summary/per_level.csv`. Biểu đồ: `main_comparison/charts/time.png`, `memory.png`, `expanded_nodes.png`, `generated_nodes.png`, `solution_length.png`, `total_cost.png`. Tất cả đều có DFS, cùng 7 cấu hình, cùng macOS cohort.

Bảng optimality so với UCS (cùng level và cost model):

| config | levels_matching_ucs_cost | maximum_absolute_cost_gap | median_relative_cost_gap |
| --- | --- | --- | --- |
| bfs | 9 | 0.25 | 0 |
| dfs | 0 | 424.5 | 7.4875 |
| ucs | 10 | 0 | 0 |
| astar_zero | 10 | 0 | 0 |
| astar_manhattan | 10 | 0 | 0 |
| astar_relaxed | 10 | 0 | 0 |
| astar_relaxed_split | 10 | 0 | 0 |

Nguồn: `main_comparison/summary/optimality.csv`. Đây là đánh giá lời giải của implementation trên bộ màn, không phải bảo đảm lý thuyết cho BFS/DFS ở weighted cost.

BFS và UCS có cùng N trên cả 10 màn ở λ=0.25, nhưng level 2 có C_BFS=13.25 và C_UCS=13. BFS chọn đường ngắn theo FIFO mà không xếp hàng theo chi phí. UCS tối ưu weighted cost; ở các màn còn lại cost bằng BFS trong cấu hình mặc định. Unit-cost đối chứng cho BFS/UCS cùng N và C trên toàn bộ 10 màn.

DFS có median N=141.5, cost=142.125, lớn hơn rõ rệt baseline. Tuy nhiên DFS nhanh hơn BFS trên các level [2, 4, 5, 6, 8, 9, 10], và search-phase traced peak thấp hơn BFS trên các level [8, 9, 10]; không suy diễn rằng DFS luôn nhanh hơn hoặc luôn ít bộ nhớ. Ở level 10, DFS dùng 446 actions, cost 450.75, so với UCS 26 actions, cost 26.25. DFS giữ visited và stack các node/parent, nên không mang bảo đảm bộ nhớ O(depth) của tree-DFS không lưu lịch sử. Tính ưu/nhược được xác định theo implementation và thứ tự actions thực tế.

Ví dụ trade-off ở level 8: DFS có time=0.098871s, search peak=2.833272MB, expanded/generated=161/588, N/C=153/154.25. BFS có time=0.709023s, peak=10.844352MB, expanded/generated=1216/4587, N/C=20/21.25. Lợi ích tài nguyên của DFS ở màn này đi cùng lời giải dài và đắt hơn nhiều. Ngược lại, level 2 DFS peak=2.924024MB lớn hơn BFS=2.559968MB.

UCS và A* Zero có cost/expanded/generated tương ứng bằng nhau trong benchmark chính. Heap, best_g và tính step_cost tạo overhead so với BFS khi không đem lại lợi ích về chất lượng lời giải. A* có heuristic giảm công sức tìm kiếm ở nhiều màn nhưng phải tính cả preprocessing; không mặc định A* luôn thắng UCS về time hoặc nodes.

### 4.3.2. Cost Sensitivity Analysis

Khảo sát trực tiếp 10 × 7 × 2 = 140 tổ hợp BFS/UCS ở λ=[0,0.25,0.5,1,1.5,2,3], weighted mode tường minh. Mỗi raw JSONL chứa actions, trace từng bước, F đo lại, N, C, search/precompute/total time, hai peak tách biệt, expanded/generated/status và metadata liên kết. Toàn bộ 140 solutions được replay lại từ disk; λ=0 vẫn đo F, và C=N. Không dùng kết quả UCS tại λ khác để giả lập BFS.

Theo cost trên lưới khảo sát, các level bị ảnh hưởng: [2, 3, 4, 8, 10]; không đổi cost: [1, 5, 6, 7, 9]. Các trường hợp không đổi được giữ đầy đủ trong bảng/biểu đồ, không loại bỏ vì kém nổi bật.

| level | bfs_F | ucs_N_by_lambda | ucs_F_by_lambda | ucs_sequence_changes | gap_lambdas |
| --- | --- | --- | --- | --- | --- |
| 1 | 0 | [10, 10, 10, 10, 10, 10, 10] | [0, 0, 0, 0, 0, 0, 0] | False | [] |
| 2 | 1 | [13, 13, 13, 13, 13, 13, 13] | [1, 0, 0, 0, 0, 0, 0] | True | [0.25, 0.5, 1.0, 1.5, 2.0, 3.0] |
| 3 | 1 | [13, 13, 13, 13, 13, 13, 13] | [1, 1, 1, 1, 1, 1, 1] | False | [] |
| 4 | 4 | [23, 23, 23, 23, 24, 24, 26] | [4, 4, 4, 4, 3, 3, 2] | True | [1.5, 2.0, 3.0] |
| 5 | 0 | [16, 16, 16, 16, 16, 16, 16] | [0, 0, 0, 0, 0, 0, 0] | False | [] |
| 6 | 0 | [20, 20, 20, 20, 20, 20, 20] | [0, 0, 0, 0, 0, 0, 0] | False | [] |
| 7 | 0 | [25, 25, 25, 25, 25, 25, 25] | [0, 0, 0, 0, 0, 0, 0] | False | [] |
| 8 | 5 | [20, 20, 20, 20, 20, 20, 20] | [5, 5, 5, 5, 5, 5, 5] | False | [] |
| 9 | 0 | [19, 19, 19, 19, 19, 19, 19] | [0, 0, 0, 0, 0, 0, 0] | False | [] |
| 10 | 1 | [26, 26, 26, 26, 26, 26, 26] | [1, 1, 1, 1, 1, 1, 1] | False | [] |

Nguồn: `cost_sensitivity/summary/survey.csv`, `level_changes.csv`; chuỗi N/F theo đúng thứ tự λ nêu trên. `transition_brackets.csv` phân biệt đổi action sequence với đổi N/F. Nếu cùng N,F thì mọi λ cho hai đường cùng cost; sequence change trong trường hợp đó không chứng minh một optimum mới. Bằng chứng ties được lưu bằng action hash và chuỗi actions thực tế.

Case studies được chọn sau survey: bắt buộc level 2,4 và mọi level có thay đổi N/F của UCS. Các bảng sau là kết quả chạy trực tiếp, 3 trials/cấu hình; mọi A* Relaxed/Relaxed Split trong cases khớp cost UCS.

| Level | λ | Solver | N | F | C |
| --- | --- | --- | --- | --- | --- |
| 2 | 0.25 | A* Relaxed | 13 | 0 | 13 |
| 2 | 0.25 | A* Relaxed Split | 13 | 0 | 13 |
| 2 | 0.25 | BFS | 13 | 1 | 13.25 |
| 2 | 0.25 | UCS | 13 | 0 | 13 |
| 2 | 3 | A* Relaxed | 13 | 0 | 13 |
| 2 | 3 | A* Relaxed Split | 13 | 0 | 13 |
| 2 | 3 | BFS | 13 | 1 | 16 |
| 2 | 3 | UCS | 13 | 0 | 13 |
| 4 | 0.25 | A* Relaxed | 23 | 4 | 24 |
| 4 | 0.25 | A* Relaxed Split | 23 | 4 | 24 |
| 4 | 0.25 | BFS | 23 | 4 | 24 |
| 4 | 0.25 | UCS | 23 | 4 | 24 |
| 4 | 1 | A* Relaxed | 23 | 4 | 27 |
| 4 | 1 | A* Relaxed Split | 23 | 4 | 27 |
| 4 | 1 | BFS | 23 | 4 | 27 |
| 4 | 1 | UCS | 23 | 4 | 27 |
| 4 | 1.5 | A* Relaxed | 24 | 3 | 28.5 |
| 4 | 1.5 | A* Relaxed Split | 24 | 3 | 28.5 |
| 4 | 1.5 | BFS | 23 | 4 | 29 |
| 4 | 1.5 | UCS | 24 | 3 | 28.5 |
| 4 | 2 | A* Relaxed | 24 | 3 | 30 |
| 4 | 2 | A* Relaxed Split | 24 | 3 | 30 |
| 4 | 2 | BFS | 23 | 4 | 31 |
| 4 | 2 | UCS | 24 | 3 | 30 |
| 4 | 3 | A* Relaxed | 26 | 2 | 32 |
| 4 | 3 | A* Relaxed Split | 26 | 2 | 32 |
| 4 | 3 | BFS | 23 | 4 | 35 |
| 4 | 3 | UCS | 26 | 2 | 32 |

Nguồn: `cost_sensitivity/summary/case_comparison.csv`; raw và step traces ở `cost_sensitivity/raw/*.jsonl`. Đường đi cụ thể không được rút gọn hoặc đổi action khi lập bảng.

Level 2 minh họa cùng số bước nhưng khác cost ở λ=0.25. Level 4 kiểm tra trực tiếp λ=3: so sánh BFS/UCS/A* trong bảng, không suy ra BFS từ dữ liệu UCS cũ. Với hai đường đã biết (N,F)=(23,4) và (26,2), các đường thẳng 23+4λ và 26+2λ cắt tại λ=1.5; điểm giao hai ứng viên chưa phải chứng minh threshold optimal toàn cục. Dữ liệu lưới ở 1,1.5,2,3 chỉ xác lập các lựa chọn observed và bracket thay đổi; tại điểm tie một solver có thể chọn bất kỳ lời giải tối ưu nào.

Phát hiện quan trọng: tại λ=1.5 có phương án thứ ba (N,F)=(24,3), cost=28.5, thấp hơn cost=29 của cả hai ứng viên cũ. Tại λ=2, UCS chọn (24,3), cost=30; (26,2) cũng cost=30, và chuỗi 26 actions đã replay hợp lệ ở λ=3 có thể được đánh giá lại bằng cùng step_cost tại λ=2. Vì vậy cùng optimal cost không bắt buộc cùng N/F. Các bracket quan sát cho UCS là [1,1.5] và [2,3], không phải khẳng định threshold chính xác. Level 2 tại λ=0 cũng có hai đường 13 actions (F=1 và F=0) cùng cost=13; khi λ>0, đường F=0 được ưu tiên. Nguồn trực tiếp: raw survey/cases và `transition_brackets.csv`.

Các biểu đồ phủ đủ 10 màn: `cost_sensitivity/charts/total_cost.png`, `solution_length.png`, `fragile_penalty_count.png`, `expanded_nodes.png`, `change_heatmap.png`. Hình case study: `cost_sensitivity/case_studies/level*.png`. Chi phí Windows không trộn với timing macOS; đối chiếu cấu trúc chỉ thực hiện sau xác nhận source/game levels tương thích.

### 4.3.3. Heuristic Performance

Nguồn: `heuristic_comparison/summary/per_level.csv`, `overall.csv`, `group_comparison.csv`. Biểu đồ `heuristic_comparison/charts/time.png` phân biệt search và total; `expanded_nodes.png` và `group_comparison.png` mô tả công sức và trade-off preprocessing.

`heuristic_comparison/summary/per_level_winners.csv` liệt kê cấu hình đạt min expanded/search/total ở từng màn (giữ cả tie). Dữ liệu expanded cũng cho thấy A* Manhattan mở 1759 node ở level 9, nhiều hơn UCS 1646; không chỉ riêng Relaxed có trường hợp bất lợi.

Ở median tổng hợp, Relaxed Split có expanded=29.5 và search time=0.020927s; Relaxed có expanded=56.5, search time=0.029731s. Tuy nhiên total median của Relaxed=0.033400s nhỏ hơn Relaxed Split=0.035372s. Không chọn heuristic thắng mọi trường hợp từ một median tổng hợp.

A* Relaxed mở nhiều node hơn UCS ở các level [9]. Tại level 9: Relaxed expanded=1737, UCS=1646, Relaxed Split=30. Relaxed trả h=0 khi split, và coi các split switches là đích trung gian cho pha full-block nên cận dưới yếu trên nhóm này. Việc A* mở nhiều node hơn UCS vẫn có thể xảy ra với heuristic admissible do thứ tự f/tie và vùng f bằng optimal cost; dữ liệu hiện tại không tách nhân quả của từng yếu tố. Không kết luận đó là heuristic sai chỉ dựa trên số node.

| group | config | levels | median_expanded_nodes | median_search_time_s | median_total_time_s | median_precompute_time_s |
| --- | --- | --- | --- | --- | --- | --- |
| basic | astar_relaxed | [1, 2] | 20 | 0.0101606 | 0.0132918 | 0.00310431 |
| basic | astar_relaxed_split | [1, 2] | 20 | 0.0101478 | 0.0150951 | 0.00496646 |
| fragile | astar_relaxed | [3, 4] | 21 | 0.0106337 | 0.0130408 | 0.00235744 |
| fragile | astar_relaxed_split | [3, 4] | 21 | 0.0106547 | 0.0143738 | 0.00359285 |
| bridge_switch | astar_relaxed | [5, 6, 7] | 84 | 0.043744 | 0.0468352 | 0.00298442 |
| bridge_switch | astar_relaxed_split | [5, 6, 7] | 84 | 0.0436489 | 0.0484125 | 0.00441792 |
| split | astar_relaxed | [8, 9, 10] | 1737 | 1.55437 | 1.55673 | 0.00249846 |
| split | astar_relaxed_split | [8, 9, 10] | 35 | 0.0315134 | 0.0827529 | 0.0511986 |

Relaxed Split mô hình hóa cả hai cube, active cube, SWITCH, teleport và merge trong bài toán nới lỏng cầu/công tắc. Bảng được dựng bằng tìm kiếm đồ thị và Dijkstra ngược; lookup nhanh nhưng chi phí dựng bảng không nằm trong expanded/generated của search. Phân tích cần nhìn cả preprocessing và search. Toàn bộ A* trong benchmark chính và cases bổ sung có C khớp UCS; điều này hỗ trợ optimality trên các instances đã kiểm tra, không chứng minh cho mọi Bloxorz hoặc mọi λ.

## 4.4. Discussion and Self-Evaluation

BFS là baseline ngắn nhất theo số search actions, dễ diễn giải; weighted-cost counterexample ở level 2 cho thấy ngắn nhất không đồng nghĩa rẻ nhất. DFS có thể sớm gặp một đích theo thứ tự duyệt, giảm thời gian ở một số màn, nhưng chất lượng lời giải thấp hơn nhiều; không phù hợp khi ưu tiên N hoặc C tối ưu. UCS có ý nghĩa khi penalty tạo sự khác nhau giữa đường đi; level 4 tại λ lớn cho thấy việc chấp nhận nhiều actions hơn có thể hợp lý theo mục tiêu cost. Trên các level F=0 hoặc không có lựa chọn thay thế tốt hơn, weighted cost không đem lại khác biệt chất lượng giữa BFS/UCS và overhead UCS vẫn tồn tại.

A* Zero cung cấp đối chứng với UCS; Manhattan là cận rẻ nhưng yếu; Relaxed và Relaxed Split dùng thêm cấu trúc game để giảm search. Relaxed thông thường yếu ở trạng thái split nên không luôn cải thiện UCS; Relaxed Split giúp nhóm split nhưng tốn nhiều preprocessing hơn. Nhóm basic/fragile nhỏ không mặc nhiên hưởng lợi từ bảng phức tạp hơn. Dữ liệu không hỗ trợ tuyên bố một thuật toán/heuristic vượt trội trên mọi metric.

Các kiểm tra thực hiện: 208 unit/integration tests PASS, không FAIL/ERROR; gồm campaign, rules, UCS/A*, heuristic admissibility/consistency trên trạng thái campaign ở unit/default weighted mode, lambda comparison, GUI headless tests. Không chạy GUI thủ công. Tất cả direct solutions mới được replay lại từ JSONL và kiểm tra N+λF bằng step_cost; summary lịch sử được tính lại từ raw; figure inputs/hash có trong `metadata/chart_manifest.json`. Tests lambda không phải bằng chứng exhaustive consistency cho mọi λ.

## 4.5. Limitations và hướng cải tiến

1. Chỉ có 10 màn campaign do nhóm thiết kế, không đại diện mọi Bloxorz. Nhóm level phản ánh tính năng, không phải độ khó đã chuẩn hóa.
2. Historical chính có 5 repetitions; case studies 3; survey chỉ 1, nên không diễn giải timing survey như ước lượng ổn định. Không kiểm định thống kê hoặc tuyên bố significance từ median.
3. Timing có nhiễu và overhead tracemalloc; peak chỉ là traced Python allocations, không phải toàn RAM. Hai pha memory không cho phép khôi phục combined peak từ CSV hiện tại.
4. Precompute nằm ngoài solver timeout/node limit; tổng thời gian có thể vượt 60s dù search chưa timeout. Các trường hợp gần deadline có khác biệt: BFS/UCS không check ngay sau mỗi engine call, DFS/A* có check ở vị trí khác; DFS trả unsolvable sau khi stack cạn mà không có final timeout check. Không sửa core code trong công việc này. Tất cả run dùng để phân tích solved, không chạm timeout/node limit, nên giới hạn này không làm thay đổi kết quả campaign đã lưu. Không suy rộng success rate hiện tại thành khả năng xử lý mọi timeout.

   Chẩn đoán riêng `metadata/deadline_diagnostic.json` dùng clock giả: result() trả goal và tăng clock từ 0 lên 2 giây với budget 1 giây; BFS/UCS trả solved, DFS/A* trả timeout. Đây là khác biệt policy tái hiện trực tiếp, không phải một run campaign và không được đưa vào thống kê success. Cần task core riêng nếu nhóm muốn thống nhất semantics; không tự sửa trong thí nghiệm này.
5. Metadata historical thiếu CPU model chi tiết/dependency freeze và raw actions; không thể khôi phục tuyệt đối môi trường cũ. Source hash, level hash và structural reproduction giúp kiểm tra tính phù hợp; các thiếu sót vẫn được nêu rõ.
6. Có nhiều lời giải cùng optimal cost; đổi action sequence không nhất thiết đổi N/F hay ngưỡng optimum. Không tuyên bố λ=1.5 là threshold toàn cục chỉ từ hai ứng viên và lưới rời rạc.
7. Constructor/factory cost defaults khác nhau dễ gây nhầm. Thực nghiệm dùng explicit mode/λ, không thay API của nhóm.
8. Tài liệu heuristic gốc còn trỏ script sweep đã xóa; script và CSV cũ được bảo tồn trong `metadata/preservation/preintegration_evidence.zip` cùng manifest hash. Không đưa dữ liệu cũ chưa có provenance đầy đủ vào thống kê time chính.

Hướng cải tiến có cơ sở: thống nhất deadline policy bằng task core riêng có review; nếu cần so tổng memory thì đo một traced session bao quanh cả precompute+search hoặc process RSS bằng protocol mới, giữ cohort tách biệt; mở rộng bộ màn độc lập và số repetitions nếu cần suy luận tổng quát. Không cần sửa thuật toán/cost để các kết quả hiện tại thể hiện khác biệt.
