"""Run the queued350-image benchmark after the owned Kimi controller finishes.

Never power off the Notebook. Never stop another model or overwrite a run.
"""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import uuid
import zipfile

BASE = Path('/root/private_data/guoxin-session010')
STAGE = Path('/root/private_data/guoxin-session014/robo-spatial-stage015')
OUT = Path('/root/private_data/guoxin-session014/robo-spatial-full015')
KIMI = Path('/root/private_data/guoxin-session013/whole-attempt2')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--wait-for-kimi',action='store_true')
    args = ap.parse_args()
    assert Path('/dev/kfd').exists()
    if args.wait_for_kimi:
        deadline = time.monotonic() + 21600
        while True:
            final = KIMI / 'run-final.json'
            archive = Path('/root/session013-kimi-whole-attempt2.zip')
            cmdline = Path('/proc/653/cmdline')
            still_owned = cmdline.exists() and 'kimi_mmmu_full014.py' in cmdline.read_text(errors='replace')
            if final.is_file() and archive.is_file() and not still_owned:
                result = json.loads(final.read_text())
                assert result.get('owned_service_stopped'), 'Kimi did not confirm cleanup'
                with zipfile.ZipFile(archive) as bundle:
                    assert bundle.testzip() is None
                print(json.dumps({'previous_controller_finished':True,
                                  'kimi_complete':result.get('complete'),
                                  'kimi_archive_sha256':sha(archive)}),flush=True)
                if result.get('complete'):
                    with Path('/root/kimi-full015-score.log').open('xb') as log:
                        scored = subprocess.run([sys.executable,str(STAGE / 'tools/score_kimi_full015.py')],
                                                stdout=log,stderr=subprocess.STDOUT,timeout=600)
                    print(json.dumps({'kimi_CPU_score_exit':scored.returncode}),flush=True)
                break
            assert time.monotonic() < deadline, 'Existing Kimi job still active; leave it untouched'
            print(json.dumps({'waiting_for_owned_kimi_controller':True,
                              'UTC':dt.datetime.now(dt.timezone.utc).isoformat()}),flush=True)
            time.sleep(30)
    for port in (30000,30001,30002,30119,30129,30139):
        with socket.socket() as sock:
            sock.settimeout(.5)
            assert sock.connect_ex(('127.0.0.1',port)) != 0, ('Existing service left untouched',port)
    OUT.mkdir(parents=True,exist_ok=False)
    project = OUT / 'project'
    shutil.copytree(BASE / 'projects/robo', project,
                    ignore=shutil.ignore_patterns('.git','__pycache__','runtime','runtime-inherited-history'))
    task = project / 'tasks/robobrain-bw-vllm'
    driver = project / 'scripts/recon2reason_runtime.py'
    run_id = uuid.uuid4().hex
    env = os.environ.copy()
    env.update(ROBOBRAIN_MAX_RUNTIME_SECONDS='9000',ROBOBRAIN_LOAD_TIMEOUT='1800',
               ROBOBRAIN_MAX_NUM_SEQS='4', PYTHONPATH=str(project / 'scripts'),
               HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    record = {'started_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
              'run_id':run_id,'model_revision':'7ae187cc62e45cfa1c5904903a8f017f11b2037b',
              'dataset':'RoboSpatial-Home complete350 RGB',
              'phases':{},'source_sha256':sha(Path(__file__)),
              'driver_sha256':sha(driver),'instance_shutdown_requested':False,
              'submitted':False,'official_acceptance':False}
    shutil.copyfile(Path(__file__),OUT / 'executed-controller.py')
    (OUT / 'run-start.json').write_text(json.dumps(record,indent=2))
    def step(argv,label,timeout):
        with (OUT / (label + '.log')).open('xb') as log:
            child = subprocess.Popen(argv,env=env,stdout=log,stderr=subprocess.STDOUT)
            try:
                code = child.wait(timeout=timeout)
            except BaseException:
                child.terminate()
                try:
                    child.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
                raise
        record['phases'][label] = code
        print(json.dumps({'phase':label,'exit':code}),flush=True)
        return code
    try:
        assert step(['bash',str(task / 'run.sh'),'--run-id',run_id],'launch',2100) == 0
        step([sys.executable,str(STAGE / 'tools/evaluate_robo_spatial015.py'),
              '--data',str(STAGE / 'data'),'--sources',str(STAGE / 'sources'),
              '--output',str(OUT / 'evaluation')],'evaluation',7200)
    except BaseException as exc:
        record['error'] = repr(exc)
    finally:
        try:
            step([sys.executable,str(driver),'stop','--task-dir',str(task),'--run-id',run_id],'stop',90)
        except BaseException as exc:
            record['cleanup_error'] = repr(exc)
        with socket.socket() as sock:
            record['owned_service_stopped'] = sock.connect_ex(('127.0.0.1',30001)) != 0
        score = OUT / 'evaluation/verify_result.json'
        if score.is_file():
            record['accuracy_result'] = json.loads(score.read_text())
        if (task / 'runtime').is_dir():
            shutil.copytree(task / 'runtime',OUT / 'runtime-final')
        record['ended_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
        (OUT / 'run-final.json').write_text(json.dumps(record,indent=2))
        files = []
        with zipfile.ZipFile('/root/session014-robo-spatial-full015.zip','x',zipfile.ZIP_DEFLATED) as bundle:
            for folder,dirs,names in os.walk(OUT,onerror=lambda e:(_ for _ in ()).throw(e)):
                dirs[:] = sorted(d for d in dirs if d != '__pycache__')
                for name in sorted(names):
                    path = Path(folder) / name
                    assert not path.is_symlink()
                    rel = path.relative_to(OUT).as_posix()
                    bundle.write(path,rel)
                    files.append({'path':rel,'bytes':path.stat().st_size,'sha256':sha(path)})
            bundle.writestr('MANIFEST.json',json.dumps({'files':files},indent=2))
        print(json.dumps(record),flush=True)


if __name__ == '__main__':
    main()
