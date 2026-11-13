"""Prepare a readable release projection; full execution records remain in the archive."""
from pathlib import Path
import shutil,copy
from irsem.common import read_json,write_json,digest
root=Path(__file__).resolve().parents[1];campaign=root/'results/campaign-v3';dst=root/'results/published/controlled-v3'
if dst.exists():raise SystemExit('Refuse to overwrite a published version directory')
dst.mkdir(parents=True)
for p in (campaign/'analysis').glob('*'):
 if p.is_file():shutil.copyfile(p,dst/'analysis'/p.name) if (dst/'analysis').exists() else None
(dst/'analysis').mkdir(exist_ok=True)
for p in (campaign/'analysis').glob('*'):
 if p.is_file():shutil.copyfile(p,dst/'analysis'/p.name)
shutil.copytree(campaign/'figures',dst/'figures')
for p in (dst/'figures').glob('*.alignment-audit.svg'):p.unlink()
shutil.copytree(campaign/'evidence',dst/'evidence')
protocol=dst/'protocol';protocol.mkdir()
for n in ['frozen.json','selected-profile.json','selection-primary.json','selection-with-hints.json','revalidation-B.json','status.json']:
 shutil.copyfile(campaign/n,protocol/n)
for n in ['experiment-v3.json','models.json','compiler-ftd.json','llama-cpp.json']:
 shutil.copyfile(root/'configs'/n,protocol/n)
shutil.copyfile(root/'tasks/v3/manifest.json',protocol/'task-manifest.json')
shutil.copyfile(root/'docs/REDESIGN_V3.md',protocol/'REDESIGN_V3.md')
for n in ['compiler-ftd-verified.json','qwen-verified.json','qwen-modelscope-transport.json','compiler-ftd-sparse-recovery.json']:
 p=root/'results/model-downloads'/n
 if p.exists():shutil.copyfile(p,protocol/n)
# One published copy per actual model-generation call, not per revalidation.
unique_runs=['v3-pilot-compiler-ftd','v3-pilot-qwen','v3b-pilot-qwen','v3b-hintpilot-compiler-ftd','v3b-hintpilot-qwen','v3b-formal-compiler-ftd','v3b-formal-qwen','v3b-hint-compiler-ftd','v3b-hint-qwen']
for name in unique_runs:
 src=root/'results'/name;out=dst/'raw'/name;out.mkdir(parents=True)
 shutil.copyfile(src/'manifest.json',out/'manifest.json');shutil.copyfile(src/'input-facts.json',out/'input-facts.json');shutil.copytree(src/'candidates',out/'candidates')

def compact(row):
 r=copy.deepcopy(row)
 if 'differential' in r:
  r['differential']={level:{k:v for k,v in data.items() if k not in {'inputs','source_outputs','candidate_outputs','logs'}} for level,data in r['differential'].items()}
 if r.get('syntax_log'):r['syntax_log'].pop('stdout',None)
 return r
summary=read_json(campaign/'analysis/summary.json')
run_names=set(summary['primary_runs'].values())|set(summary['pilot_runs'].values())|set(summary['selected_pilot_runs'].values())|set(summary['hint_runs'].values())|{'v3b-hintpilot-compiler-ftd','v3b-hintpilot-qwen'}
for name in sorted(run_names):
 src=root/'results'/name;m=read_json(src/'manifest.json');rows=read_json(src/'results.json')
 write_json(dst/'evaluations'/(name+'.json'),{'projection':'Per-case fields and full Alive2 logs; complete native input/output arrays and execution logs are in the evidence archive.',
  'full_results_path_in_archive':str((src/'results.json').relative_to(root)),'full_results_sha256':digest(src/'results.json'),
  'generation_origin_run':m.get('generation_provenance',{}).get('original_run',name),'rows':[compact(r) for r in rows]})
for model in ['compiler-ftd','qwen']:
 src=campaign/'analysis/application'/model
 shutil.copytree(src,dst/'analysis/application'/model,ignore=shutil.ignore_patterns('evaluation.json'))
case_dir=campaign/'analysis/cases';shutil.copytree(case_dir,dst/'analysis/cases',ignore=shutil.ignore_patterns('evaluation.json','illustrative-diagnostic-replay.json'))
for p in case_dir.rglob('evaluation.json'):
 r=read_json(p);out=dst/'analysis/cases'/p.relative_to(case_dir)
 write_json(out,{'projection':'Full native arrays/logs are in the evidence archive.','full_path_in_archive':str(p.relative_to(root)),'full_sha256':digest(p),'evaluation':compact(r)})
for p in case_dir.rglob('illustrative-diagnostic-replay.json'):
 r=read_json(p);r['evaluation']=compact(r['evaluation']);r['full_path_in_archive']=str(p.relative_to(root));r['full_sha256']=digest(p)
 write_json(dst/'analysis/cases'/p.relative_to(case_dir),r)
accept=read_json(campaign/'oracle-acceptance.json');write_json(protocol/'oracle-acceptance-summary.json',{'passed':accept['passed'],'count':accept['count'],'created_utc':accept['created_utc'],'inspector_sha256':accept['inspector_sha256'],'toolchain':accept['toolchain'],'sandbox':accept['sandbox'],'checks':[{'id':r['id'],'expected':r['expected'],'status':r['evaluation']['status'],'passed':r['passed']} for r in accept['records']]})
shutil.copyfile(campaign/'final-tests.log',protocol/'unit-native-tests.log')
(dst/'README.md').write_text('''# V3 受控重跑结果\n\n本版本解决早期实验的输入适配、粗糙准入和错误启动门槛问题。正式模型阶段只在最终冻结和两模型预检通过后启动，使用 18 个新程序、9 个预定优化机会。\n\n- [中文发现与真实反例](analysis/FINDINGS.md)\n- [全部计数与开发对照](analysis/REPORT.md)、[逐题 CSV](analysis/per_case.csv)、[配对提示 CSV](analysis/paired_hints.csv)、[汇总 JSON](analysis/summary.json)\n- [验证覆盖/语义/优化图](figures/coverage_correctness_optimization.png)、[开发集提示对照](figures/development_prompt_contrast.png)、[共同语义提示](figures/shared_semantic_hints.png)；同目录提供 PDF、SVG、源数据与 QA 记录。\n- [原始生成记录](raw/)：每个实际模型调用保留一次，包含任务提示、wire prompt、原始回答、精确 token/设置；共 84 条。\n- [便于浏览的逐题评估](evaluations/)和[所有未通过案例](analysis/cases/)\n- [协议、门槛和验收摘要](protocol/)\n- [完整证据包](evidence/controlled-v3-evidence.tar.gz)、[逐文件校验清单](evidence/FILES.sha256.json)、[归档校验和](evidence/ARCHIVE.sha256)\n\n网页中的评估 JSON 是明确标注的阅读投影：保留结果、结构、原始 Alive2 日志和具体反例，省略冗长的全部原生输入输出数组。**完整数组、编译/执行日志、原始逐题评估、A/B 冻结与源码快照都在证据包中**；投影附有完整记录的归档路径和 SHA-256，不改写源记录。\n\n首轮 FTD 11/18 验证通过、3 个已证反例、4 个非法 IR、5/9 有效优化；Qwen 11/18 验证通过、7 个已证反例、3/9 有效优化。所有合法候选均进入语义验证。两模型的 10 个正式语义反例均有 -O0、-O2 的保留执行差异。\n\n共同语义提示来自人工错误程序，不是另一个模型的输出，也不是模型各自错误的修复率。验证后回退的 18/18 是系统结果，不能算模型准确率。\n\n```bash\npython scripts/verify_evidence.py results/published/controlled-v3/evidence/controlled-v3-evidence.tar.gz\npython scripts/verify_v3_publication.py results/published/controlled-v3\n```\n\n模型权重、凭据和服务器登录信息不在仓库。模型与输出条款见项目 THIRD_PARTY_NOTICES.md。旧版实验完整保留，不能跨不同协议直接计算“模型能力提升率”。\n''')
(dst/'evidence/README.md').write_text('''# Complete evidence\n\nThe archive preserves all raw runs and per-case evaluations, every native input/output, LLVM/Alive2 logs, development revisions A and B, immutable snapshots, gates, infrastructure status, figures and source code. No model weights or credentials are included.\n\nThe embedded FILES.sha256.json identifies each archived file. Verification reads the archive without extraction. The archive includes repeated validation copies with explicit lineage; they are not counted as independent model calls.\n''')
print('Prepared',sum(p.is_file() for p in dst.rglob('*')),'public files; full evidence remains separately verifiable')
