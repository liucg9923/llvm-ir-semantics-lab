"""V3 figures: coverage, semantic outcome and useful optimization remain distinct."""
from pathlib import Path
import argparse,json
import numpy as np
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap,ListedColormap
from matplotlib.patches import Patch
from plot_campaign import export
for name in ['NotoSansSC-Regular.ttf','NotoSansSC-Bold.ttf']:
 font_manager.fontManager.addfont(str(Path('.cache/report-fonts')/name))
mpl.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Noto Sans SC','DejaVu Sans'],'font.size':13,'svg.fonttype':'none','pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False,'legend.frameon':False})
CATS={
 'verified':(0,'通过','#a6d9ce'),'refuted':(1,'反例','#efa6a4'),
 'format_error':(2,'格式/IR','#e7cf8e'),'invalid_ir':(2,'格式/IR','#e7cf8e'),
 'interface_mismatch':(3,'接口/范围','#c6b5dd'),'unsupported_ir':(3,'接口/范围','#c6b5dd'),'unproved_input_assumption':(3,'接口/范围','#c6b5dd'),
 'unknown':(4,'未知/异常','#c8d4e2'),'tested_only':(4,'未知/异常','#c8d4e2'),'verification_only':(4,'未知/异常','#c8d4e2'),'verifier_unsupported':(4,'未知/异常','#c8d4e2'),
 'tool_error':(4,'未知/异常','#c8d4e2'),'execution_error':(4,'未知/异常','#c8d4e2'),'oracle_conflict':(4,'未知/异常','#c8d4e2'),
 'generation_error':(5,'生成失败','#edc6a1')}
COLORS=['#a6d9ce','#efa6a4','#e7cf8e','#c6b5dd','#c8d4e2','#edc6a1']
def build(analysis,out,audit=None):
 analysis=Path(analysis);out=Path(out);out.mkdir(parents=True,exist_ok=True);data=json.loads((analysis/'summary.json').read_text())
 names=['LLVM opt\n17.0.6','LLM Compiler\n7B-FTD / F16','Qwen2.5-Coder\n7B-Instruct','原样返回\n控制组'];models=['opt','compiler-ftd','qwen','identity'];levels=['L0','L1','L2']
 fig,axs=plt.subplots(1,4,figsize=(15.5,7.6),sharey=True);fig.subplots_adjust(left=.18,right=.92,bottom=.23,top=.78,wspace=.16)
 fig.suptitle('V3：先看验证覆盖，再看语义与优化',fontsize=23,y=.95,color='#102b40')
 cmap=LinearSegmentedColormap.from_list('teal',['#f4faf9','#7fc7c1','#076d74']);source=[]
 for ax,letter,field,denom,title in zip(axs,'abcd',['syntax_valid','semantic_attempted','verified','effective'],['n','n','n','opportunity_n'],['合法 IR\n每类 6 题','进入语义验证\n每类 6 题','验证通过\n每类 6 题','有效优化\n每类 3 个机会']):
  values=np.zeros((4,3));labels={}
  for i,model in enumerate(models):
   for j,level in enumerate(levels):
    r=next(x for x in data['summary'] if x['model']==model and x['level']==level);assert r[denom]>0
    values[i,j]=r[field]/r[denom];labels[i,j]=f"{r[field]}/{r[denom]}";source.append({'panel':letter,'model':model,'level':level,'numerator':r[field],'denominator':r[denom]})
  im=ax.imshow(values,cmap=cmap,vmin=0,vmax=1,aspect='auto',interpolation='nearest')
  for (i,j),s in labels.items():ax.text(j,i,s,ha='center',va='center',fontsize=18,color='white' if values[i,j]>.65 else '#243746')
  ax.set_xticks(range(3),levels,fontsize=14);ax.set_yticks(range(4),names,fontsize=13);ax.tick_params(length=0,pad=10)
  ax.set_xticks(np.arange(-.5,3,1),minor=True);ax.set_yticks(np.arange(-.5,4,1),minor=True);ax.grid(which='minor',color='white',linewidth=2);ax.tick_params(which='minor',bottom=False,left=False)
  for spine in ax.spines.values():spine.set_visible(False)
  ax.set_title(title,fontsize=15,pad=18,color='#102b40');ax.annotate(letter,xy=(0,1),xycoords='axes fraction',xytext=(-18,16),textcoords='offset points',fontsize=18,fontweight='bold',va='bottom')
 for ax in axs[1:]:ax.tick_params(axis='y',labelleft=False)
 cax=fig.add_axes([.945,.23,.014,.55]);cb=fig.colorbar(im,cax=cax,ticks=[0,.5,1]);cb.ax.set_yticklabels(['0%','50%','100%']);cb.ax.tick_params(labelsize=12)
 fig.text(.18,.12,'L0：局部计算；L1：控制与依赖；L2：内存与别名。每款模型在 18 道新任务上各生成一次。',fontsize=12,color='#526675')
 fig.text(.18,.075,'进入验证、验证通过和完成优化是不同指标；未知与接口失败不能当作已证语义错误。',fontsize=12,color='#526675')
 fig.text(.18,.03,'社区 FTD 使用 llama.cpp；Qwen 使用 Transformers。两者均为 F16/FP16，不能据此隔离专用训练的因果效果。',fontsize=11,color='#526675')
 export(fig,out/'coverage_correctness_optimization',list(axs),audit,[cax]);(out/'primary_source_data.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n')

 if all(any(r['model']==m and r['arm']=='legacy' for r in data['development_contrasts']) for m in ['compiler-ftd','qwen']):
  fig,axs=plt.subplots(1,2,figsize=(13.5,7),sharey=True);fig.subplots_adjust(left=.09,right=.97,bottom=.27,top=.80,wspace=.16)
  seen=set();sources=[]
  for ax,letter,model,title in zip(axs,'ab',['compiler-ftd','qwen'],['LLM Compiler 7B-FTD','Qwen2.5-Coder-7B-Instruct']):
   for x,arm in enumerate(['legacy',data['selected_arm_by_model'][model]]):
    r=next(z for z in data['development_contrasts'] if z['model']==model and z['arm']==arm);counts=[0]*6
    for status,n in r['statuses'].items():counts[CATS[status][0]]+=n
    bottom=0
    for index,n in enumerate(counts):
     if not n:continue
     ax.bar(x,n,bottom=bottom,width=.55,color=COLORS[index],edgecolor='white',linewidth=1);ax.text(x,bottom+n/2,str(n),ha='center',va='center',fontsize=16,color='#243746');bottom+=n;seen.add(index)
    ax.text(x,-.9,f"旧准入：{r['legacy_admission']}/6",ha='center',va='top',fontsize=12,color='#526675')
    sources.append({'model':model,'arm':arm,**r})
   ax.set_ylim(0,6.5);ax.set_yticks(range(7));ax.set_xticks([0,1],['旧多示例提示','经预检的最终接口'],fontsize=14);ax.tick_params(axis='x',length=0,pad=10);ax.set_xlim(-.65,1.65)
   ax.set_title(title,fontsize=17,pad=20,color='#102b40');ax.annotate(letter,xy=(0,1),xycoords='axes fraction',xytext=(-18,14),textcoords='offset points',fontsize=18,fontweight='bold',va='bottom')
  axs[0].set_ylabel('开发题数量（每种提示 6 题）',fontsize=13)
  fig.suptitle('开发集配对诊断：旧提示与最终接口',fontsize=21,y=.95,color='#102b40')
  legend_names=['通过','反例','格式/IR','接口/范围','未知/异常','生成失败']
  fig.legend(handles=[Patch(facecolor=COLORS[i],label=legend_names[i]) for i in sorted(seen)],loc='lower center',bbox_to_anchor=(.53,.07),ncol=min(6,len(seen)),fontsize=12)
  fig.text(.09,.025,'柱内是 V3 语义评测结果；柱下“旧准入”只表示同一候选能否通过旧结构检查。开发题不计正式成绩；中间方案另见完整表。',fontsize=11,color='#526675')
  export(fig,out/'development_prompt_contrast',list(axs),audit);(out/'development_source_data.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
 if data['hint_runs']:
  import csv
  with (analysis/'paired_hints.csv').open() as f:paired=list(csv.DictReader(f))
  ids=list(dict.fromkeys(r['task_id'] for r in paired));assert len(ids)==6
  fig,axs=plt.subplots(1,2,figsize=(14,6.6),sharey=True);fig.subplots_adjust(left=.24,right=.96,bottom=.24,top=.72,wspace=.14);seen=set();source=[]
  for ax,letter,model,title in zip(axs,'ab',['compiler-ftd','qwen'],['LLM Compiler 7B-FTD','Qwen2.5-Coder-7B-Instruct']):
   byid={r['task_id']:r for r in paired if r['model']==model};matrix=np.zeros((6,2));texts={}
   for i,id in enumerate(ids):
    r=byid[id]
    for j,(field,eff) in enumerate([('initial_status','initial_effective'),('hint_status','hint_effective')]):
     n,label,color=CATS[r[field]];matrix[i,j]=n;texts[i,j]=label+('*' if r[eff]=='True' else '');seen.add(n);source.append({'model':model,'task_id':id,'condition':j,'status':r[field],'effective':r[eff]=='True'})
   ax.imshow(matrix,cmap=ListedColormap(COLORS),vmin=-.5,vmax=5.5,aspect='auto',interpolation='nearest')
   for (i,j),t in texts.items():ax.text(j,i,t,ha='center',va='center',fontsize=13,color='#243746')
   ax.set_xticks([0,1],['仅原始任务','追加语义提示'],fontsize=14);ax.xaxis.tick_top();ax.tick_params(length=0,pad=10);ax.set_yticks(range(6),ids,fontsize=12)
   ax.set_xticks(np.arange(-.5,2,1),minor=True);ax.set_yticks(np.arange(-.5,6,1),minor=True);ax.grid(which='minor',color='white',linewidth=1.5);ax.tick_params(which='minor',bottom=False,left=False)
   for sp in ax.spines.values():sp.set_visible(False)
   ax.set_title(title,fontsize=16,pad=47,color='#102b40');ax.annotate(letter,xy=(0,1),xycoords='axes fraction',xytext=(-18,44),textcoords='offset points',fontsize=18,fontweight='bold',va='bottom')
  axs[1].tick_params(axis='y',labelleft=False)
  fig.suptitle('同一批 6 题：共同语义提示的影响',fontsize=22,y=.95,color='#102b40')
  fig.legend(handles=[Patch(facecolor=COLORS[i],label=legend_names[i]) for i in sorted(seen)],loc='lower center',bbox_to_anchor=(.60,.10),ncol=min(5,len(seen)),fontsize=12)
  fig.text(.24,.055,'* 表示完成预定优化目标；两模型使用相同的人工错误程序反例，保留测试输入不进入提示。',fontsize=11,color='#526675')
  fig.text(.24,.02,'这是统一语义信息对重新生成的影响，不是模型各自错误的修复率。',fontsize=11,color='#526675')
  export(fig,out/'shared_semantic_hints',list(axs),audit);(out/'hint_source_data.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n')
 (out/'FIGURE_NOTES.md').write_text('''# Figure notes

Python/Matplotlib only. Fixed authored task set, descriptive counts, no random population sampling or independent repeated seeds; no confidence intervals or p-values are asserted. All candidates remain in the primary denominators. Identity is a control, not an additional model.

Primary panels separate legal syntax, semantic-check coverage, verified outcomes and verified optimization goals. Each level has 6 tasks and 3 declared opportunities. The prompt contrast uses the same 6 development tasks and the same v3 evaluator, comparing the old multi-example format with each model's final accepted adapter. The intervening Qwen native-only format is retained in the full development table but is not one of this before/final figure's conditions. No case is removed within a condition. Development results are not part of the formal 18-task score. Old-admission counts are a structural-policy comparison on the exact candidates, not old semantic scores.

The optional hint figure contains the same six predefined formal tasks and the same counterexample information for both models. Its three opportunities are a subset, not the denominator of the full primary experiment. Hints come from authored mutants and diagnostic inputs; they are not the other model's answers or held-out execution inputs.

F16/FP16 checkpoints use different model families and inference backends. These plots do not isolate specialization as a causal treatment. Context normalization is restricted and logged; model code is not repaired before semantic validation.

Exports are slide-sized PNG at 300dpi and editable PDF/SVG, with companion source data. Counts/status labels supplement color. Panel alignment, PDF glyph size and collisions are checked after final rendering.
''')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--analysis',default='results/campaign-v3/analysis');p.add_argument('--out',default='results/campaign-v3/figures');a=p.parse_args();build(a.analysis,a.out)
