# V3 受控重跑结果

本版本解决早期实验的输入适配、粗糙准入和错误启动门槛问题。正式模型阶段只在最终冻结和两模型预检通过后启动，使用 18 个新程序、9 个预定优化机会。

- [中文发现与真实反例](analysis/FINDINGS.md)
- [全部计数与开发对照](analysis/REPORT.md)、[逐题 CSV](analysis/per_case.csv)、[配对提示 CSV](analysis/paired_hints.csv)、[汇总 JSON](analysis/summary.json)
- [验证覆盖/语义/优化图](figures/coverage_correctness_optimization.png)、[开发集提示对照](figures/development_prompt_contrast.png)、[共同语义提示](figures/shared_semantic_hints.png)；同目录提供 PDF、SVG、源数据与 QA 记录。
- [原始生成记录](raw/)：每个实际模型调用保留一次，包含任务提示、wire prompt、原始回答、精确 token/设置；共 84 条。
- [便于浏览的逐题评估](evaluations/)和[所有未通过案例](analysis/cases/)
- [协议、门槛和验收摘要](protocol/)
- [完整证据包](evidence/controlled-v3-evidence.tar.gz)、[逐文件校验清单](evidence/FILES.sha256.json)、[归档校验和](evidence/ARCHIVE.sha256)

网页中的评估 JSON 是明确标注的阅读投影：保留结果、结构、原始 Alive2 日志和具体反例，省略冗长的全部原生输入输出数组。**完整数组、编译/执行日志、原始逐题评估、A/B 冻结与源码快照都在证据包中**；投影附有完整记录的归档路径和 SHA-256，不改写源记录。

首轮 FTD 11/18 验证通过、3 个已证反例、4 个非法 IR、5/9 有效优化；Qwen 11/18 验证通过、7 个已证反例、3/9 有效优化。所有合法候选均进入语义验证。两模型的 10 个正式语义反例均有 -O0、-O2 的保留执行差异。

共同语义提示来自人工错误程序，不是另一个模型的输出，也不是模型各自错误的修复率。验证后回退的 18/18 是系统结果，不能算模型准确率。

```bash
python scripts/verify_evidence.py results/published/controlled-v3/evidence/controlled-v3-evidence.tar.gz
python scripts/verify_v3_publication.py results/published/controlled-v3
```

模型权重、凭据和服务器登录信息不在仓库。模型与输出条款见项目 THIRD_PARTY_NOTICES.md。旧版实验完整保留，不能跨不同协议直接计算“模型能力提升率”。
