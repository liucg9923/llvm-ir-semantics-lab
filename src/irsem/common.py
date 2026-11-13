from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib, json, os, signal, subprocess, tempfile, time


def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def text_digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=path.parent,delete=False) as f:
        json.dump(value,f,ensure_ascii=False,indent=2); f.write('\n'); temp=f.name
    os.replace(temp,path)


@dataclass
class ProcessResult:
    command: list[str]
    returncode: int | None
    stdout: str
    stderr: str
    seconds: float
    timed_out: bool=False
    truncated: bool=False

    def as_dict(self): return asdict(self)


def run_process(command, timeout=60, cwd=None) -> ProcessResult:
    """No shell; kill the complete process group on timeout; bounded log reads."""
    command=[str(x) for x in command]; start=time.monotonic()
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        try:
            p=subprocess.Popen(command,stdout=out,stderr=err,cwd=cwd,start_new_session=True)
        except OSError as e:
            return ProcessResult(command,None,'',str(e),time.monotonic()-start)
        timed_out=False
        try: p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out=True
            try: os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            p.wait()
        limit=1024*1024
        truncated=out.tell()>limit or err.tell()>limit
        out.seek(0); err.seek(0)
        return ProcessResult(command,p.returncode,out.read(limit).decode(errors='replace'),
            err.read(limit).decode(errors='replace'),time.monotonic()-start,timed_out,truncated)


def source_digest(root):
    root=Path(root)
    return text_digest(str([(str(p.relative_to(root)),digest(p)) for p in sorted((root/'src').rglob('*.py'))]))
