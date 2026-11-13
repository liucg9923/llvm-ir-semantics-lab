"""Check a complete evidence archive without extracting it to the filesystem."""
import argparse,hashlib,json,tarfile
from pathlib import PurePosixPath
p=argparse.ArgumentParser();p.add_argument('archive');a=p.parse_args()
with tarfile.open(a.archive) as tar:
    members={m.name:m for m in tar.getmembers()}
    if len(members)!=len(tar.getmembers()):raise SystemExit('Duplicate archive member')
    for name,m in members.items():
        path=PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or not m.isfile():raise SystemExit('Unexpected archive member: '+name)
    checks=json.load(tar.extractfile('FILES.sha256.json'))
    for name,expected in checks.items():
        if name not in members:raise SystemExit('Missing archive member: '+name)
        stream=tar.extractfile(name);h=hashlib.sha256()
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
        if h.hexdigest()!=expected:raise SystemExit('Checksum mismatch: '+name)
    if set(members)!=set(checks)|{'FILES.sha256.json'}:raise SystemExit('Unlisted archive files')
print(f'PASS: {len(checks)} files verified; no extraction performed.')
