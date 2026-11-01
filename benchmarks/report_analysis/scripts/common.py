"""Shared I/O and provenance; never changes historical or production files."""
from pathlib import Path
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[1]
sys.path.insert(0, str(ROOT))


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8').strip()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f'No rows for {path}')
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def provenance():
    paths = sorted(set([ROOT/'runner.py', ROOT/'levels/levelLoader.py'] +
                       list((ROOT/'gameModel').glob('*.py')) +
                       list((ROOT/'search').glob('*.py')) +
                       list((ROOT/'levels').glob('level[0-9]*.json')) +
                       list((BASE/'scripts').glob('*.py'))))
    packages = {d.metadata['Name']: d.version for d in metadata.distributions() if d.metadata['Name']}
    cpu = platform.processor()
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
            cpu = winreg.QueryValueEx(key, 'ProcessorNameString')[0].strip()
    except (ImportError, OSError):
        pass
    return {
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'git_revision': git('rev-parse', 'HEAD'), 'origin_main': git('rev-parse', 'origin/main'),
        'branch': git('branch', '--show-current'), 'git_status': git('status', '--porcelain'),
        'merge_head': git('rev-parse', '-q', '--verify', 'MERGE_HEAD') if (ROOT/'.git/MERGE_HEAD').exists() else None,
        'environment': {'platform': platform.platform(), 'cpu': cpu, 'logical_cpus': os.cpu_count(),
                        'python': sys.version, 'executable': sys.executable, 'packages': packages,
                        'PYTHONHASHSEED': os.environ.get('PYTHONHASHSEED', 'not fixed; ordered action/heap policy is deterministic')},
        'source_sha256_raw': {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in paths},
        'source_sha256_lf': {p.relative_to(ROOT).as_posix(): digest(p.read_bytes().replace(b'\r\n', b'\n')) for p in paths},
    }
