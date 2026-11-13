from pathlib import Path
from collections import Counter
import csv,html
from .common import read_json,write_json


def summarize(rows):
    groups={}
    for row in rows: groups.setdefault((row['level'],row['arm']),[]).append(row)
    result=[]
    for (level,arm),group in sorted(groups.items()):
        opportunities=[r for r in group if r['role']=='opportunity']
        result.append({'level':level,'arm':arm,'n':len(group),'statuses':dict(Counter(r['status'] for r in group)),
          'syntax_valid':sum(bool(r['syntax_valid']) for r in group),
          'verified':sum(r['status']=='verified' for r in group),
          'refuted':sum(r['status']=='refuted' for r in group),
          'unchanged':sum(bool(r['unchanged']) for r in group),
          'opportunities':len(opportunities),
          'effective_optimizations':sum(bool(r['effective_optimization']) for r in opportunities)})
    return result


def report(runs,out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    combined=[]; flat=[]; lock=None; code_hash=None
    for run in map(Path,runs):
        meta=read_json(run/'manifest.json')
        if meta['status']!='evaluated': raise ValueError('Cannot report a partially evaluated run')
        if lock is not None and lock!=meta['dataset_sha256']: raise ValueError('Cannot combine different dataset versions')
        lock=meta['dataset_sha256']
        if code_hash is not None and code_hash!=meta.get('evaluation_code_sha256'):
            raise ValueError('Cannot combine runs from different evaluator source versions')
        code_hash=meta.get('evaluation_code_sha256')
        rows=read_json(run/'results.json')
        if len(rows)!=len(meta['items']): raise ValueError('Incomplete result rows')
        label=meta['model']['id'] if meta['model'] else meta['backend']
        for s in summarize(rows): combined.append(dict(s,run=run.name,label=label,mode=meta['mode']))
        for r in rows:
            flat.append({'run':run.name,'label':label,'mode':meta['mode'],**{k:r.get(k) for k in
                ['task_id','level','role','arm','status','syntax_valid','goal_met','effective_optimization','unchanged']}})
    write_json(out/'summary.json',{'dataset_sha256':lock,'groups':combined})
    with (out/'cases.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(flat[0])); w.writeheader(); w.writerows(flat)
    lines=['# 实验结果','', '只将 mode=formal 的 opt/HF 记录作为正式实验；fixture/smoke 记录是评测器检查。',
      'refuted 是已发现反例的比例，不是所有未知候选的真实错误率。每个数值保留分母。','',
      '| 选手/运行 | 模式 | 层级 | 分支 | 合法 IR | 验证通过 | 发现反例 | 有效优化 | 原样返回 |',
      '|---|---|---|---|---:|---:|---:|---:|---:|']
    for s in combined:
        n=s['n']; op=s['opportunities']
        lines.append(f"| {s['label']} ({s['run']}) | {s['mode']} | {s['level']} | {s['arm']} | {s['syntax_valid']}/{n} | {s['verified']}/{n} | {s['refuted']}/{n} | {s['effective_optimizations']}/{op} | {s['unchanged']}/{n} |")
    lines += ['', '全部状态分布见 summary.json；逐题记录见 cases.csv。原始 IR、反例和诊断保存在各运行目录。']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    table=[]
    for s in combined:
        score=s['effective_optimizations']/s['opportunities'] if s['opportunities'] else 0
        shade=f'hsl(180 35% {96-score*35:.0f}%)'
        table.append('<tr>'+''.join('<td>'+html.escape(str(s[k]))+'</td>' for k in ['label','mode','level','arm'])+
          f'<td style="background:{shade}">{s["effective_optimizations"]}/{s["opportunities"]}</td>'+
          '<td>'+html.escape(str(s['statuses']))+'</td></tr>')
    (out/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>IR semantics results</title><style>body{font:16px system-ui;margin:3em;color:#102b40}table{border-collapse:collapse}td,th{border:1px solid #ccd;padding:12px}p{max-width:70em}</style><h1>LLVM IR 变换实验</h1><p>单元格为有效优化数/优化机会数。fixture 和 smoke 均不是正式模型成绩；详细未知、错误和反例分布同时保留。</p><table><tr><th>选手</th><th>模式</th><th>层级</th><th>分支</th><th>有效优化</th><th>全部状态</th></tr>'+''.join(table)+'</table>',encoding='utf-8')
    return combined
