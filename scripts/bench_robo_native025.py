"""Expose the unchanged native six-load/two-round benchmark from bench.sh."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / 'scripts/t02_sglang_bench.py'
RUNTIME = ROOT / 'tasks/robobrain-bw-vllm/runtime'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', action='store_true', help='Print the complete608-request plan; no model calls')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--client-python', type=Path)
    args = parser.parse_args()
    assert hashlib.sha256(WRAPPER.read_bytes()).hexdigest() == 'ff8eef852e19f336e99884cc031353627ca304c6a7534c22375116758a850000'
    client = args.client_python
    if client is None:
        configured = os.environ.get('ROBOBRAIN_CLIENT_PYTHON')
        client = Path(configured) if configured else Path('/root/private_data/sglang-client-004c/bin/python')
        if not args.plan and not configured and not client.is_file():
            client = Path('/opt/guoxin/robo-client025/bin/python')
    output = args.output or ROOT / 'bench' / ('native-' + uuid.uuid4().hex)
    model = os.environ.get('MODEL_PATH', '/root/private_data/SothisAI/model/Aihub/RoboBrain2.5-8B-NV/main/RoboBrain2.5-8B-NV')
    served = os.environ.get('SERVED_NAME', model)
    command = [sys.executable, str(WRAPPER), '--client-python', str(client),
               '--allow-client-device-discovery', '--model-path', model, '--served-model-name', served,
               '--port', os.environ.get('PORT', '30001'), '--output-dir', str(output),
               '--timeout-seconds', '9000', '--total-timeout-seconds', '24000']
    if not args.plan:
        state = json.loads((RUNTIME / 'state.json').read_text())
        assert state['status'] == 'ready', 'Run the owned root service before benchmarking'
        run_id = state['run_id']
        assert len(run_id) == 32 and all(value in '0123456789abcdef' for value in run_id)
        command += ['--run', '--runtime-dir', str(RUNTIME), '--expected-run-id', run_id]
    raise SystemExit(subprocess.run(command, stdin=subprocess.DEVNULL).returncode)


if __name__ == '__main__':
    main()
