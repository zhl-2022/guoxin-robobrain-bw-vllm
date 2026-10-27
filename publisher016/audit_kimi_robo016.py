"""Independently check complete raw runs and recompute frozen public scorers."""
from pathlib import Path
import ast
import base64
import copy
import datetime as dt
import hashlib
import importlib.util
import json
import math
import stat
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


def verified_extract(archive,target):
    target.mkdir(exist_ok=True,parents=True)
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        manifest = json.loads(bundle.read('MANIFEST.json'))['files']
        assert len(bundle.namelist()) == len(set(bundle.namelist())) == len(manifest)+1
        assert set(bundle.namelist()) == {r['path'] for r in manifest}|{'MANIFEST.json'}
        for item in manifest:
            path = target/item['path']
            assert path.resolve().is_relative_to(target.resolve()) and not Path(item['path']).is_absolute()
            assert not stat.S_ISLNK(bundle.getinfo(item['path']).external_attr >> 16)
            data = bundle.read(item['path'])
            assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
            if path.exists(): assert path.read_bytes() == data
            else:
                path.parent.mkdir(parents=True,exist_ok=True)
                with path.open('xb') as stream:stream.write(data)
    return {'archive_sha256':digest(archive),'files':len(manifest),'CRC_manifest_and_file_hashes':True}


def audit_ocr(attempt=3):
    name = 'kimi-ocrbench' + str(attempt).zfill(3)
    raw = ROOT/'evidence/session016'/name
    proof = verified_extract(ROOT/'dist'/('session016-'+name+'.zip'),raw)
    final = json.loads((raw/'run-final.json').read_text())
    assert digest(raw/'executed-controller.py') == final['source_sha256']
    if attempt == 3:
        assert final['source_sha256'] == '9530b0b9f7844e4e78db96d886264de5b47e98dc54a7a4a738a6db8dcd263210'
    else:
        assert attempt == 4 and final['long_prefill_safe']
    assert final['complete'] and final['owned_service_stopped'] and final['budget_exhausted'] == 0
    data = ROOT/'datasets/session016/ocrbench001'
    samples = rows(data/'samples.jsonl')
    labels = json.loads((data/'annotations.json').read_text(encoding='utf-8'))
    predictions = rows(raw/'predictions.jsonl')
    assert len(samples) == len(labels) == len(predictions) == len({r['id'] for r in predictions}) == 1000
    mapping = {r['id']:r for r in predictions}
    assert set(mapping) == {s['id'] for s in samples} == {s['id'] for s in labels}
    from PIL import Image
    import io,mimetypes
    for sample in samples:
        row = mapping[sample['id']]
        path = data/sample['image']
        assert digest(path) == sample['image_sha256'] == row['image_sha256']
        image = Image.open(path)
        if image.mode == 'RGBA':
            image = Image.alpha_composite(Image.new('RGBA',image.size,(255,255,255,255)),image).convert('RGB')
        buffer = io.BytesIO()
        image.convert('RGB').save(buffer,format=sample['image_format'])
        mime = mimetypes.guess_type(path.name)[0] or 'image/jpeg'
        body = dict(final['decoding'],model='kimi-vl-a3b-instruct',messages=[{'role':'user','content':[
            {'type':'image_url','image_url':{'url':'data:'+mime+';base64,'+base64.b64encode(buffer.getvalue()).decode()}},
            {'type':'text','text':sample['question']}]}],stream=False)
        assert hashlib.sha256(json.dumps(body,ensure_ascii=False).encode()).hexdigest() == row['request_sha256']
        assert row['status'] == 'ok' and row['finish_reason'] == 'stop'
        assert row['text'] == row['raw_response']['choices'][0]['message']['content']
    frame = [dict(label,answer=repr(label['answer']),prediction=mapping[label['id']]['text']) for label in labels]
    class Frame:
        iloc = frame
        def __len__(self):return len(frame)
    source = ROOT/'evidence/session014/sources/vlmeval-image-vqa-160e8a7.py'
    assert digest(source) == final['scorer_source_sha256']
    tree = ast.parse(source.read_text(encoding='utf-8'))
    cls = next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name == 'OCRBench')
    ns = {'ImageBaseDataset':object,'load':lambda _:Frame(),'eval':ast.literal_eval,'tqdm':lambda x:x,
          'get_intermediate_file_path':lambda *x:None,'dump':lambda *x:None}
    exec(compile(ast.Module(body=[cls],type_ignores=[]),'<pinned public OCRBench scorer>','exec'),ns)
    score = ns['OCRBench'].evaluate('unused')
    assert score == final['score'] and score['Final Score'] == (867 if attempt == 3 else 861)
    workers = [json.loads(p.read_text()) for p in (raw/'math-sdpa-worker-audits').glob('*.json')]
    assert workers and all(r['math'] and not r['flash'] and not r['mem_efficient'] for r in workers)
    proof.update(samples=1000,images_requests_and_raw_responses_verified=1000,score=score,
                 full_split=True,unfiltered=True,publisher_baseline=867,threshold=847,numeric_pass=True,
                 worker_audits=len(workers),MMMU_pass=False,technical_delivery_complete=False,submitted=False)
    return proof


def audit_mmmu():
    raw = ROOT/'evidence/session014/kimi-full014'
    proof = verified_extract(ROOT/'dist/session013-kimi-whole-attempt2.zip',raw)
    final = json.loads((raw/'run-final.json').read_text())
    assert digest(raw/'executed-controller.py') == final['source_sha256']
    data = ROOT/'datasets/session010/mmmu'
    samples = rows(data/'samples.jsonl')
    predictions = rows(raw/'predictions.jsonl')
    assert len(samples) == len(predictions) == len({r['id'] for r in predictions}) == 900
    assert {r['id'] for r in predictions} == {s['id'] for s in samples}
    assert all(r['status'] == 'ok' and r['text'] == r['raw_response']['choices'][0]['message']['content'] for r in predictions)
    sys.path.insert(0,str(ROOT/'scripts/submission010'))
    from evaluate_vlm003 import score
    source = ROOT/'evidence/session010/sources/vlmeval-kimi-vl.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    extractor = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name == 'extract_boxed_content')
    ns = {}
    exec(compile(ast.Module(body=[extractor],type_ignores=[]),'<published boxed extractor>','exec'),ns)
    transformed = copy.deepcopy(predictions)
    for row in transformed:row['text'] = ns['extract_boxed_content'](row['text'])
    scored,metrics = score(samples,transformed,'mmmu')
    remote = json.loads((ROOT/'evidence/session014/kimi-scoring-full015/verify_result.json').read_text())
    assert metrics == remote['boxed_final_score']
    from collections import Counter
    remote_rows = rows(ROOT/'evidence/session014/kimi-scoring-full015/boxed-scored.jsonl')
    assert len(scored) == len(remote_rows)
    for here,there in zip(scored,remote_rows):
        assert {k:v for k,v in here.items() if k != 'parsed'} == {k:v for k,v in there.items() if k != 'parsed'}
        # Upstream open-answer parser returns list(set(...)); hash ordering differs across processes.
        if isinstance(here['parsed'],list):
            assert Counter(json.dumps(v,sort_keys=True) for v in here['parsed']) == Counter(json.dumps(v,sort_keys=True) for v in there['parsed'])
        else: assert here['parsed'] == there['parsed']
    assert digest(raw/'predictions.jsonl') == remote['raw_predictions_sha256']
    proof.update(samples=900,full_split=True,score_recomputed=metrics,numeric_pass=False,submitted=False)
    return proof


def audit_robo():
    raw = ROOT/'evidence/session016/robo-spatial-full015'
    proof = verified_extract(ROOT/'dist/session014-robo-spatial-full015.zip',raw)
    final = json.loads((raw/'run-final.json').read_text())
    assert digest(raw/'executed-controller.py') == final['source_sha256']
    assert final['owned_service_stopped'] and all(v == 0 for v in final['phases'].values())
    data = ROOT/'datasets/session014/robo-spatial-home015'
    samples = rows(data/'samples.jsonl')
    annotations_list = json.loads((data/'annotations.json').read_text(encoding='utf-8'))
    predictions = rows(raw/'evaluation/predictions.jsonl')
    assert len(samples) == len(predictions) == len({r['id'] for r in predictions}) == 350
    mapping = {r['id']:r for r in predictions}
    assert set(mapping) == {s['id'] for s in samples}
    for sample in samples:
        row = mapping[sample['id']]
        path = data/sample['image']
        assert digest(path) == sample['image_sha256'] == row['image_sha256']
        body = {'model':'robobrain2-5-8b-nv','messages':[{'role':'user','content':[
            {'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+base64.b64encode(path.read_bytes()).decode()}},
            {'type':'text','text':sample['prompt']}]}],
            'max_tokens':768,'temperature':0,'top_p':1,'seed':42,'stream':False}
        assert hashlib.sha256(json.dumps(body,ensure_ascii=False).encode()).hexdigest() == row['request_sha256']
        assert row['status'] == 'ok' and row['text'] == row['raw_response']['choices'][0]['message']['content']
    source_root = ROOT/'evidence/session014/sources'
    sys.path[:] = [p for p in sys.path if Path(p).resolve() != (ROOT/'scripts/submission010/vendor').resolve()]
    sys.path.insert(0,str(source_root))
    # A previous MMMU import loaded an older flagevalmm package; clear only that vendor namespace.
    for key in list(sys.modules):
        if key == 'flagevalmm' or key.startswith('flagevalmm.'):del sys.modules[key]
    spec = importlib.util.spec_from_file_location('frozen_robo_scorer016',source_root/'tasks/robo_spatial_home/evaluate_norm1k.py')
    scorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer)
    annotations = {row['question_id']:dict(row,data_root=str(data)) for row in annotations_list}
    scored = [{'question_id':s['id'],'answer':mapping[s['id']]['text']} for s in samples]
    metrics = scorer.get_result(annotations,scored)
    assert metrics == final['accuracy_result']['metrics']
    bench = list((raw/'evaluation/bench').glob('*.jsonl'))
    bench_rows = [r for p in bench for r in rows(p)]
    assert len(bench) == 4 and len(bench_rows) == 96 and all(r['status'] == 'ok' for r in bench_rows)
    proof.update(samples=350,full_split=True,images_requests_verified=350,score_recomputed=metrics,
                 extra_performance_requests_verified=96,template_six_load_matrix=False,numeric_pass=False,submitted=False)
    return proof


if __name__ == '__main__':
    result = {'UTC':dt.datetime.now(dt.timezone.utc).isoformat(),
              'OCRBench':audit_ocr(),'OCRBench_safe_replay':audit_ocr(4),'MMMU':audit_mmmu(),'RoboSpatial':audit_robo(),
              'additional_GPU_requests':0,'submitted':False}
    path = ROOT/'evidence/session016/kimi-robo-independent-audit.json'
    path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
