"""Combine four pre-image cases and eight fresh native cases; preserve all sources."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import zipfile


ALL = {(n,c,r) for n in (4096,16384) for c in (1,8,64) for r in (1,2)}
OLD = {(4096,c,r) for c in (1,8) for r in (1,2)}
WRAPPER = 'ff8eef852e19f336e99884cc031353627ca304c6a7534c22375116758a850000'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024**2),b''):h.update(block)
    return h.hexdigest()


def select(old,new):
    selected=[]
    for report,expected,is_old in [(old,OLD,True),(new,ALL-OLD,False)]:
        assert report['source_provenance']['verified_for_reanalysis']
        candidates=[r for r in report['rows'] if r['eligible_client_report']]
        if is_old:candidates=[r for r in candidates if (r['text_target_tokens'],r['concurrency'],r['round']) in OLD]
        keys=[(r['text_target_tokens'],r['concurrency'],r['round']) for r in candidates]
        assert len(keys)==len(set(keys)) and set(keys)==expected
        for r in candidates:
            assert r['process_status']=='exited' and r['exit_code']==0 and r['child_reaped']
            assert r['expected_requests']==max(8,2*r['concurrency'])
            selected.append(dict(r,selected_from='pre_image' if is_old else 'post_image'))
    assert len(selected)==12 and sum(r['expected_requests'] for r in selected)==608
    return selected


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--old',type=Path,required=True);p.add_argument('--new',type=Path,required=True)
    p.add_argument('--old-project',type=Path,required=True);p.add_argument('--new-project',type=Path,required=True)
    p.add_argument('--source-zip',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();reports=[json.loads(x.read_text()) for x in (a.old,a.new)]
    rows=select(*reports);profiles=[];sources=[];identities=[]
    for path,report in zip((a.old,a.new),reports):
        run=Path(report['source_run_path']);assert sha(run)==report['source_run_sha256']
        data=json.loads(run.read_text());assert data['driver_sha256']==WRAPPER
        cfgs=list((run.parent/'runtime/before').glob('config-*.json'));assert len(cfgs)==1
        cfg=json.loads(cfgs[0].read_text());profiles.append({k:v for k,v in cfg.items() if k not in ('task','run_id')})
        identities.append({'client_python':data['client_python'],'version':data['client_identity']['version'],
                           'sources':data['client_identity']['sources']})
        for r in report['rows']:
            if r['eligible_client_report']:assert sha(run.parent/r['native_file'])==r['native_file_sha256']
        sources.append({'analysis':str(path),'analysis_sha256':sha(path),'run':str(run),'run_sha256':sha(run),
                        'runtime_config_sha256':sha(cfgs[0])})
    assert profiles[0]==profiles[1] and identities[0]==identities[1]
    assert sha(a.source_zip)=='0e23f35bb4e99208cbc50d10d556d0fb1d9ac9ad9023c68db7ce99ebe3b4a2ef'
    code=[]
    with zipfile.ZipFile(a.source_zip) as z:
        assert z.testzip() is None
        for item in z.infolist():
            if item.is_dir() or not item.filename.endswith(('.py','.sh')):continue
            raw=z.read(item);h=hashlib.sha256(raw).hexdigest()
            for project in (a.old_project,a.new_project):assert sha(project/item.filename)==h,item.filename
            code.append({'path':item.filename,'sha256':h})
    result={'UTC':dt.datetime.now(dt.timezone.utc).isoformat(),'complete_native_matrix':True,
            'native_reports':12,'measured_requests':608,'rows':rows,'identical_profile':profiles[0],
            'identical_client_identity':identities[0],'immutable_runtime_sources':code,'source_reports':sources,
            'selection_policy':'Four completed pre-image cases retained; the image-overlapping attempt and unfinished cases preserved and replaced by only eight post-image cases',
            'excluded_old_cases_preserved':[r['name'] for r in reports[0]['rows'] if (r['text_target_tokens'],r['concurrency'],r['round']) not in OLD],
            'output_tokens':1024,'model_accuracy_repeated':False,'official_acceptance':False,'submitted':False,
            'exact_output_tokens_independently_verified':False}
    with a.output.open('x') as f:f.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'complete_native_matrix':True,'native_reports':12,'measured_requests':608}))


if __name__=='__main__':main()
