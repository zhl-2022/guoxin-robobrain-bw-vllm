"""Await an operator-verified image gate, run only eight remaining Robo cases."""
from pathlib import Path,PurePosixPath
import datetime as dt
import hashlib
import json
import os
import resource
import shutil
import signal
import socket
import subprocess
import sys
import time
import uuid
import zipfile


BASE=Path('/root/private_data/guoxin-session021')
OUT=BASE/'robo-continuation002'
OLD=Path('/root/private_data/guoxin-session017/robo-refspatial001')
STAGE=Path('/root/private_data/guoxin-session017/refspatial-stage001')
GATE=BASE/'kimi-image-work-complete.json'
AUK_ARGV=['/root/private_data/guoxin-auk-port006/venv002/bin/python','-u',
          '/root/private_data/guoxin-session019/auk-zhhard-stage001/tools/run_auk_zhhard_queue019.py']
AUK_TOKEN='314793785'
PORTS=(30000,30001,30002,30109,30119,30129,30139)


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024**2),b''):h.update(block)
    return h.hexdigest()


def now():return dt.datetime.now(dt.timezone.utc).isoformat()


def identity(pid):
    root=Path('/proc')/str(pid);s=root.joinpath('stat').read_text().rsplit(')',1)[1].split()
    return {'pid':pid,'state':s[0],'ppid':int(s[1]),'token':s[19],
            'argv':[x.decode() for x in root.joinpath('cmdline').read_bytes().split(b'\0') if x]}


def alive(pid):
    try:return identity(pid)['state']!='Z'
    except (FileNotFoundError,ProcessLookupError):return False


def ports_clear():
    for port in PORTS:
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1',port))==0:return False
    return True


def main():
    assert sys.platform=='linux' and Path('/dev/kfd').exists()
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    OUT.mkdir(parents=True,exist_ok=False)
    (OUT/'executed-controller.py').write_bytes(Path(__file__).read_bytes())
    record={'UTC':now(),'controller_pid':os.getpid(),'source_sha256':sha(Path(__file__)),
            'state':'waiting_owned_Robo_cleanup','phases':{},'GPU_started':False,
            'old_accuracy200_preserved':True,'AUK_held_PID':45258,'AUK_released':False,
            'Notebook_shutdown_requested':False,'submitted':False,'complete':False}
    def save():
        p=OUT/'progress.tmp';p.write_text(json.dumps(record,indent=2)+'\n');p.replace(OUT/'progress.json')
    save();run_id=None;project=None;owned_child=None
    env=os.environ.copy()
    env.update(ROBOBRAIN_PYTHON_BIN='/usr/bin/python3',ROBOBRAIN_MAX_RUNTIME_SECONDS='43200',
               ROBOBRAIN_LOAD_TIMEOUT='1800',ROBOBRAIN_MAX_NUM_SEQS='4',HF_HUB_OFFLINE='1',
               TRANSFORMERS_OFFLINE='1',ROCM_PATH='/opt/dtk',HIP_PATH='/opt/dtk/hip')
    env['PATH']='/opt/ucx/bin:/opt/dtk/bin:/opt/dtk/llvm/bin:/opt/dtk/hip/bin:/opt/hyhal/bin:'+env.get('PATH','/usr/bin:/bin')
    env['LD_LIBRARY_PATH']=':'.join(['/opt/ucx/lib','/opt/dtk/dcc/gcvm/lib','/opt/dtk/hip/lib',
        '/opt/dtk/llvm/lib','/opt/dtk/lib','/opt/dtk/lib64','/opt/hyhal/lib','/opt/hyhal/lib64',
        '/opt/dtk/dushmem/lib','/opt/dtk/opencl/lib','/opt/mpi/lib','/opt/hwloc/lib',env.get('LD_LIBRARY_PATH','')])
    def step(argv,label,seconds):
        nonlocal owned_child
        with (OUT/(label+'.log')).open('xb') as log:
            owned_child=subprocess.Popen(argv,cwd=project or OUT,env=env,stdin=subprocess.DEVNULL,
                                         stdout=log,stderr=subprocess.STDOUT)
            record['current_child']=identity(owned_child.pid);save()
            try:code=owned_child.wait(timeout=seconds)
            except BaseException:
                if owned_child.poll() is None:
                    owned_child.send_signal(signal.SIGINT)
                    try:owned_child.wait(timeout=150)
                    except subprocess.TimeoutExpired:
                        owned_child.terminate();owned_child.wait(timeout=30)
                raise
        record['phases'][label]=code;record['current_child']=None;save();return code
    try:
        auk=identity(45258);assert auk['token']==AUK_TOKEN and auk['argv']==AUK_ARGV and auk['state']=='T'
        deadline=time.monotonic()+600
        while alive(43964) or alive(54510) or not Path('/root/session017-robo-refspatial001.zip').is_file():
            assert time.monotonic()<deadline,'Old controller still owns work; no GPU launch'
            time.sleep(10)
        old=json.loads((OLD/'progress.json').read_text());assert old['owned_service_stopped'] and ports_clear()
        assert old['accuracy_result']['complete'] and old['accuracy_result']['sample_count']==200
        assert old['accuracy_result']['numeric_pass'] and old['accuracy_result']['score_percent']==63.0
        record.update(state='waiting_operator_verified_image_gate',old_progress_sha256=sha(OLD/'progress.json'));save()
        deadline=time.monotonic()+5400
        while not GATE.is_file():
            assert time.monotonic()<deadline,'Image gate not available within bounded wait'
            time.sleep(15)
        gate=json.loads(GATE.read_text())
        assert gate['image_save_complete'] and gate['all_image_operations_complete']
        assert gate['image_id']=='2115214831904727041' and gate['final_tag']=='dtk2604-vllm018-kimi-final-20261028'
        assert gate['fixed_code_commit']=='89033aa9c0a2a6d3912912490fea9a13d501cc86'
        assert ports_clear();record['image_gate']=gate
        archive=STAGE/'robo-project.zip'
        assert sha(archive)=='0e23f35bb4e99208cbc50d10d556d0fb1d9ac9ad9023c68db7ce99ebe3b4a2ef'
        project=OUT/'project';project.mkdir()
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            for item in z.infolist():
                n=PurePosixPath(item.filename);assert not n.is_absolute() and '..' not in n.parts
                assert item.external_attr>>28!=10
                target=project/item.filename
                if item.is_dir():target.mkdir(parents=True,exist_ok=True);continue
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as f:f.write(z.read(item))
        preflight=json.loads((project/'evidence/robobrain-preflight-hashed-001.json').read_text())
        model=Path(preflight['model_path']);identities=preflight['model_checks']['shards']+preflight['files']
        for row in identities:assert sha(model/row['name'])==row['sha256']
        env.update(ROBOBRAIN_MODEL_PATH=str(model),ROBOBRAIN_SERVED_NAME=str(model),PYTHONPATH=str(project/'scripts'))
        auditor=STAGE/'tools/analyze_sglang_results_004.py'
        assert sha(auditor)=='d73ecca728b47b8f58fed407f13c9a496e73ba8e165ee08b740afd9065efdaa8'
        assert step(['python3',str(auditor),'--run',str(OLD/'performance/run.json'),
                     '--analysis-dir',str(OUT/'old-analysis')],'old-four-analysis',180) in (0,1)
        run_id=uuid.uuid4().hex;record.update(state='remaining_eight_native_cases',GPU_started=True,run_id=run_id);save()
        assert step(['bash',str(project/'run.sh'),'--run-id',run_id],'launch',2100)==0
        runtime=project/'tasks/robobrain-bw-vllm/runtime'
        previous=list((OLD/'performance/runtime/before').glob('config-*.json'));assert len(previous)==1
        new=json.loads((runtime/('config-'+run_id+'.json')).read_text());oldcfg=json.loads(previous[0].read_text())
        norm=lambda d:{k:v for k,v in d.items() if k not in ('task','run_id')}
        assert norm(new)==norm(oldcfg),'New actual service configuration differs'
        wrapper=STAGE/'tools/t02_sglang_bench.py'
        assert sha(wrapper)=='ff8eef852e19f336e99884cc031353627ca304c6a7534c22375116758a850000'
        command=['python3',str(wrapper),'--run','--client-python','/root/private_data/sglang-client-004c/bin/python',
                 '--allow-client-device-discovery','--model-path',str(model),'--served-model-name',str(model),
                 '--port','30001','--runtime-dir',str(runtime),'--expected-run-id',run_id,'--output-dir',str(OUT/'performance'),
                 '--timeout-seconds','9000','--total-timeout-seconds','24000']
        for load in ['4096:64','16384:1','16384:8','16384:64']:command+=['--load',load]
        step(command,'native-eight',24150)
        assert step(['python3',str(auditor),'--run',str(OUT/'performance/run.json'),
                     '--analysis-dir',str(OUT/'new-analysis')],'new-eight-analysis',180) in (0,1)
        assert step(['python3','/root/combine_robo_native021.py','--old',str(OUT/'old-analysis/analysis.json'),
            '--new',str(OUT/'new-analysis/analysis.json'),'--old-project',str(OLD/'project'),'--new-project',str(project),
            '--source-zip',str(archive),'--output',str(OUT/'combined-native-matrix.json')],'combined-audit',180)==0
        record['complete']=True;record['combined_native_reports']=12;record['measured_requests']=608
    except BaseException as exc:record['error']=repr(exc)
    finally:
        if run_id is not None and project is not None:
            try:assert step(['bash',str(project/'stop.sh'),'--run-id',run_id],'stop',100)==0
            except BaseException as exc:record['cleanup_error']=repr(exc)
        safe=not alive(43964) and not alive(54510) and (owned_child is None or owned_child.poll() is not None) and ports_clear()
        record['owned_services_cleaned']=safe
        if safe:
            try:
                auk=identity(45258);assert auk['token']==AUK_TOKEN and auk['argv']==AUK_ARGV and auk['state']=='T'
                os.kill(45258,signal.SIGCONT);record['AUK_released']=True
            except BaseException as exc:record['release_error']=repr(exc)
        record.update(state='complete_native_matrix_pending_delivery' if record['complete'] and safe else 'continuation_failed_preserved',ended_utc=now());save()
    entries=[]
    with zipfile.ZipFile('/root/session021-robo-continuation001.zip','x',zipfile.ZIP_DEFLATED) as z:
        for folder,dirs,files in os.walk(OUT,onerror=lambda e:(_ for _ in ()).throw(e)):
            dirs[:]=sorted(d for d in dirs if d not in ('.git','__pycache__'))
            for name in sorted(files):
                p=Path(folder)/name;assert not p.is_symlink();rel=p.relative_to(OUT).as_posix()
                z.write(p,rel);entries.append({'path':rel,'bytes':p.stat().st_size,'sha256':sha(p)})
        z.writestr('MANIFEST.json',json.dumps({'scope':'All bounded continuation files; no failed row removed','files':entries},indent=2))
    print(json.dumps(record),flush=True)


if __name__=='__main__':main()
