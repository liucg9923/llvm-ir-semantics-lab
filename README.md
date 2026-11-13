# LLVM IR Semantics Lab

在同一批 LLVM IR 程序变换任务上比较 LLVM `opt`、社区 LLM Compiler 7B-FTD F16 与 Qwen2.5-Coder-7B-Instruct FP16，分别检查**可评估覆盖、语义保持与有效优化**。

## 当前版本：V3 受控重跑

针对早期 FTD 实验的输入适配、粗糙准入和预检门槛问题，已完成重设计并重新运行。正式任务为 18 个新编写程序，L0/L1/L2 各 6 题，其中共 9 个预定优化机会。开发阶段、失败预检和旧结果全部保留。

| 对象 | 合法 IR | 进入语义验证 | 验证通过 | 已证反例 | 有效优化 |
|---|---:|---:|---:|---:|---:|
| LLVM opt 17.0.6 | 18/18 | 18/18 | 18/18 | 0 | 9/9 |
| 社区 LLM Compiler 7B-FTD F16 | 14/18 | 14/18 | 11/18 | 3 | 5/9 |
| Qwen2.5-Coder-7B-Instruct FP16 | 18/18 | 18/18 | 11/18 | 7 | 3/9 |
| 原样返回控制 | 18/18 | 18/18 | 18/18 | 0 | 0/9 |

本轮所有合法候选均进入语义验证。FTD 另有 4 个真实 LLVM IR 错误，未被自动修复，也不计入语义反例。两模型的总体通过数相同，失败方式和优化收益不同；不能推广成所有模型、所有编译任务的排名。

- [完整中文发现与反例](results/published/controlled-v3/analysis/FINDINGS.md)
- [结果、原始生成记录与完整证据包](results/published/controlled-v3/README.md)
- [覆盖、语义和优化图](results/published/controlled-v3/figures/coverage_correctness_optimization.png)
- [开发集提示对照图](results/published/controlled-v3/figures/development_prompt_contrast.png)
- [共同语义提示的逐题对照](results/published/controlled-v3/figures/shared_semantic_hints.png)

## 怎样避免重复早期的问题

**输入适配：** FTD 采用一个原程序、指定 pass 和实际输入代码大小的原生任务形式；Qwen 使用相同语义任务和官方 chat template，并增加仅约束唯一 IR 输出的 system 消息。不再用多个同名函数示例和自由式自查作为共同接口。

**评分：** 使用 LLVM 解析器处理结构，保留候选的指令、标志和属性。上下文继承及等价表示规范化有明确、受限的规则与记录；不运行优化 pass 替模型修复。真实接口不符、未证明假设、不支持、未知和已证语义反例分别统计。

**启动门槛：** 从原始开发记录重新计算可判定覆盖与指针题覆盖，不要求模型必须答对。Qwen 原生输出曾因多代码块被门槛阻止，改进格式适配后才开启正式任务。最终两模型均为 6/6 开发验证通过，所有正式模型输出均在最终冻结与共同门槛通过后产生。

**工具信息对照：** 两模型获得相同的人工错误程序所对应的语义反例，诊断输入与保留输入分开。这是共同语义提示对重新生成的影响，不是各自模型错误的修复率。FTD 配对 6 题的验证通过为 3→3，有效优化 1→2；Qwen 为 3→4，有效优化 1→1。

**应用回放：** 只依据支持范围和 Alive2 证明选择候选，否则回退原程序，选择时不读保留测试结果。两组最终均为 18/18 验证通过，各有 7 次原程序回退；系统结果不等于模型准确率。

## 复现与项目资料

- [V3 实验协议和开发修订](docs/REDESIGN_V3.md)
- [V3 云端部署与复现](docs/V3_DEPLOYMENT.md)
- [验证记录](docs/VALIDATION.md)
- [研究主线](docs/RESEARCH_FRAMEWORK.md)与[参考文献](docs/REFERENCES.md)
- [课堂 PPT 草稿](slides/README.md)
- [许可、模型来源与输出条款](THIRD_PARTY_NOTICES.md)

主要入口：

```bash
# 完成部署文档中的 LLVM/Alive2、GPU 环境及权重准备后，在云端运行：
bash scripts/run_controlled_v3.sh
.venv/bin/python scripts/collect_v3.py
.venv/bin/python scripts/replay_v3_verified_selection.py
.venv/bin/python scripts/v3_case_evidence.py
```

代码与人工任务按 Apache-2.0 发布，模型和其输出保留各自条款。权重、账号凭据和服务器登录信息不进入 GitHub。所有计算在云端完成，Mac 仅作 SSH 与结果查看/发布客户端。

## 历史记录

- [最初的 CPU 基线](results/published/baseline-v1/REPORT.md)
- [Qwen v2 实验](results/published/experiment-v2/README.md)
- [社区 FTD 首次接入及异常诊断](results/published/compiler-ftd-v1/README.md)

旧 FTD 的 0/24 是当时接口与准入条件下的零通过，不是测得语义正确率为零。它与新的 18 题不是同一协议/数据，不能写成模型能力提升率。旧记录完整保留，不追溯改分。

本项目是固定小函数上的可审查实验，不是广泛模型排行榜。没有循环、浮点、外部调用、并发或跨函数优化结论；不以文本完全匹配作为语义 oracle，也不把静态 IR 指令数等同于运行速度。
