"""Reproducible descriptive figures from collected experiment data, without mock values."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import os
font_dir=Path(os.environ.get("IRSEM_REPORT_FONT_DIR",Path.cwd()/".cache/report-fonts"))
for font_name in ["NotoSansSC-Regular.ttf","NotoSansSC-Bold.ttf"]:
    font_path=font_dir/font_name
    if not font_path.is_file(): raise FileNotFoundError("Run the report-font setup before rendering Chinese labels")
    font_manager.fontManager.addfont(str(font_path))
from matplotlib.colors import LinearSegmentedColormap,ListedColormap
from matplotlib.patches import Patch

mpl.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Noto Sans SC','DejaVu Sans','sans-serif'],
 'font.size':15,'axes.titlesize':18,'axes.labelsize':15,'svg.fonttype':'none','pdf.fonttype':42,
 'axes.spines.top':False,'axes.spines.right':False,'legend.frameon':False,'axes.unicode_minus':False})


def export(fig,stem,axes,audit=None,excluded=()):
    fig.canvas.draw(); w,h=fig.get_size_inches()*72
    renderer=fig.canvas.get_renderer()
    for axis in axes:
        labels=[t for t in axis.get_xticklabels() if t.get_visible() and t.get_text()]
        bounds=[t.get_window_extent(renderer) for t in labels]
        if any(right.x0 < left.x1 for left,right in zip(bounds,bounds[1:])):
            raise RuntimeError('Adjacent x labels overlap')
    boxes=[]
    for ax in axes:
        b=ax.get_position();boxes.append({'left_pt':b.x0*w,'bottom_pt':b.y0*h,'width_pt':b.width*w,'height_pt':b.height*h,'top_pt':b.y1*h})
    if len(boxes)>1:
        for key in ['width_pt','height_pt','bottom_pt','top_pt']:
            if max(b[key] for b in boxes)-min(b[key] for b in boxes)>1.5:raise RuntimeError('Comparable panels misaligned: '+key)
    Path(str(stem)+'.layout.json').write_text(json.dumps({'boxes':boxes,'tolerance_pt':1.5,'status':'pass' if len(boxes)>1 else 'not_applicable'},indent=2)+'\n')
    if audit:audit(fig,stem,excluded)
    fig.savefig(str(stem)+'.svg')
    fig.savefig(str(stem)+'.pdf')
    fig.savefig(str(stem)+'.png',dpi=300)
    plt.close(fig)


def build_figures(analysis_dir,out_dir,audit=None):
    analysis=Path(analysis_dir);out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
    data=json.loads((analysis/'summary.json').read_text());roles=data['run_roles']
    if data['compiler_model'].get('scored'): raise ValueError('Update figure mapping to include measured compiler-model results; never silently omit them')
    levels=['L0','L1','L2'];labels=['L0\n局部计算','L1\n控制与依赖','L2\n内存与别名']
    runs=[roles['baseline'],roles['qwen'],None,roles['identity']]
    names=['LLVM opt\n17.0.6','Qwen2.5-Coder\n7B-Instruct','LLM Compiler 7B\n待授权','原样返回\n控制组']
    cmap=LinearSegmentedColormap.from_list('teal',['#f4faf9','#7fc7c1','#076d74']);cmap.set_bad('#e6e8eb')
    fig,axs=plt.subplots(1,3,figsize=(15.5,7.3),sharey=True)
    fig.subplots_adjust(left=.18,right=.92,bottom=.22,top=.80,wspace=.16)
    fig.suptitle('合法、正确与有效优化分别统计',fontsize=23,y=.95,color='#102b40')
    source=[]
    for ax,letter,field,denom,title in zip(axs,['a','b','c'],['syntax_valid','verified','effective'],['n','n','opportunity_n'],['合法 IR（每类 8 题）','语义验证通过（每类 8 题）','有效优化（每类 4 个机会）']):
        values=np.full((4,3),np.nan);texts={}
        for i,run in enumerate(runs):
            for j,level in enumerate(levels):
                if run is None:texts[i,j]='待授权';continue
                row=next(s for s in data['summary'] if s['run']==run and s['arm']=='initial' and s['level']==level)
                n=row[denom];value=row[field]
                if n<=0:raise ValueError('Empty measured denominator')
                values[i,j]=value/n;texts[i,j]=f'{value}/{n}'
                source.append({'panel':letter,'run':run,'level':level,'numerator':value,'denominator':n})
        image=ax.imshow(np.ma.masked_invalid(values),cmap=cmap,vmin=0,vmax=1,aspect='auto',interpolation='nearest')
        for (i,j),text in texts.items():
            ax.text(j,i,text,ha='center',va='center',fontsize=20,color='white' if np.isfinite(values[i,j]) and values[i,j]>.65 else '#243746')
        ax.set_xticks(range(3),labels,fontsize=14);ax.tick_params(axis='x',length=0,pad=12)
        ax.set_yticks(range(4),names,fontsize=14);ax.tick_params(axis='y',length=0,pad=12)
        ax.set_xticks(np.arange(-.5,3,1),minor=True);ax.set_yticks(np.arange(-.5,4,1),minor=True)
        ax.grid(which='minor',color='white',linewidth=2);ax.tick_params(which='minor',bottom=False,left=False)
        for spine in ax.spines.values():spine.set_visible(False)
        ax.set_title(title,pad=18,color='#102b40',fontsize=16)
        ax.annotate(letter,xy=(0,1),xycoords='axes fraction',xytext=(-22,16),textcoords='offset points',ha='left',va='bottom',fontweight='bold',fontsize=19)
    for ax in axs[1:]: ax.tick_params(axis='y',labelleft=False)
    cax=fig.add_axes([.945,.22,.014,.58]);cb=fig.colorbar(image,cax=cax,ticks=[0,.25,.5,.75,1]);cb.ax.set_yticklabels(['0%','25%','50%','75%','100%']);cb.ax.tick_params(labelsize=12);cb.ax.set_title('比例',fontsize=13,pad=12)
    fig.text(.18,.065,'前两列各统计每类 8 道任务；第三列仅统计每类 4 道优化机会题。Meta 组未运行，不计零分。',fontsize=12,color='#526675')
    fig.text(.18,.025,'原样返回可以保持语义，但不构成有效优化。仅覆盖本项目的 L0—L2 子集。',fontsize=12,color='#526675')
    export(fig,out/'correctness_and_optimization',list(axs),audit,[cax])
    Path(out/'correctness_source_data.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n')

    # A matched-case display, not a comparison of 24 initial cases with 12 revised cases.
    import csv
    with (analysis/'paired_feedback.csv').open() as f:paired=list(csv.DictReader(f))
    ids=list(dict.fromkeys(r['task_id'] for r in paired))
    if len(ids)!=12:raise ValueError('Expected the predeclared 12 matched tasks')
    initial={r['task_id']:(r['initial_status'],r['initial_effective']=='True') for r in paired}
    repairs={(r['task_id'],r['arm']):(r['revised_status'],r['revised_effective']=='True') for r in paired}
    categories={
      'verified':(0,'通过','#a6d9ce'),'refuted':(1,'反例','#efa6a4'),
      'invalid_ir':(2,'格式','#e7cf8e'),'format_error':(2,'格式','#e7cf8e'),
      'contract_violation':(3,'约束','#c6b5dd'),
      'unknown':(4,'未知','#c8d4e2'),'tested_only':(4,'未知','#c8d4e2'),'verification_only':(4,'未知','#c8d4e2'),
      'generation_error':(5,'生成','#edc6a1'),
      'tool_error':(6,'异常','#d5d7da'),'execution_error':(6,'异常','#d5d7da'),'oracle_conflict':(6,'异常','#d5d7da')}
    colors=['#a6d9ce','#efa6a4','#e7cf8e','#c6b5dd','#c8d4e2','#edc6a1','#d5d7da']
    matrix=np.zeros((12,3));cell_text={};seen={};sources=[]
    for i,id in enumerate(ids):
        conditions=[initial[id],repairs[id,'self_review'],repairs[id,'tool_feedback']]
        for j,(status,effective) in enumerate(conditions):
            if status not in categories:raise ValueError('Unknown result category: '+status)
            index,label,color=categories[status];matrix[i,j]=index;cell_text[i,j]=label+('*' if effective else '')
            seen[index]=(label,color);sources.append({'task_id':id,'condition':j,'status':status,'effective':effective})
    fig,ax=plt.subplots(figsize=(12,8))
    fig.subplots_adjust(left=.30,right=.95,bottom=.20,top=.86)
    ax.imshow(matrix,cmap=ListedColormap(colors),vmin=-.5,vmax=6.5,aspect='auto',interpolation='nearest')
    for (i,j),label in cell_text.items():ax.text(j,i,label,ha='center',va='center',fontsize=13,color='#243746')
    ax.set_xticks(range(3),['首次输出','自行复查','工具反馈'],fontsize=16);ax.xaxis.tick_top();ax.tick_params(axis='x',length=0,pad=12)
    ax.set_yticks(range(12),ids,fontsize=12);ax.tick_params(axis='y',length=0,pad=12)
    ax.set_xticks(np.arange(-.5,3,1),minor=True);ax.set_yticks(np.arange(-.5,12,1),minor=True)
    ax.grid(which='minor',color='white',linewidth=1.5);ax.tick_params(which='minor',bottom=False,left=False)
    for spine in ax.spines.values():spine.set_visible(False)
    fig.suptitle('Qwen：同一批 12 道题的修订结果',fontsize=22,y=.975,color='#102b40')
    handles=[Patch(facecolor=color,label=label) for _,(label,color) in sorted(seen.items())]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.61,.075),ncol=min(4,len(handles)),fontsize=12)
    fig.text(.30,.035,'* 表示同时完成预设优化目标；两种修订都从同一首次输出出发，各一次生成。',fontsize=11,color='#526675')
    export(fig,out/'paired_feedback', [ax],audit)
    (out/'paired_feedback_source_data.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
    (out/'FIGURE_NOTES.md').write_text('''# Figure notes

These are descriptive counts from a fixed authored task set, not estimates from random samples of all programs. Each formal task has one greedy candidate per condition. No confidence intervals or p-values are claimed. The initial comparison contains 24 tasks and 12 optimization opportunities per measured competitor/control. Feedback contains the same predeclared 12 tasks in each condition, with 6 optimization opportunities.

The Meta row is explicitly unmeasured and masked, not assigned zero. Failed, unknown and unsupported outputs remain in the denominators and in the full data tables. The identity control is not an additional language model.

The three main panels have distinct roles: syntax/SSA legality is the entry check; semantic validation establishes correctness within the supported domain; verified goal completion establishes useful optimization. The first two panels use all tasks, while the third uses only the predeclared opportunity tasks. The paired display shows every predeclared feedback task, including regressions and unchanged cases. All data are derived from summary.json and paired_feedback.csv; no observations are removed for layout.

Exports are sized for classroom slides and repository reports, not a specific journal submission. Python/Matplotlib is the sole drawing backend. SVG/PDF retain text; PNG is provided for slide insertion. Every font is at least 11 pt at the native export size. In-cell labels are intentional and constitute the primary count/status evidence.
''')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--analysis',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    build_figures(a.analysis,a.out)
