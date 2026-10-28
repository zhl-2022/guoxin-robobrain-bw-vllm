"""Independently audit closed Robo native and fixed-root archives on CPU."""
from pathlib import Path, PurePosixPath
import datetime as dt
import hashlib
import importlib.util
import json
import math
import stat
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'evidence/session030'
sys.path.insert(0, str(ROOT / 'scripts'))
import analyze_sglang_results_004 as native


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024**2), b''):
            h.update(block)
    return h.hexdigest()


def unpack(name, digest, target):
    path = ROOT / name
    assert sha(path) == digest
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        names = [i.filename for i in z.infolist() if not i.is_dir()]
        assert len(names) == len(set(names))
        rows = json.loads(z.read('MANIFEST.json'))['files']
        assert len(rows) == len({r['path'] for r in rows})
        assert set(names) == {r['path'] for r in rows} | {'MANIFEST.json'}
        for row in rows:
            name = PurePosixPath(row['path'])
            assert not name.is_absolute() and '..' not in name.parts
            assert not stat.S_ISLNK(z.getinfo(str(name)).external_attr >> 16)
            raw = z.read(str(name))
            assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
            dest = target / str(name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                assert dest.is_file() and not dest.is_symlink() and sha(dest) == row['sha256']
            else:
                with dest.open('xb') as stream:
                    stream.write(raw)
    return len(rows)


def main():
    OUT.mkdir(exist_ok=True)
    continuation = OUT / 'robo-native-originals'
    replay = OUT / 'robo-root-originals'
    native_count = unpack('dist/session021-robo-continuation001.zip',
        '8ce787013f0b1c45e244587e607661d577c55c1635c3f17a9e383c17e9106577', continuation)
    replay_count = unpack('dist/session025-robo-root-replay001.zip',
        '4db560cbf7cee6fa731884f52643b0b1d7d7d4967afc28c809a8f98ef458d2df', replay)
    proof = json.loads((continuation / 'combined-native-matrix.json').read_text())
    assert proof['complete_native_matrix'] and proof['native_reports'] == 12 and proof['measured_requests'] == 608
    assert sha(native.__file__) == 'd73ecca728b47b8f58fed407f13c9a496e73ba8e165ee08b740afd9065efdaa8'
    keys = set()
    checked = []
    runs = []
    for kind, base in [('pre_image', ROOT / 'evidence/session021/robo-initial-originals'),
                       ('post_image', continuation)]:
        raw_run = (base / 'performance/run.json').read_bytes()
        source = proof['source_reports'][len(runs)]
        assert hashlib.sha256(raw_run).hexdigest() == source['run_sha256']
        run, _ = native.parse_json(raw_run)
        runs.append(run)
        config_files = list((base / 'performance/runtime/before').glob('config-*.json'))
        assert len(config_files) == 1 and sha(config_files[0]) == source['runtime_config_sha256']
        config = json.loads(config_files[0].read_text())
        assert {k: v for k, v in config.items() if k not in ('task', 'run_id')} == proof['identical_profile']
        for row in proof['rows']:
            if row['selected_from'] != kind:
                continue
            key = (row['text_target_tokens'], row['concurrency'], row['round'])
            assert key not in keys
            keys.add(key)
            assert row['process_status'] == 'exited' and row['exit_code'] == 0 and row['child_reaped']
            raw = (base / 'performance' / row['native_file']).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == row['native_file_sha256']
            result = native.native_result(raw, row)
            assert result['native_structure_complete'] and not result['issues']
            assert {k: v for k, v in result.items() if k != 'native_record'} == row['parsed']
            assert len(result['normalizations']) == 1
            assert result['normalizations'][0]['path'] == '$.request_rate'
            checked.append({'name': row['name'], 'sha256': row['native_file_sha256'],
                            'requests': row['expected_requests'], 'metrics': result['metrics']})
    assert keys == {(n, c, r) for n in (4096, 16384) for c in (1, 8, 64) for r in (1, 2)}
    assert sum(r['requests'] for r in checked) == 608
    for field in ['version', 'sources']:
        assert runs[0]['client_identity'][field] == runs[1]['client_identity'][field]
    assert runs[0]['client_python'] == runs[1]['client_python']
    record = json.loads((replay / 'progress.json').read_text())
    assert record['root_entry_replayed'] and record['owned_service_stopped']
    assert all(record['phases'][k] == 0 for k in ['launch', 'environment', 'smoke', 'selfcheck', 'bench-plan', 'verify', 'stop'])
    assert sha(continuation / 'combined-native-matrix.json') == record['native_proof_sha256']
    lock = json.loads((ROOT / 'evidence/session025/robo-root-project-lock-v2.json').read_text())
    rows = lock['files']
    assert len(rows) == 1098
    for row in rows:
        p = replay / 'project' / row['path']
        assert sha(p) == row['sha256']
    runtime = replay / 'project/tasks/robobrain-bw-vllm/runtime'
    config = json.loads((runtime / ('config-' + record['run_id'] + '.json')).read_text())
    assert {k: v for k, v in config.items() if k not in ('task', 'run_id')} == proof['identical_profile']
    worker = ROOT / 'scripts/submission013/evaluate_refspatial017.py'
    assert sha(worker) == sha(replay / 'project/scripts/submission013/evaluate_refspatial017.py')
    spec = importlib.util.spec_from_file_location('refspatial030', worker)
    evaluator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluator)
    data = ROOT / 'datasets/session017/refspatial200-002'
    sources = ROOT / 'evidence/session021/robo-author-sources'
    _, samples, _, _ = evaluator.data_check(data, sources)
    protocol = json.loads((replay / 'evaluation/protocol.json').read_text())
    assert protocol['source_sha256'] == sha(worker)
    predictions = [json.loads(line) for line in (replay / 'evaluation/predictions.jsonl').read_text(encoding='utf-8').splitlines()]
    mapping = {r['id']: r for r in predictions}
    assert len(predictions) == len(mapping) == 200
    ids = []
    for sample in samples:
        row = mapping[sample['id']]
        assert row['status'] == 'ok' and row['finish_reason'] == 'stop'
        assert row['image_sha256'] == sample['image_sha256']
        body = evaluator.request_body(sample, data, config['served_name'])
        assert hashlib.sha256(json.dumps(body, ensure_ascii=False).encode()).hexdigest() == row['request_sha256']
        raw = row['raw_response_utf8'].encode()
        assert hashlib.sha256(raw).hexdigest() == row['raw_response_sha256']
        response = json.loads(raw)
        assert response == row['raw_response'] and response['model'] == config['served_name']
        assert response['choices'][0]['message']['content'] == row['text']
        assert response['choices'][0]['finish_reason'] == 'stop'
        assert math.isfinite(row['wall_seconds']) and row['wall_seconds'] > 0
        ids.append(response['id'])
    assert len(set(ids)) == 200
    rescore = OUT / 'robo-root-full200-rescore'
    subprocess.run([sys.executable, str(worker), '--data', str(data), '--sources', str(sources),
                    '--rescore', str(replay / 'evaluation/predictions.jsonl'), '--output', str(rescore)], check=True)
    result = json.loads((rescore / 'verify_result.json').read_text())
    assert result == json.loads((replay / 'evaluation/verify_result.json').read_text())
    assert result['sample_count'] == 200 and result['score_percent'] == 65.0
    assert result['excluded'] == 0 and not result['parse_exceptions_counted_as_zero'] and result['length_finishes'] == 0
    receipt = {'UTC': dt.datetime.now(dt.timezone.utc).isoformat(),
               'complete_CRC_manifest_and_all_payload_SHA_verified': True,
               'native_archive_payloads': native_count, 'root_archive_payloads': replay_count,
               'native_reports': 12, 'measured_requests': 608, 'strict_native_array_and_metric_recheck': True,
               'only_top_level_request_rate_Infinity_normalized': True, 'same_actual_profile_except_task_UUID': True,
               'fixed_root_Git_files_verified': 1098, 'git_commit': record['git_commit'],
               'all_root_phases_exit0': True, 'owned_service_stopped': True,
               'complete_input_images_reconstructed_requests_unique_raw_responses': 200,
               'full_author_CPU_rescore_matches': True, 'accuracy': result,
               'GPU_requests_by_auditor': 0, 'technical_delivery_complete': False, 'submitted': False,
               'native_rows': checked}
    with (OUT / 'robo-full-native-root-independent-audit.json').open('x', encoding='utf-8') as f:
        f.write(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'native_rows'}))


if __name__ == '__main__':
    main()
