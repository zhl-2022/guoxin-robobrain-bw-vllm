"""Seal complete data, public scorers and existing fixed private project code."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import zipfile


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'dist/session017-refspatial-queue001.zip'
PROJECT = ROOT / 'dist/session017-robo-a1304-project.zip'
COMMIT = 'a1304dad3fe762691735c7fe03beffb8efcffd21'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not PROJECT.exists() and not OUT.exists()
    repo = ROOT / 'deliverables/submission011/repos/robo'
    assert subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD']).decode().strip() == COMMIT
    assert not subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain'])
    subprocess.run(['git', '-C', str(repo), 'archive', '--format=zip', '--output=' + str(PROJECT), COMMIT], check=True)
    lock = {'git_commit': COMMIT, 'sha256': sha(PROJECT), 'bytes': PROJECT.stat().st_size,
            'note': 'Prior frozen source is a backup, not a completed RefSpatial delivery.'}
    rows = []
    data = ROOT / 'datasets/session017/refspatial200-002'
    for directory, dirs, names in os.walk(data, onerror=lambda error: (_ for _ in ()).throw(error)):
        dirs[:] = sorted(d for d in dirs if d != 'raw')
        for name in sorted(names):
            path = Path(directory) / name
            rows.append((path, 'data/' + path.relative_to(data).as_posix()))
    for name in ('Evaluation/summarize_acc.py', 'Evaluation/test_benchmark.py', 'RoboBrain2.5/inference.py'):
        rows.append((ROOT / 'evidence/session017/sources' / name, 'sources/' + name))
    for name in ('evaluate_refspatial017.py', 'run_refspatial_queue017.py'):
        rows.append((ROOT / 'scripts/submission013' / name, 'tools/' + name))
    rows.extend([(ROOT / 'scripts/t02_sglang_bench.py', 'tools/t02_sglang_bench.py'),
                 (ROOT / 'scripts/analyze_sglang_results_004.py', 'tools/analyze_sglang_results_004.py'),
                 (PROJECT, 'robo-project.zip')])
    manifest = []
    with zipfile.ZipFile(OUT, 'x', zipfile.ZIP_DEFLATED) as bundle:
        for path, name in rows:
            assert path.is_file() and not path.is_symlink()
            bundle.write(path, name)
            manifest.append({'path': name, 'bytes': path.stat().st_size, 'sha256': sha(path)})
        raw = (json.dumps(lock, indent=2) + '\n').encode()
        bundle.writestr('project-lock.json', raw)
        manifest.append({'path': 'project-lock.json', 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
        bundle.writestr('MANIFEST.json', json.dumps({'files': manifest}, indent=2))
    with zipfile.ZipFile(OUT) as bundle:
        assert bundle.testzip() is None and len(bundle.namelist()) == len(set(bundle.namelist())) == len(manifest) + 1
    receipt = dict(lock, queue_archive=str(OUT), queue_archive_sha256=sha(OUT), queue_archive_bytes=OUT.stat().st_size,
                   files=len(manifest), GPU_started=False, queue_started=False, submitted=False)
    (ROOT / 'evidence/session017/refspatial-queue-package.json').write_text(json.dumps(receipt, indent=2) + '\n')
    bootstrap = '''"""Import sealed CPU files, then wait for the owned Kimi work."""
from pathlib import Path
import hashlib,json,os,stat,sys,zipfile
archive=Path('/root/session017-refspatial-queue001.zip')
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='QUEUE_HASH'
stage=Path('/root/private_data/guoxin-session017/refspatial-stage001')
stage.mkdir(parents=True,exist_ok=False)
with zipfile.ZipFile(archive) as bundle:
 assert bundle.testzip() is None
 manifest=json.loads(bundle.read('MANIFEST.json'))['files']
 assert len(bundle.namelist())==len(set(bundle.namelist()))==len(manifest)+1
 assert set(bundle.namelist())=={r['path'] for r in manifest}|{'MANIFEST.json'}
 for row in manifest:
  name=row['path'];target=stage/name
  assert not Path(name).is_absolute() and target.resolve().is_relative_to(stage.resolve())
  assert not stat.S_ISLNK(bundle.getinfo(name).external_attr>>16)
  data=bundle.read(name)
  assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
  target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as stream:stream.write(data)
(stage/'IMPORT-READY.json').write_text(json.dumps({'ready':True,'files':len(manifest),'GPU_started':False}))
os.execv(sys.executable,[sys.executable,'-u',str(stage/'tools/run_refspatial_queue017.py')])
'''.replace('QUEUE_HASH', receipt['queue_archive_sha256'])
    (ROOT / 'scripts/submission013/start_refspatial017.py').write_text(bootstrap, encoding='utf-8', newline='\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
