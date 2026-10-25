"""Reproduce level inventory and necessity evidence; writes only test docs."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from test_advanced_portfolio import RestrictedProblem, events, load, replay, solve
from gameModel.state import State
from levels.levelLoader import loadLevelFromJson


def describe(path):
    board, block = loadLevelFromJson(path, False)
    data = json.loads(path.read_text(encoding='utf-8'))
    specials = {ch: [[r, c] for r, row in enumerate(data['grid'])
                     for c, tile in enumerate(row) if tile == ch]
                for ch in 'wWTFB'}
    return State(board, block).copy(), {
        'file': path.relative_to(ROOT).as_posix(),
        'dimensions': [board.rows, board.cols], 'initial': list(block.key()[:4]),
        'orientation': block.orientation.name,
        'goal': next([r, c] for r, row in enumerate(data['grid'])
                     for c, tile in enumerate(row) if tile == 'G'),
        'special_tiles': specials,
    }


def record_result(result):
    return dict(status=result.status, expanded=result.expanded_nodes,
                actions=[a.name for a in result.actions], cost=result.total_cost)


def main():
    report = {'method': 'Existing registered A*, h=0, 10s/100000 expanded per query; not benchmark',
              'restrictions': 'bridge: remove effects on copied initial board; split/control/merge: remove event edges',
              'levels': [], 'fixtures': []}
    for number in range(1, 15):
        initial, record = describe(ROOT / f'levels/level{number}.json')
        _, full = solve(initial)
        record['full'] = record_result(full)
        record['restricted'] = {}
        if initial.board.switchEffects:
            record['restricted']['bridge'] = record_result(solve(initial, ('bridge',))[1])
        if initial.board.splitTargets:
            for event in ('split', 'control', 'merge'):
                record['restricted'][event] = record_result(solve(initial, (event,))[1])
        report['levels'].append(record)
        print(record['file'], full.status,
              {k: v['status'] for k, v in record['restricted'].items()}, flush=True)
    requirements = {'soft_gate': ['bridge'], 'heavy_gate': ['bridge'],
                    'split_control': ['split', 'control', 'merge'],
                    'split_gate': ['split', 'control', 'bridge', 'merge'],
                    'optional_gate': [], 'dead_gate': []}
    for name, required in requirements.items():
        initial, record = describe(ROOT / f'tests/fixtures/advanced/{name}.json')
        problem, full = solve(initial)
        record['full'] = record_result(full)
        record['required'] = required
        record['observed'] = sorted(replay(problem, full)[0]) if full.status == 'solved' else []
        record['restricted'] = {e: record_result(solve(initial, (e,))[1])
                                for e in required or ['bridge']}
        report['fixtures'].append(record)
    target = ROOT / 'docs/ADVANCED_LEVEL_EVIDENCE.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['# Kiểm kê màn chơi — 25/10/2026', '',
             'Kết quả chạy lại bằng `python -B tests/audit_advanced_portfolio.py`. '
             'Mỗi truy vấn dùng A* đăng ký hiện có, h=0; chỉ `unsolvable` sau cạn frontier '
             'mới là bằng chứng âm. Chi tiết tọa độ ô đặc biệt và đường đi nằm trong '
             '[ADVANCED_LEVEL_EVIDENCE.json](ADVANCED_LEVEL_EVIDENCE.json).', '',
             '| Màn | Kích thước | Start (đứng) → goal | Ô đặc biệt (số lượng) | Đầy đủ | Khi bỏ cơ chế |',
             '| --- | --- | --- | --- | --- | --- |']
    for rec in report['levels'] + report['fixtures']:
        special = ', '.join(f'{k}:{len(v)}' for k, v in rec['special_tiles'].items() if v) or 'không'
        restricted = ', '.join(f'{k}: {v["status"]}' for k, v in rec['restricted'].items()) or 'không áp dụng'
        lines.append(f'| {Path(rec["file"]).stem} | {rec["dimensions"]} | '
                     f'{rec["initial"][:2]} → {rec["goal"]} | {special} | '
                     f'{rec["full"]["status"]}, {len(rec["full"]["actions"])} bước | {restricted} |')
    lines += ['', 'Bỏ bridge nghĩa là bỏ toàn bộ effects công tắc trên bản sao, không xóa ô '
              'công tắc và không cấm đi qua nó. Đây là chứng minh phụ thuộc tác động cầu nói chung, '
              'không chứng minh từng công tắc riêng đều bắt buộc. Split và teleport là một '
              'chuyển tiếp nguyên tử; không thể tuyên bố đã kiểm tra độc lập hai cơ chế.', '',
              'Các màn cũ đều được giữ vì demo, GUI, witness/reset và quy trình tài liệu đang dùng. '
              'Các màn cùng có cơ chế không mặc nhiên tương đương về coverage. Chưa chứng minh '
              'tương đương trạng thái giữa các màn nên không xóa màn nào. Các màn cầu vẫn solved '
              'khi bỏ effects chỉ cung cấp coverage tùy chọn cho cơ chế đó.', '']
    (ROOT / 'docs/ADVANCED_LEVEL_INVENTORY.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
