"""Audit complete200 archived real requests and independently rescore on CPU."""
from pathlib import Path,PurePosixPath
import datetime as dt
import hashlib
import importlib.util
import json
import math
import stat
import subprocess
import sys
import zipfile


ROOT=Path(__file__).resolve().parents[2]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    archive=ROOT/'dist/session017-robo-refspatial001.zip'
    assert sha(archive)=='71bc904667e1c54c507ac21661fa31666803cbbe5eaa53d3138a015f53846a3f'
    out=ROOT/'evidence/session021/robo-initial-originals';out.mkdir(exist_ok=False)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        names=[x.filename for x in z.infolist() if not x.is_dir()];assert len(names)==len(set(names))
        manifest=json.loads(z.read('MANIFEST.json'));rows=manifest['files']
        assert set(names)=={r['path'] for r in rows}|{'MANIFEST.json'}
        for row in rows:
            name=PurePosixPath(row['path']);assert not name.is_absolute() and '..' not in name.parts
            info=z.getinfo(row['path']);assert not stat.S_ISLNK(info.external_attr>>16)
            raw=z.read(row['path']);assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
            p=out/row['path'];p.parent.mkdir(parents=True,exist_ok=True)
            with p.open('xb') as f:f.write(raw)
    sources=ROOT/'evidence/session021/robo-author-sources';sources.mkdir(exist_ok=False)
    queue=ROOT/'dist/session017-refspatial-queue001.zip'
    assert sha(queue)=='b337960b56b5e26e2282db68c2614031357f7167e75b0cc0806e9face602ae5a'
    with zipfile.ZipFile(queue) as z:
        assert z.testzip() is None
        for n in ['Evaluation/summarize_acc.py','Evaluation/test_benchmark.py','RoboBrain2.5/inference.py']:
            p=sources/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read('sources/'+n))
    worker=ROOT/'scripts/submission013/evaluate_refspatial017.py'
    spec=importlib.util.spec_from_file_location('refspatial_audited',worker);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    data=ROOT/'datasets/session017/refspatial200-002';ready,samples,annotations,scorer=m.data_check(data,sources)
    protocol=json.loads((out/'evaluation/protocol.json').read_text());assert protocol['source_sha256']==sha(worker)
    predictions=[json.loads(line) for line in (out/'evaluation/predictions.jsonl').read_text(encoding='utf-8').splitlines()]
    mapping={r['id']:r for r in predictions};assert len(predictions)==len(mapping)==200
    model='/root/private_data/SothisAI/model/Aihub/RoboBrain2.5-8B-NV/main/RoboBrain2.5-8B-NV'
    responses=[]
    for sample in samples:
        row=mapping[sample['id']];assert row['status']=='ok' and row['finish_reason']=='stop'
        assert row['image_sha256']==sample['image_sha256']
        body=m.request_body(sample,data,model);assert body['messages'][0]['content'][1]['text']==sample['question']
        assert hashlib.sha256(json.dumps(body,ensure_ascii=False).encode()).hexdigest()==row['request_sha256']
        raw=row['raw_response_utf8'].encode();assert hashlib.sha256(raw).hexdigest()==row['raw_response_sha256']
        response=json.loads(raw);assert response==row['raw_response'] and response['model']==model
        choice=response['choices'][0];assert choice['message']['content']==row['text'] and choice['finish_reason']=='stop'
        assert math.isfinite(row['wall_seconds']) and row['wall_seconds']>0
        responses.append(response['id'])
    assert len(set(responses))==200
    rescore=ROOT/'evidence/session021/robo-full200-local-rescore'
    subprocess.run([sys.executable,str(worker),'--data',str(data),'--sources',str(sources),
                    '--rescore',str(out/'evaluation/predictions.jsonl'),'--output',str(rescore)],check=True)
    result=json.loads((rescore/'verify_result.json').read_text());original=json.loads((out/'evaluation/verify_result.json').read_text())
    assert result==original and result['sample_count']==200 and result['score_percent']==63.0
    assert result['excluded']==0 and not result['parse_exceptions_counted_as_zero'] and result['length_finishes']==0
    receipt={'UTC':dt.datetime.now(dt.timezone.utc).isoformat(),'complete_archive_CRC_and_manifest_verified':True,
             'archive_files':len(rows),'samples':200,'all_input_image_hashes_verified':True,
             'reconstructed_request_hash_matches':200,'unique_raw_response_ids':200,
             'raw_response_UTF8_hash_matches':200,'full_author_grader_rescore_matches':True,
             'score_percent':63.0,'split_scores_percent':result['split_scores_percent'],
             'numeric_pass':True,'GPU_requests':0,'performance_complete':False,'submitted':False,
             'archive_sha256':sha(archive),'worker_sha256':sha(worker)}
    target=ROOT/'evidence/session021/robo-full200-independent-audit.json'
    with target.open('x') as f:f.write(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__=='__main__':main()
