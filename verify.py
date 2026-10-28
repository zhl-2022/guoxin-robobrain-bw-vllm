#!/usr/bin/env python3
"""Complete pinned RefSpatial200 evaluation from the repository root.

This replaces the unconfigured legacy generic official-evaluator delegate.
The published grader, RGB requests, decoding and coordinate policy are the
unchanged evaluator used for the original full200 result.
"""
import argparse
import os
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from prepare_refspatial_data025 import prepare


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--data', '--data-dir', type=Path)
    parser.add_argument('--sources', type=Path, default=ROOT / 'publisher025/author-sources')
    args, rest = parser.parse_known_args()
    data = args.data if args.data is not None else prepare()
    worker = ROOT / 'scripts/submission013/evaluate_refspatial017.py'
    model = os.environ.get('ROBOBRAIN_SERVED_NAME', os.environ.get('ROBOBRAIN_MODEL_PATH',
        '/root/private_data/SothisAI/model/Aihub/RoboBrain2.5-8B-NV/main/RoboBrain2.5-8B-NV'))
    if '--model' not in rest and not any(value.startswith('--model=') for value in rest):
        rest += ['--model', model]
    sys.argv = [str(worker), '--data', str(data), '--sources', str(args.sources), *rest]
    runpy.run_path(str(worker), run_name='__main__')


if __name__ == '__main__':
    main()
