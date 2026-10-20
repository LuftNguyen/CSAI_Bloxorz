# Hướng dẫn đọc bố cục bản trích contract

`CSAI_Project.pdf` bắt đầu bằng **CONTRACT V1** và là contract triển khai nhóm
đã cung cấp. `CONTRACT.md` giữ nguyên văn bản trích; tệp này chỉ trình bày lại
những chỗ ngắt dòng/thụt dòng gây khó đọc, không đề xuất đổi quy ước.
Ký tự ngắt trang trong bản trích không thuộc tên trường hoặc đoạn mã Python.

Trong bảng §7, các từ `total_cos` + `t`, `unsolvab` + `le`, `node_lim` + `it`
phải đọc liền thành `total_cost`, `unsolvable`, `node_limit`; đối chiếu với
khai báo SearchStatus/SearchResult ngay trước bảng.

| Trường hợp | status | actions | total_cost |
| --- | --- | --- | --- |
| Có lời giải | solved | Chuỗi hành động | Tổng chi phí |
| Ban đầu đã thắng | solved | () | 0.0 |
| Duyệt hết không có lời giải | unsolvable | () | None |
| Hết thời gian | timeout | () | None |
| Đạt giới hạn node | node_limit | () | None |

Trong §10, `expanded_nod` + `es` là `expanded_nodes`; `generated_no` + `des`
là `generated_nodes`. Node mở rộng tính những lần thực sự sinh successor,
không tính node đích/mục lỗi thời. Node sinh tính successor hợp lệ trước lọc
trùng, không tính trạng thái đầu. Đơn vị peak memory là byte Python do
tracemalloc đo, không phải RSS.

Vòng gọi engine ở §6 bị lệch thụt dòng và ngắt trang giữa đoạn. Bố cục Python
hợp lệ tương ứng, giữ nguyên các thao tác và thứ tự:

```python
for action in problem.actions(state):
    child_state = problem.result(state, action)
    if child_state is None:
        continue
    step = problem.step_cost(state, action, child_state)
    # Xử lý frontier, trạng thái lặp và truy vết
```

Chữ ký solver và các dataclass trong §§6–7 có thể đối chiếu trực tiếp tại
`search/contracts.py` và các khung `search/{bfs,dfs,ucs,astar}.py`.
RunResult giữ ba trường trong §11, khai báo ở `runner.py`.
