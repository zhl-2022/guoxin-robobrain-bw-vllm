"""Wait for the exact owned native matrix, then replay fixed portable root code.

Never stops existing work, launches a duplicate model, or changes a Notebook.
Only the new UUID is cleaned up; complete and failed evidence is preserved.
"""
from pathlib import Path, PurePosixPath
import datetime as dt
import hashlib
import json
import os
import resource
import signal
import socket
import stat
import subprocess
import time
import uuid
import zipfile

BASE = Path('/root/private_data/guoxin-session025')
OUT = BASE / 'robo-root-replay001'
PRIOR = Path('/root/private_data/guoxin-session021/robo-continuation002')
ZIP = Path('/root/session025-robo-refspatial-root-source-v2.zip')
LOCK = Path('/root/session025-robo-root-project-lock-v2.json')
ZIP_SHA = '6b3f24631e3451003ad6924c00f4e63721fc585ae123fa5bf92e1ee2ad6d6c04'
LOCK_SHA = 'f334ee094ef98c3d8dadd060c6a795395e2e80e53d0ab12ef6cf9d7e787db2c9'
COMMIT = 'f5cc42d64f0143fa2f25a63d513c69a44c1f55d1'
PORTS = (30000, 30001, 30002, 30109, 30119, 30129, 30139)


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024**2), b''):
            value.update(chunk)
    return value.hexdigest()


def identity(pid):
    try:
        root = Path('/proc') / str(pid)
        fields = (root / 'stat').read_text().rsplit(')', 1)[1].split()
        return {'state': fields[0], 'token': fields[19],
                'argv': (root / 'cmdline').read_bytes().split(b'\0')[:-1]}
    except (FileNotFoundError, ProcessLookupError):
        return None


def save(record):
    temp = OUT / 'progress.tmp'
    temp.write_text(json.dumps(record, indent=2) + '\n')
    temp.replace(OUT / 'progress.json')


def ports_clear():
    for port in PORTS:
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1', port)) == 0:
                return False
    return True


def extract_fixed(project):
    assert sha(ZIP) == ZIP_SHA and sha(LOCK) == LOCK_SHA
    manifest = json.loads(LOCK.read_text())
    assert manifest['git_commit'] == COMMIT and manifest['archive_sha256'] == ZIP_SHA
    rows = manifest['files']
    assert len(rows) == len({row['path'] for row in rows}) == 1098
    project.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(ZIP) as bundle:
        assert bundle.testzip() is None and bundle.comment.decode() == COMMIT
        names = bundle.namelist()
        assert len(names) == len(set(names))
        assert {name for name in names if not name.endswith('/')} == {row['path'] for row in rows}
        for item in bundle.infolist():
            name = PurePosixPath(item.filename)
            assert not name.is_absolute() and '..' not in name.parts and '\\' not in item.filename
            assert ':' not in item.filename and not stat.S_ISLNK(item.external_attr >> 16)
        for row in rows:
            path = project / row['path']
            assert path.resolve().is_relative_to(project.resolve())
            raw = bundle.read(row['path'])
            assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
            assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['git_blob']
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(raw)


def archive_all():
    rows = []
    with zipfile.ZipFile('/root/session025-robo-root-replay001.zip', 'x', zipfile.ZIP_DEFLATED) as bundle:
        def failed_scan(error):
            raise error
        for folder, dirs, files in os.walk(OUT, onerror=failed_scan):
            dirs[:] = sorted(name for name in dirs if name not in ('.git', '__pycache__'))
            for name in dirs + files:
                assert not (Path(folder) / name).is_symlink()
            for name in sorted(files):
                path = Path(folder) / name
                relative = path.relative_to(OUT).as_posix()
                bundle.write(path, relative)
                rows.append({'path': relative, 'bytes': path.stat().st_size, 'sha256': sha(path)})
        bundle.writestr('MANIFEST.json', json.dumps({'scope': 'All fixed root replay files, successes and failures retained', 'files': rows}, indent=2))


def main():
    assert socket.gethostname() == 'crdnotebook-2112186448839770114-ac3p4mowhz-97046'
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    assert Path('/dev/kfd').exists()
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT / 'executed-controller.py').write_bytes(Path(__file__).read_bytes())
    record = {'started_utc': now(), 'controller_pid': os.getpid(), 'source_sha256': sha(__file__),
              'git_commit': COMMIT, 'source_archive_sha256': ZIP_SHA,
              'state': 'waiting_exact_owned_Robo_native_cleanup', 'phases': {}, 'GPU_started': False,
              'root_entry_replayed': False, 'technical_delivery_complete': False,
              'Notebook_shutdown_requested': False, 'submitted': False}
    save(record)
    deadline = time.monotonic() + 43200
    while True:
        owner = identity(56755)
        if owner is None or owner['state'] == 'Z' or owner['token'] != '317164876':
            break
        assert owner['argv'] == [b'python3', b'-u', b'/root/continue_robo_after_image021v2.py']
        assert time.monotonic() < deadline, 'Native coordinator still active; existing work left untouched'
        time.sleep(20)
    previous = json.loads((PRIOR / 'progress.json').read_text())
    assert previous['complete'] and previous['owned_services_cleaned'] and previous['phases']['stop'] == 0
    assert previous.get('current_child') is None
    native = json.loads((PRIOR / 'combined-native-matrix.json').read_text())
    assert native['complete_native_matrix'] and native['native_reports'] == 12 and native['measured_requests'] == 608
    wrapper = identity(58566)
    assert wrapper is None or wrapper['state'] == 'Z' or wrapper['token'] != '317339796'
    assert ports_clear(), 'Another active model was left untouched'
    record.update(state='preparing_exact_fixed_root', complete_native_matrix_verified=True,
                  native_proof_sha256=sha(PRIOR / 'combined-native-matrix.json'),
                  prior_expected_AuK_migration_release_error=previous.get('release_error'))
    save(record)
    project = OUT / 'project'
    extract_fixed(project)
    preflight = json.loads((project / 'evidence/robobrain-preflight-hashed-001.json').read_text())
    model = Path(preflight['model_path'])
    identities = preflight['model_checks']['shards'] + preflight['files']
    for item in identities:
        assert sha(model / item['name']) == item['sha256']
    record['model_files_rehashed'] = len(identities)
    env = os.environ.copy()
    env.update(ROBOBRAIN_MODEL_PATH=str(model), ROBOBRAIN_SERVED_NAME=str(model),
               ROBOBRAIN_PYTHON_BIN='/usr/bin/python3', ROBOBRAIN_MAX_RUNTIME_SECONDS='43200',
               ROBOBRAIN_MAX_LEN='32768', ROBOBRAIN_MEM_FRAC='0.85',
               ROBOBRAIN_LOAD_TIMEOUT='1800', ROBOBRAIN_MAX_NUM_SEQS='4',
               HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
               PYTHONPATH=str(project / 'scripts'))
    run_id = uuid.uuid4().hex
    record.update(state='root_entry_GPU_replay', run_id=run_id)
    save(record)

    def step(argv, label, seconds):
        with (OUT / (label + '.log')).open('xb') as log:
            child = subprocess.Popen(argv, cwd=project, env=env, stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            record['current_child'] = {'pid': child.pid, 'argv': argv}
            save(record)
            try:
                code = child.wait(timeout=seconds)
            except BaseException:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGINT)
                    try:
                        child.wait(timeout=120)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGTERM)
                        child.wait(timeout=30)
                raise
        record['phases'][label] = code
        record['current_child'] = None
        save(record)
        return code

    launched = False
    try:
        launched = True
        record['GPU_started'] = True
        save(record)
        assert step(['bash', 'run.sh', '--run-id', run_id], 'launch', 2100) == 0
        task = project / 'tasks/robobrain-bw-vllm'
        config = json.loads((task / 'runtime' / ('config-' + run_id + '.json')).read_text())
        old_runtime = PRIOR / 'project/tasks/robobrain-bw-vllm/runtime'
        old = json.loads((old_runtime / 'config-6a8bc01951644a9d84d6e7acf8794246.json').read_text())
        normalize = lambda value: {k: v for k, v in value.items() if k not in ('task', 'run_id')}
        assert normalize(config) == normalize(old), 'Actual root profile differs from the native matrix'
        record['same_actual_config_except_task_and_UUID'] = True
        save(record)
        assert step(['bash', 'env_check.sh'], 'environment', 180) == 0
        assert step(['bash', 'smoke.sh'], 'smoke', 900) == 0
        assert step(['/usr/bin/python3', 'verify.py', '--selfcheck'], 'selfcheck', 180) == 0
        assert step(['bash', 'bench.sh', '--plan'], 'bench-plan', 180) == 0
        assert step(['/usr/bin/python3', 'verify.py', '--output', str(OUT / 'evaluation')], 'verify', 5400) == 0
        result = json.loads((OUT / 'evaluation/verify_result.json').read_text())
        assert result['complete'] and result['sample_count'] == 200 and result['excluded'] == 0
        assert result['numeric_pass'] and result['stricter_relative_pass']
        record.update(root_entry_replayed=True, accuracy_result=result,
                      accuracy_result_sha256=sha(OUT / 'evaluation/verify_result.json'))
    except BaseException as exc:
        record['replay_error'] = repr(exc)
    finally:
        if launched:
            try:
                assert step(['bash', 'stop.sh', '--run-id', run_id], 'stop', 100) == 0
            except BaseException as exc:
                record['cleanup_error'] = repr(exc)
        record['owned_service_stopped'] = ports_clear()
        complete = record['root_entry_replayed'] and record['phases'].get('stop') == 0 and record['owned_service_stopped']
        record.update(state='complete_root_replay_pending_final_delivery' if complete else 'root_replay_or_cleanup_failed',
                      ended_utc=now())
        save(record)
    archive_all()
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    try:
        main()
    except BaseException as exc:
        if (OUT / 'progress.json').exists():
            value = json.loads((OUT / 'progress.json').read_text())
            value.update(state='failed', error=repr(exc), ended_utc=now(), submitted=False)
            save(value)
        raise
