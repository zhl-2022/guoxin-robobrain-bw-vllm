"""Verify or fetch the fixed thirteen evaluated model files before GPU startup."""
from pathlib import Path, PurePosixPath
import argparse
import json
import os
import sys
import time

from download_candidate_models_20261023 import download_file, OfficialRedirects
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = Path('/root/private_data/SothisAI/model/Aihub/RoboBrain2.5-8B-NV/main/RoboBrain2.5-8B-NV')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan-only', action='store_true')
    args = parser.parse_args()
    lock = json.loads((ROOT / 'publisher030/model-download-lock.json').read_text())
    assert lock['HF_revision'] == '7ae187cc62e45cfa1c5904903a8f017f11b2037b'
    assert len(lock['files']) == 13
    destination = Path(os.environ.get('ROBOBRAIN_MODEL_PATH', str(CANONICAL)))
    allowed = Path('/root/private_data/guoxin-candidates/models')
    assert destination.is_absolute() and '..' not in destination.parts
    assert destination == CANONICAL or (destination.is_relative_to(allowed)
        and destination != allowed and destination.relative_to(allowed).parts[0].startswith('robobrain-nv-'))
    for row in lock['files']:
        name = PurePosixPath(row['path'])
        assert len(name.parts) == 1 and not name.is_absolute() and name.name not in ('.', '..')
        assert row['url'] == ('https://modelscope.cn/models/BAAI/RoboBrain2.5-8B-NV/resolve/'
                             + row['modelscope_revision'] + '/' + row['path'])
    print(json.dumps({'destination': str(destination), 'files': len(lock['files']),
        'HF_revision': lock['HF_revision'], 'strategy': 'verify_existing_or_fetch_exact_fixed_official_files',
        'plan_only': args.plan_only, 'GPU_requests': 0, 'model_weights_in_image': False}), flush=True)
    if args.plan_only:
        return
    assert sys.platform == 'linux'
    for part in (destination, *destination.parents):
        assert not part.is_symlink(), 'Model destination contains a symlink'
    destination.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 6900
    opener = urllib.request.build_opener(OfficialRedirects())
    results = []
    for row in lock['files']:
        results.append(download_file(row, destination / row['path'], row['url'], deadline, opener))
    print(json.dumps({'complete': True, 'verified_files': len(results),
                      'statuses': [r['status'] for r in results], 'GPU_requests': 0}), flush=True)


if __name__ == '__main__':
    main()
