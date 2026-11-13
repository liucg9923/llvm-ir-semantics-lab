from pathlib import Path
from irsem.common import read_json
from irsem.tasks import Task,load_tasks

def tasks(root,split):
    root=Path(root)
    if split=='dev':return load_tasks(root,'dev')
    if split!='test':raise ValueError('Unknown split')
    specs=read_json(root/'tasks/v3/manifest.json')['tasks']
    return [Task(root,s) for s in specs]
