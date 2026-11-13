from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from .common import digest,read_json,write_json,text_digest


@dataclass(frozen=True)
class Task:
    root: Path
    spec: dict
    @property
    def id(self): return self.spec['id']
    def file(self,name): return self.root/self.spec['directory']/(name+'.ll')
    def text(self,name='source'): return self.file(name).read_text(encoding='utf-8')


def load_tasks(root, split=None):
    root=Path(root).resolve()
    data=read_json(root/'tasks/manifest.json')
    if data.get('schema_version')!=1: raise ValueError('Unsupported task manifest')
    ids=set(); result=[]
    for spec in data['tasks']:
        if spec['id'] in ids: raise ValueError('Duplicate task id')
        ids.add(spec['id'])
        task=Task(root,spec)
        for name in ('source','reference','mutant'):
            file=task.file(name).resolve()
            if not file.is_relative_to(root/'tasks') or not file.is_file():
                raise ValueError(f'Missing or escaping task path: {task.id}/{name}')
        if split is None or spec['split']==split: result.append(task)
    return result


def snapshot(root):
    root=Path(root).resolve()
    paths=[root/'tasks/manifest.json',root/'configs/experiment.json',root/'configs/models.json']
    for task in load_tasks(root): paths += [task.file(n) for n in ('source','reference','mutant')]
    return {str(p.relative_to(root)):digest(p) for p in sorted(paths)}


def freeze(root):
    entries=snapshot(root)
    lock={'schema_version':1,'files':entries,'sha256':text_digest(str(sorted(entries.items()))),
          'status':'frozen_content_only_not_proof_of_correctness'}
    write_json(Path(root)/'tasks/dataset.lock.json',lock)
    return lock


def check_lock(root):
    path=Path(root)/'tasks/dataset.lock.json'
    if not path.exists(): raise ValueError('Dataset not frozen: run irsem freeze after review')
    lock=read_json(path)
    now=snapshot(root)
    if now!=lock['files'] or text_digest(str(sorted(now.items())))!=lock['sha256']:
        raise ValueError('Dataset/config changed since freeze; do not mix results across versions')
    return lock
