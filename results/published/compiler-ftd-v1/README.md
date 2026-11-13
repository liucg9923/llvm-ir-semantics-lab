# 社区 LLM Compiler 7B-FTD 补充实验

本轮使用 second-state/llm-compiler-7b-ftd-GGUF 的 F16 文件、固定 llama.cpp 后端，在原 v2 任务与评分器上完成 24 道初始任务和 12 道任务的两种独立修订。另保存 6 道接入开发题、6 道事后去示例诊断，开发数据不计正式成绩。

- [中文结果与解释边界](analysis/FINDINGS.md)
- [全部分层计数](analysis/REPORT.md)、[汇总 JSON](analysis/summary.json)、[逐题 CSV](analysis/per_case.csv)、[同题反馈 CSV](analysis/paired_feedback.csv)
- [主图](figures/correctness_and_optimization.png)、[配对图](figures/paired_feedback.png)，同目录提供 PDF、SVG、源数据和检查记录。
- [原始提示、答案、精确 token 和逐题评估](raw/)
- [独立执行重放](analysis/illustrative_replay/)与[开发集提示诊断](analysis/prompt_diagnostic.json)
- [证据归档](evidence/experiment-evidence.tar.gz)、[逐文件校验清单](evidence/FILES.sha256.json)、[归档校验和](evidence/ARCHIVE.sha256)
- [补充协议](PROTOCOL_SUPPLEMENT.md)与[来源说明](PROVENANCE_NOTES.md)

首轮 FTD 为 21 个合法但契约不符、3 个非法 IR，没有候选进入正式语义验证。零次完整验收通过不等于 24 个已证语义错误。独立重放发现 x=0 时原程序 x+9 返回 9、FTD 候选返回 11；该重放单列，不修改主表分类。

旧 Qwen、LLVM 和 identity 的 96 条结果在新版程序下重新验证，原始内容与评分保持一致，没有重新调用旧模型。新证据包收录这些复核记录；其更早的开发过程和原始代码快照见 [experiment-v2](../experiment-v2/README.md)。

模型权重和登录凭据不在此目录。原始模型输出保留其来源及适用条款，见仓库 THIRD_PARTY_NOTICES.md；不要将 Meta 输出作为无限制训练数据。

```bash
python scripts/verify_evidence.py results/published/compiler-ftd-v1/evidence/experiment-evidence.tar.gz
python scripts/verify_comparison.py results/published/compiler-ftd-v1
```
