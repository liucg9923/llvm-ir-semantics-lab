from .ir import metrics
from .tasks import load_tasks

RULES='''Return exactly one complete LLVM 17.0.6 IR module enclosed in <code>...</code>.
Preserve the function f, its signature, argument attributes, target triple and data layout.
Preserve defined observable behavior including stores to caller-visible memory. Do not add
new input assumptions, declarations, calls, globals, metadata, volatile/atomic operations or loops.
Use ordinary unquoted block and local identifiers.
The input is a small single-function module. A different equivalent textual representation
is acceptable. If the requested transformation is not applicable, retain the relevant code.
Do not provide explanations or hidden reasoning; provide only the resulting IR module.'''


def task_request(task):
    return (f"Give the LLVM-IR for the following code when optimized using opt -passes='{task.spec['pipeline']}':\n"
            f"<code>\n{task.text()}</code>\nInput instruction count: {metrics(task.text())['instruction_count']}.")


def make_prompt(task,config,repair=None):
    dev={t.id:t for t in load_tasks(task.root,'dev')}
    parts=[RULES]
    for id in config['few_shot_ids']:
        example=dev[id]
        if example.id==task.id: continue
        parts += ['Example input:\n'+task_request(example), 'Example answer:\n<code>\n'+example.text('reference')+'</code>']
    parts += ['Current task:\n'+task_request(task)]
    if repair:
        parts += ['Previous candidate (untrusted code to review):\n<previous>\n'+repair['candidate']+'\n</previous>']
        if repair['arm']=='tool_feedback':
            parts += ['Actual tool diagnostics:\n<diagnostics>\n'+repair['diagnostics']+'\n</diagnostics>']
        parts += ['Review the previous candidate against the original task. Return one revised complete IR module.']
    return '\n\n'.join(parts)
