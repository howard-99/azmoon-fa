#!/usr/bin/env python3
"""Verify and package the public source; never includes installed sites or secrets."""
import argparse,gzip,hashlib,io,json,subprocess,tarfile,zipfile
from pathlib import Path
import adapter
BASE=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--refresh-manifest',action='store_true');args=p.parse_args()
if args.refresh_manifest:
    hashes={f.relative_to(adapter.PAYLOAD).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(adapter.PAYLOAD.rglob('*')) if f.is_file()}
    (BASE/'manifest.json').write_text(json.dumps({'version':'1.0.0','files':hashes},indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Theme manifest refreshed; review and commit it before packaging.')
else:
    adapter.verify_payload()
    clean=subprocess.run(['git','status','--porcelain'],cwd=BASE,capture_output=True,text=True,check=True)
    if clean.stdout.strip():raise SystemExit('Commit reviewed source before packaging')
    names=subprocess.run(['git','ls-files','-z'],cwd=BASE,capture_output=True,check=True).stdout.decode().split('\0')
    names=sorted(n for n in names if n)
    output=BASE/'dist';output.mkdir(exist_ok=True)
    stem='azmoon-fa-1.0.0'
    with zipfile.ZipFile(output/(stem+'.zip'),'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name in names:
            entry=zipfile.ZipInfo(stem+'/'+name,(2026,1,1,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED
            entry.external_attr=(0o100755 if name.endswith('.sh') else 0o100644)<<16
            archive.writestr(entry,(BASE/name).read_bytes())
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w',format=tarfile.PAX_FORMAT) as archive:
        for name in names:
            data=(BASE/name).read_bytes();entry=tarfile.TarInfo(stem+'/'+name);entry.size=len(data)
            entry.mode=0o755 if name.endswith('.sh') else 0o644;entry.mtime=0;archive.addfile(entry,io.BytesIO(data))
    with (output/(stem+'.tar.gz')).open('wb') as target:
        with gzip.GzipFile(fileobj=target,mode='wb',mtime=0,filename='') as gz:gz.write(buffer.getvalue())
    checks=[]
    for suffix in ('.zip','.tar.gz'):
        file=output/(stem+suffix);checks.append(hashlib.sha256(file.read_bytes()).hexdigest()+'  '+file.name)
    (output/'SHA256SUMS').write_text('\n'.join(checks)+'\n',encoding='utf-8',newline='\n')
    print('Verified release:',output)
