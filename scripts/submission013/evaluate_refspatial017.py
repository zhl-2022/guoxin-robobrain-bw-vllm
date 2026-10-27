"""Evaluate the two original RefSpatial splits with the pinned author's grader.

Only RGB and the author's question enter model requests. Masks stay local.
RoboBrain2.5 returns coordinates in 0..1000; the adapter converts that domain
to pixels, without clipping, before calling the unchanged mask grader.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
import argparse
import base64
import datetime as dt
import hashlib
import importlib.util
import io
import json
import math
import os
import re
import shutil
import time
import urllib.error
import urllib.request


REVISION = '098de7c8785277e5d3b3270d13863c8ac85a6852'
SAMPLES_SHA = '80630b66ad20713f2bc0d8423ee589a61dc6db2d2b7f482ebd2363d5bbbd24c3'
ANNOTATIONS_SHA = '97c1697cf574d3545e5457395724544abb22a34d199fe4e13c92a57b8685af29'
SOURCE_BLOBS = {
    'Evaluation/summarize_acc.py': '65a5c57802bf19c0d718e49eb1f0eec806a4d4ff',
    'Evaluation/test_benchmark.py': 'de9ef5ae26436d6fbf6c15738989305383432332',
    'RoboBrain2.5/inference.py': 'ba701a47cea304e244f0fe5be47370bfd8f1d885',
}
# This is the original text2pts tuple pattern, including its treatment of
# otherwise unparseable output. No best point, answer extraction or clipping.
TUPLES = re.compile(r'\(([-+]?\d+\.?\d*(?:,\s*[-+]?\d+\.?\d*)*?)\)')


def sha(path):
    with Path(path).open('rb') as stream:
        value = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def data_check(data, sources):
    ready = load(data / 'READY.json')
    assert ready['revision'] == REVISION and ready['samples'] == 200
    assert sha(data / 'samples.jsonl') == ready['samples_sha256'] == SAMPLES_SHA
    assert sha(data / 'annotations.json') == ready['annotations_sha256'] == ANNOTATIONS_SHA
    samples = [json.loads(s) for s in (data / 'samples.jsonl').read_text(encoding='utf-8').splitlines()]
    annotations = load(data / 'annotations.json')
    mapped = {r['id']: r for r in annotations}
    assert len(samples) == len(annotations) == len(mapped) == 200
    assert len({s['id'] for s in samples}) == 200 and set(mapped) == {s['id'] for s in samples}
    assert {k: sum(s['split'] == k for s in samples) for k in ('location', 'placement')} == {'location': 100, 'placement': 100}
    for name, blob in SOURCE_BLOBS.items():
        raw = (sources / name).read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == blob
    from PIL import Image
    for row in samples:
        annotation = mapped[row['id']]
        assert row['question'] == annotation['source_prompt'] + ' Please provide its 2D coordinates.'
        assert row['split'] == annotation['split']
        for field, digest in ((row['image'], row['image_sha256']), (annotation['mask'], annotation['mask_sha256'])):
            path = data / field
            assert path.resolve().is_relative_to(data.resolve()) and not path.is_symlink()
            assert sha(path) == digest
            with Image.open(path) as image:
                image.load()
                assert image.size == (row['width'], row['height'])
    spec = importlib.util.spec_from_file_location('refspatial_author017', sources / 'Evaluation/summarize_acc.py')
    scorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer)
    return ready, samples, mapped, scorer


def parse_norm1000(text, width, height, scorer, errors=None, question_id=None):
    def convert(match):
        values = [float(n) for n in match.group(1).split(',')]
        if len(values) not in (2, 4):
            return match.group(0)
        pixels = [int(round(value * (width if i % 2 == 0 else height) / 1000.0))
                  for i, value in enumerate(values)]
        return '(' + ', '.join(str(v) for v in pixels) + ')'
    try:
        converted = TUPLES.sub(convert, text)
        return scorer.text2pts(converted, width, height, is_absolute=True)
    except (ValueError, OverflowError) as exc:
        # Upstream compute_accuracy otherwise skips parser exceptions. A malformed
        # model answer must remain in our complete denominator with zero reward.
        if errors is not None:
            errors.append({'id': question_id, 'error': repr(exc), 'counted_as_zero': True})
        import numpy as np
        return np.empty((0, 2), dtype=int)


def request_body(row, data, model):
    path = data / row['image']
    mime = {'JPEG': 'image/jpeg', 'PNG': 'image/png', 'BMP': 'image/bmp',
            'TIFF': 'image/tiff', 'WEBP': 'image/webp'}[row['image_format']]
    return {'model': model, 'messages': [{'role': 'user', 'content': [
        {'type': 'image_url', 'image_url': {'url': 'data:' + mime + ';base64,' + base64.b64encode(path.read_bytes()).decode()}},
        {'type': 'text', 'text': row['question']},
    ]}], 'max_tokens': 768, 'temperature': 0, 'top_p': 1, 'seed': 42, 'stream': False}


@contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def score_predictions(samples, annotations, predictions, data, output, scorer):
    mapped = {r['id']: r for r in predictions}
    assert len(predictions) == len(mapped) == 200 and set(mapped) == set(annotations)
    assert all(r['status'] == 'ok' for r in predictions), 'Incomplete model requests; not an accuracy score'
    parsed_errors = []
    scored = []
    split_scores = {}
    for split in ('location', 'placement'):
        answers = []
        split_dir = output / 'RefSpatial-Bench' / split
        split_dir.mkdir(parents=True, exist_ok=False)
        for row in samples:
            if row['split'] != split:
                continue
            a = annotations[row['id']]
            mask = data / a['mask']
            shutil.copyfile(mask, split_dir / mask.name)
            answers.append({'question_id': row['id'], 'mask_path': mask.name,
                            'text': mapped[row['id']]['text']})
        with working_directory(output), (output / (split + '-author-grader.log')).open('x', encoding='utf-8') as log, redirect_stdout(log):
            scorer.compute_accuracy(answers, split,
                lambda text, w, h: parse_norm1000(text, w, h, scorer, parsed_errors))
        assert len(answers) == 100 and all('accuracy' in a for a in answers), 'Original grader excluded an answer'
        assert all(math.isfinite(float(a['accuracy'])) and 0 <= a['accuracy'] <= 1 for a in answers)
        split_scores[split] = sum(float(a['accuracy']) for a in answers) * 100 / len(answers)
        scored.extend(answers)
    assert len(scored) == 200
    score = sum(float(a['accuracy']) for a in scored) * 100 / 200
    value = {'complete': True, 'sample_count': 200, 'split_counts': {'location': 100, 'placement': 100},
             'excluded': 0, 'score_percent': score, 'split_scores_percent': split_scores,
             'publisher_baseline_percent': 60.5, 'absolute_threshold_percent': 58.5,
             'relative_threshold_percent': 59.29, 'numeric_pass': score >= 58.5,
             'stricter_relative_pass': score >= 59.29, 'coordinate_clipping': False,
             'parse_exceptions_counted_as_zero': parsed_errors,
             'length_finishes': sum(r.get('finish_reason') == 'length' for r in predictions),
             'official_acceptance': False, 'submitted': False}
    (output / 'scored-predictions.json').write_text(json.dumps(scored, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output / 'verify_result.json').write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', type=Path, required=True)
    ap.add_argument('--sources', type=Path, required=True)
    ap.add_argument('--output', type=Path)
    ap.add_argument('--model', default='robobrain2-5-8b-nv')
    ap.add_argument('--port', type=int, default=30001)
    ap.add_argument('--selfcheck', action='store_true')
    ap.add_argument('--rescore', type=Path)
    args = ap.parse_args()
    args.data, args.sources = args.data.resolve(), args.sources.resolve()
    ready, samples, annotations, scorer = data_check(args.data, args.sources)
    if args.selfcheck:
        assert parse_norm1000('[(500, 500)]', 640, 480, scorer).tolist() == [[320, 240]]
        assert parse_norm1000('[(1000, 1000), (-10, -10)]', 640, 480, scorer).tolist() == [[640, 480], [-6, -5]]
        assert len(parse_norm1000('No coordinate', 640, 480, scorer)) == 0
        errors = []
        assert len(parse_norm1000('[(900, 900, 100, 100)]', 640, 480, scorer, errors)) == 0 and len(errors) == 1
        print(json.dumps({'complete_data_sources_verified': 200, 'domain_boundary_checks': True,
                          'model_requests': 0, 'GPU_executed': False}))
        return
    assert args.output is not None
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    protocol = dict(ready, source_sha256=sha(__file__), UTC=dt.datetime.now(dt.timezone.utc).isoformat(),
                    model_revision='7ae187cc62e45cfa1c5904903a8f017f11b2037b',
                    decoding={'max_tokens': 768, 'temperature': 0, 'top_p': 1, 'seed': 42},
                    coordinate_conversion='round(native/1000*width,height); no clipping; all parsed tuples',
                    author_grader_unmodified=True, parse_error_policy='zero, never exclude a row',
                    source_blobs=SOURCE_BLOBS, inference_concurrency=4, labels_or_masks_sent_to_model=False)
    (args.output / 'protocol.json').write_text(json.dumps(protocol, indent=2) + '\n', encoding='utf-8')
    if args.rescore:
        predictions = [json.loads(r) for r in args.rescore.read_text(encoding='utf-8').splitlines()]
        result = score_predictions(samples, annotations, predictions, args.data, args.output, scorer)
        print(json.dumps(result))
        return
    assert 1 <= args.port <= 65535
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(row):
        body = request_body(row, args.data, args.model)
        raw = json.dumps(body, ensure_ascii=False).encode()
        value = {'id': row['id'], 'image_sha256': row['image_sha256'],
                 'request_sha256': hashlib.sha256(raw).hexdigest()}
        start = time.perf_counter()
        try:
            req = urllib.request.Request(f'http://127.0.0.1:{args.port}/v1/chat/completions', raw, {'Content-Type': 'application/json'})
            with opener.open(req, timeout=600) as response:
                response_raw = response.read(8 * 1024**2 + 1)
                assert len(response_raw) <= 8 * 1024**2
                result = json.loads(response_raw)
            value['raw_response'] = result
            value['raw_response_sha256'] = hashlib.sha256(response_raw).hexdigest()
            value['raw_response_utf8'] = response_raw.decode()
            choice = result['choices'][0]
            assert choice['finish_reason'] in ('stop', 'length') and isinstance(choice['message']['content'], str)
            value.update(status='ok', text=choice['message']['content'], finish_reason=choice['finish_reason'])
        except urllib.error.HTTPError as exc:
            value.update(status='failed', error=str(exc), error_body=exc.read(16384).decode(errors='replace'))
        except Exception as exc:
            value.update(status='failed', error=repr(exc))
        value['wall_seconds'] = time.perf_counter() - start
        return value

    predictions = []
    with (args.output / 'predictions.jsonl').open('x', encoding='utf-8') as stream, ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(request, row) for row in samples]
        for future in as_completed(futures):
            value = future.result()
            predictions.append(value)
            stream.write(json.dumps(value, ensure_ascii=False) + '\n')
            stream.flush()
            if len(predictions) % 10 == 0:
                print(json.dumps({'done': len(predictions), 'failed': sum(r['status'] != 'ok' for r in predictions)}), flush=True)
    if any(r['status'] != 'ok' for r in predictions):
        result = {'complete': False, 'samples': 200, 'failed_ids': [r['id'] for r in predictions if r['status'] != 'ok'],
                  'numeric_pass': None, 'submitted': False}
        (args.output / 'verify_result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(result), flush=True)
        raise SystemExit(2)
    result = score_predictions(samples, annotations, predictions, args.data, args.output, scorer)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
