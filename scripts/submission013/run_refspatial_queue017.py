"""Wait for both owned Kimi controllers, then evaluate complete RefSpatial200.

Never shuts down the Notebook or stops another service. Preserve failed scores.
Run the native six-load/two-round matrix only if the selected full accuracy passes.
"""
from pathlib import Path
import datetime as dt
import hashlib
import json
import os
import resource
import shutil
import socket
import subprocess
import sys
import time
import uuid
import zipfile


STAGE = Path('/root/private_data/guoxin-session017/refspatial-stage001')
OUT = Path('/root/private_data/guoxin-session017/robo-refspatial001')
PRIOR = Path('/root/private_data/guoxin-session016/kimi-performance005')
REPLAY = Path('/root/private_data/guoxin-session017/kimi-portable-replay001')
COMMIT = 'a1304dad3fe762691735c7fe03beffb8efcffd21'


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def save(record):
    path = OUT / 'progress.json'
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def owned_alive(pid, script):
    try:
        root = Path('/proc') / str(pid)
        return root.joinpath('stat').read_text().rsplit(')', 1)[1].split()[0] != 'Z' and script.encode() in root.joinpath('cmdline').read_bytes()
    except (FileNotFoundError, ProcessLookupError):
        return False


def checked_extract(archive, target):
    target.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert len(bundle.namelist()) == len(set(bundle.namelist()))
        for item in bundle.infolist():
            path = Path(item.filename)
            destination = target / path
            assert not path.is_absolute() and destination.resolve().is_relative_to(target.resolve())
            assert not item.is_dir() or item.file_size == 0
            assert item.external_attr >> 28 != 10, 'Refuse symbolic links'
            if item.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open('xb') as stream:
                    stream.write(bundle.read(item))


def main():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    assert Path('/dev/kfd').exists()
    assert json.loads((STAGE / 'IMPORT-READY.json').read_text())['ready']
    lock = json.loads((STAGE / 'project-lock.json').read_text())
    assert lock['git_commit'] == COMMIT and sha(STAGE / 'robo-project.zip') == lock['sha256']
    OUT.mkdir(parents=True, exist_ok=False)
    record = {'started_utc': now(), 'controller_pid': os.getpid(), 'state': 'cpu_stage',
              'source_sha256': sha(__file__), 'project_git_commit': COMMIT,
              'project_zip_sha256': lock['sha256'], 'full_sample_count': 200,
              'GPU_started': False, 'phases': {}, 'submitted': False,
              'instance_shutdown_requested': False, 'prior_kimi_controllers': [38105, 43060]}
    save(record)
    shutil.copyfile(__file__, OUT / 'executed-controller.py')
    project = OUT / 'project'
    checked_extract(STAGE / 'robo-project.zip', project)
    task = project / 'tasks/robobrain-bw-vllm'
    data = STAGE / 'data'
    sources = STAGE / 'sources'
    worker = STAGE / 'tools/evaluate_refspatial017.py'
    env = os.environ.copy()
    env.update(ROBOBRAIN_PYTHON_BIN='/usr/bin/python3', ROBOBRAIN_MAX_RUNTIME_SECONDS='43200',
               ROBOBRAIN_LOAD_TIMEOUT='1800', ROBOBRAIN_MAX_NUM_SEQS='4',
               PYTHONPATH=str(project / 'scripts'), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
               ROCM_PATH='/opt/dtk', HIP_PATH='/opt/dtk/hip')
    env['PATH'] = '/opt/ucx/bin:/opt/dtk/bin:/opt/dtk/llvm/bin:/opt/dtk/hip/bin:/opt/hyhal/bin:' + env.get('PATH', '/usr/bin:/bin')
    env['LD_LIBRARY_PATH'] = ':'.join(['/opt/ucx/lib', '/opt/dtk/dcc/gcvm/lib', '/opt/dtk/hip/lib',
        '/opt/dtk/llvm/lib', '/opt/dtk/lib', '/opt/dtk/lib64', '/opt/hyhal/lib', '/opt/hyhal/lib64',
        '/opt/dtk/dushmem/lib', '/opt/dtk/opencl/lib', '/opt/mpi/lib', '/opt/hwloc/lib', env.get('LD_LIBRARY_PATH', '')])

    def step(argv, label, timeout):
        with (OUT / (label + '.log')).open('xb') as log:
            child = subprocess.Popen(argv, cwd=project, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                value = child.wait(timeout=timeout)
            except BaseException:
                child.terminate()
                try:
                    child.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
                raise
        record['phases'][label] = value
        save(record)
        return value

    assert step(['python3', str(worker), '--data', str(data), '--sources', str(sources), '--selfcheck'], 'cpu-selfcheck', 180) == 0
    record['state'] = 'waiting_owned_kimi_performance_and_replay'
    save(record)
    deadline = time.monotonic() + 43200
    while True:
        parent_alive = owned_alive(38105, '/root/run_kimi_performance016e.py')
        replay_alive = owned_alive(43060, '/root/finalize_kimi_replay017.py')
        if not parent_alive and not replay_alive and (PRIOR / 'run-final.json').is_file() and (REPLAY / 'progress.json').is_file():
            prior = json.loads((PRIOR / 'run-final.json').read_text())
            replay = json.loads((REPLAY / 'progress.json').read_text())
            assert prior['owned_service_stopped'], 'Kimi performance did not finish cleanup'
            assert replay['state'] in ('complete', 'failed', 'replay_or_cleanup_failed'), 'Kimi replay is still queued'
            record.update(prior_kimi_performance_complete=prior.get('complete'), prior_kimi_replay_state=replay['state'],
                          prior_kimi_final_sha256=sha(PRIOR / 'run-final.json'), prior_kimi_replay_progress_sha256=sha(REPLAY / 'progress.json'))
            break
        assert time.monotonic() < deadline, 'Existing Kimi work still active; left untouched'
        time.sleep(20)
    for port in (30000, 30001, 30002, 30109, 30119, 30129, 30139):
        with socket.socket() as sock:
            assert sock.connect_ex(('127.0.0.1', port)) != 0, ('Existing service left untouched', port)
    preflight = json.loads((project / 'evidence/robobrain-preflight-hashed-001.json').read_text())
    model = Path(preflight['model_path'])
    assert model.is_dir()
    identities = preflight['model_checks']['shards'] + preflight['files']
    for row in identities:
        assert sha(model / row['name']) == row['sha256'], ('Model file identity changed', row['name'])
    record['model_files_hashed'] = len(identities)
    env.update(ROBOBRAIN_MODEL_PATH=str(model), ROBOBRAIN_SERVED_NAME=str(model))
    run_id = uuid.uuid4().hex
    record.update(state='root_entry_full_refspatial', run_id=run_id, GPU_started=True)
    save(record)
    launched = False
    try:
        launched = True
        assert step(['bash', str(project / 'run.sh'), '--run-id', run_id], 'launch', 2100) == 0
        assert step(['bash', str(project / 'env_check.sh')], 'environment', 180) == 0
        assert step(['bash', str(project / 'smoke.sh')], 'smoke', 900) == 0
        assert step(['python3', str(worker), '--data', str(data), '--sources', str(sources), '--model', str(model),
                     '--output', str(OUT / 'evaluation')], 'full-accuracy', 5400) == 0
        accuracy = json.loads((OUT / 'evaluation/verify_result.json').read_text())
        record['accuracy_result'] = accuracy
        if accuracy['numeric_pass']:
            record['state'] = 'native_performance_matrix'
            save(record)
            wrapper = STAGE / 'tools/t02_sglang_bench.py'
            assert sha(wrapper) == 'ff8eef852e19f336e99884cc031353627ca304c6a7534c22375116758a850000'
            step(['python3', str(wrapper), '--run', '--client-python', '/root/private_data/sglang-client-004c/bin/python',
                  '--allow-client-device-discovery', '--model-path', str(model), '--served-model-name', str(model),
                  '--port', '30001', '--runtime-dir', str(task / 'runtime'), '--expected-run-id', run_id,
                  '--output-dir', str(OUT / 'performance'), '--timeout-seconds', '5400', '--total-timeout-seconds', '24000'],
                 'native-benchmark', 24100)
            assert step(['python3', str(STAGE / 'tools/analyze_sglang_results_004.py'), '--run', str(OUT / 'performance/run.json'),
                         '--analysis-dir', str(OUT / 'performance-analysis')], 'performance-audit', 180) in (0, 1)
            proof = json.loads((OUT / 'performance-analysis/analysis.json').read_text())
            record['complete_native_matrix_verified'] = proof['summary']['full_two_round_matrix_complete']
            record['eligible_client_reported_requests'] = proof['summary']['eligible_client_reported_requests']
    except BaseException as exc:
        record['error'] = repr(exc)
    finally:
        if launched:
            try:
                step(['bash', str(project / 'stop.sh'), '--run-id', run_id], 'stop', 100)
            except BaseException as exc:
                record['cleanup_error'] = repr(exc)
        with socket.socket() as sock:
            record['owned_service_stopped'] = sock.connect_ex(('127.0.0.1', 30001)) != 0
        complete = (record.get('accuracy_result', {}).get('numeric_pass', False)
                    and record.get('complete_native_matrix_verified', False)
                    and record['owned_service_stopped'] and record['phases'].get('stop') == 0)
        record.update(state='validated_pending_final_delivery' if complete else 'accuracy_or_performance_not_qualified',
                      ended_utc=now(), technical_delivery_complete=False)
        save(record)
    entries = []
    with zipfile.ZipFile('/root/session017-robo-refspatial001.zip', 'x', zipfile.ZIP_DEFLATED) as bundle:
        for directory, dirs, names in os.walk(OUT, onerror=lambda error: (_ for _ in ()).throw(error)):
            dirs[:] = sorted(d for d in dirs if d not in ('.git', '__pycache__'))
            for name in sorted(names):
                path = Path(directory) / name
                assert not path.is_symlink()
                relative = path.relative_to(OUT).as_posix()
                bundle.write(path, relative)
                entries.append({'path': relative, 'bytes': path.stat().st_size, 'sha256': sha(path)})
        bundle.writestr('MANIFEST.json', json.dumps({'scope': 'All queued run files; no removed failures', 'files': entries}, indent=2))
    print(json.dumps(record, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    try:
        main()
    except BaseException as exc:
        if (OUT / 'progress.json').is_file():
            record = json.loads((OUT / 'progress.json').read_text())
            record.update(state='failed', error=repr(exc), ended_utc=now(), submitted=False)
            save(record)
        raise
