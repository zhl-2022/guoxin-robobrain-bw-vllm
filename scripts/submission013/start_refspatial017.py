"""Import sealed CPU files, then wait for the owned Kimi work."""
from pathlib import Path
import hashlib,json,os,stat,sys,zipfile
archive=Path('/root/session017-refspatial-queue001.zip')
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='b337960b56b5e26e2282db68c2614031357f7167e75b0cc0806e9face602ae5a'
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
