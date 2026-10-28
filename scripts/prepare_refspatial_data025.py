"""Prepare the exact complete public RefSpatial200 data without network or GPU."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'publisher021/refspatial200-reprodata.zip'
ARCHIVE_SHA256 = 'e4fdf64db04eedfb61a2f6847f9e12f0329e1034af42e8785edbce45c0583bde'
DEFAULT_DATA = ROOT / 'runtime/refspatial025/data'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_name(name):
    path = PurePosixPath(name)
    assert name and path.as_posix() == name and not path.is_absolute()
    assert '..' not in path.parts and '\\' not in name and ':' not in name
    return name


def prepare():
    assert digest(ARCHIVE.read_bytes()) == ARCHIVE_SHA256
    with zipfile.ZipFile(ARCHIVE) as bundle:
        names = bundle.namelist()
        assert len(names) == len(set(names)) == 404
        assert bundle.testzip() is None
        rows = json.loads(bundle.read('DATA-MANIFEST.json'))['files']
        assert len(rows) == 403 and len({row['path'] for row in rows}) == 403
        assert set(names) == {row['path'] for row in rows} | {'DATA-MANIFEST.json'}
        for item in bundle.infolist():
            safe_name(item.filename)
            assert not item.is_dir() and not stat.S_ISLNK(item.external_attr >> 16)
        payloads = {}
        for row in rows:
            raw = bundle.read(safe_name(row['path']))
            assert len(raw) == row['bytes'] and digest(raw) == row['sha256']
            payloads[row['path']] = raw
    target = DEFAULT_DATA
    assert not target.is_symlink() and target.resolve().is_relative_to((ROOT / 'runtime').resolve())
    if target.exists():
        actual = set()
        def scan_error(error):
            raise error
        import os
        for folder, dirs, files in os.walk(target, onerror=scan_error):
            for name in dirs + files:
                assert not (Path(folder) / name).is_symlink()
            actual.update((Path(folder) / name).relative_to(target).as_posix() for name in files)
        assert actual == set(payloads), 'Existing data tree contains missing or extra files'
        for name, raw in payloads.items():
            assert (target / name).read_bytes() == raw, ('Existing data changed', name)
    else:
        target.mkdir(parents=True, exist_ok=False)
        for name, raw in payloads.items():
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(raw)
    return target


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps({'data': str(prepare()), 'files_verified': 403,
                      'samples': 200, 'network_requests': 0, 'GPU_requests': 0}))
