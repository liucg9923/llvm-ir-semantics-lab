# LLVM IR Semantics Lab

一个面向编译原理课堂的可复现实验：让 LLVM `opt`、LLM Compiler 7B-FTD 的社区 F16 GGUF 版本、Qwen2.5-Coder-7B-Instruct 在同一批 LLVM IR 任务上工作，分别检查**合法输出、语义保持和有效优化**。

核心问题：各自能交付多少安全且有效的变换？真实工具反馈能否改善结果？“没有通过完整检查”究竟发生在格式、任务契约，还是程序行为这一层？

## 当前结果

本轮三方组已完成。专用组按项目所有者要求采用 `second-state/llm-compiler-7b-ftd-GGUF` 中未量化的 **F16** 文件，不再等待官方基础模型权限。旧实验记录完整保留，新补充报告单独发布。

| 对象 | 合法 IR | 实际进入语义检查 | 通过完整检查 | 有效优化 |
|---|---:|---:|---:|---:|
| LLVM opt 17.0.6 | 24/24 | 24 | 24/24 | 12/12 |
| LLM Compiler 7B-FTD，社区 F16 | 21/24 | 0 | 0/24 | 0/12 |
| Qwen2.5-Coder-7B-Instruct，FP16 | 22/24 | 22 | 15/24 | 7/12 |
| 原样返回控制 | 24/24 | 24 | 24/24 | 0/12 |

**FTD 的 0/24 不表示 24 个答案都已被证明语义错误。** 21 个合法 IR 因改变目标设置、接口或增加元数据等违反冻结契约，另外 3 个非法 IR 重复定义了函数。它们没有进入主流程的语义验证。本轮体现了固定提示/接口下的端到端表现，不能据此单独排名两款模型的纯语义能力，也不是“专用训练收益”的因果消融。

在同一批预选的 12 题中，FTD 的自行复查与工具反馈均未修复完整验收；Qwen 从首次 7/12，通过自行复查变为 6/12，工具反馈变为 10/12，但有效优化从 4/6 降至 2/6。逐题变化和所有失败状态均公开。

独立执行重放另保存了一个 FTD 具体反例：原程序 `x+9` 在 `x=0` 时返回 `9`，未修改的模型候选返回 `11`。去示例的六题开发集诊断也单列，不替换正式成绩。人工 `mutant.ll` 是评分器验收材料，不是模型输出。

- [完整中文解读](results/published/compiler-ftd-v1/analysis/FINDINGS.md)
- [三方结果、原始回答、诊断与证据包](results/published/compiler-ftd-v1/README.md)
- [分层比较图](results/published/compiler-ftd-v1/figures/correctness_and_optimization.png)与[逐题反馈图](results/published/compiler-ftd-v1/figures/paired_feedback.png)
- [此前的 Qwen 实验版本](results/published/experiment-v2/README.md)，以及[最初 CPU 基线](results/published/baseline-v1/REPORT.md)

## 研究与资料导航

- [研究主线与核心问题](docs/RESEARCH_FRAMEWORK.md)
- [固定实验协议](docs/PROTOCOL.md)与[FTD 补充协议](results/published/compiler-ftd-v1/PROTOCOL_SUPPLEMENT.md)
- [云端部署](docs/DEPLOYMENT.md)与[社区 FTD 部署](docs/FTD_DEPLOYMENT.md)
- [实际验证记录](docs/VALIDATION.md)
- [课堂展示 PPT 草稿](slides/README.md)
- [参考文献与阅读用途](docs/REFERENCES.md)

## 任务范围

6 个开发题与 24 个正式题分属不同案例家族。正式题是 12 对案例，覆盖 L0 局部计算、L1 控制与依赖、L2 内存和别名，每层 8 题，其中 4 个预定优化机会、4 个约束案例。L0/L1/L2 是本项目分类，不是 LLVM 优化等级。

每题有输入、人工参考变换、人工错误变换、输入范围、pass 和可检查的优化目标。约束题不要求原样返回，安全的其他改写可以接受。首版无循环、浮点、外部调用、并发及跨函数优化；不把与 opt 文本完全一致当作语义 oracle。

## 云端复现入口

Mac 只用于 SSH，不需要在本机启动 Docker、编译或下载权重。在 Ubuntu 22.04 x86_64 云端项目根目录准备环境：

```bash
bash scripts/setup_python.sh
bash scripts/bootstrap_validator.sh
bash scripts/run_cpu.sh check-dataset
bash scripts/run_cpu.sh check-lock
bash scripts/run_cpu.sh accept-toolchain
bash scripts/setup_inference.sh
```

工具验收要求 90 个源程序/参考变换/人工错误变换达到预期，并绑定数据、代码、二进制及动态库哈希。详细的 LLVM EH/RTTI 构建说明见部署文档。

FTD 入口使用独立模型与运行时 lock；原数据集、提示词和解码设置保持 v2 冻结状态：

```bash
bash scripts/setup_llama_cpp.sh
HF_HUB_DISABLE_XET=1 .venv-inference/bin/python scripts/download_gguf.py
bash scripts/run_ftd.sh dev
bash scripts/run_ftd.sh formal
bash scripts/run_ftd.sh feedback
```

Qwen 与 LLVM 的原始入口保留：

```bash
bash scripts/run_cpu.sh generate --backend opt --out results/opt-v2
bash scripts/run_cpu.sh evaluate --run results/opt-v2
bash scripts/run_model.sh generate --backend hf --model qwen --out results/qwen-v2
bash scripts/run_cpu.sh evaluate --run results/qwen-v2
bash scripts/run_model.sh feedback --parent results/qwen-v2 --out results/qwen-feedback-v2
bash scripts/run_cpu.sh evaluate --run results/qwen-feedback-v2
```

运行目录拒绝覆盖。已有结果用独立新名称保存；本次对旧输出重评，没有重新调用 Qwen，也没有覆盖其 v2 记录。原官方基础模型的 `--model compiler` 配置仅保留用于历史追溯，不冒充已经运行。

## 评分与报告

顺序为：提取唯一 IR、LLVM verify、任务契约、Alive2 refinement、独立保留输入测试、预定优化目标。verify 只做语法检查和规范化打印，不用优化 pass 替模型修复答案。生成与 CPU 验证分开；候选在受 seccomp 和资源限制的子进程执行。

`verified` 需要完整验证通过；`refuted` 是已发现反例；格式/IR/契约失败与未知、工具错误分别记录。有效优化只统计**验证通过且完成预定目标**的机会题。原样返回保持语义，但拿不到机会题优化分。静态指令数不等于运行速度。

两种反馈都从同一个首次候选独立出发，各一次生成。反馈仅包含语法/契约/Alive2 与诊断集结果，不含保留输入集。额外的验证器选择与原程序回退是事后应用回放，不是模型准确率。

```bash
.venv/bin/python scripts/recheck_runs.py
.venv/bin/python scripts/collect_comparison.py
bash scripts/setup_reports.sh
.venv-report/bin/python scripts/plot_comparison.py \
  --analysis results/campaign-ftd-v1/analysis \
  --out results/campaign-ftd-v1/figures
```

图表提供 PNG、可编辑 SVG/PDF 和源数据；逐题 CSV、JSON、HTML 报告与完整证据归档可审查。模型权重和凭据不进入 GitHub。公开原始输出保留模型来源与适用条款，不能将 Meta 输出当作无限制训练数据，见 [许可与来源](THIRD_PARTY_NOTICES.md)。

## 主要来源

- [LLM Compiler 论文](https://arxiv.org/abs/2407.02524)
- [Meta FTD 模型卡与条款](https://huggingface.co/facebook/llm-compiler-7b-ftd)
- [社区 FTD GGUF 转换](https://huggingface.co/second-state/llm-compiler-7b-ftd-GGUF)
- [Qwen 官方模型](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct)
- [Alive2](https://github.com/AliveToolkit/alive2)
- [LLVM 17.0.6](https://github.com/llvm/llvm-project/tree/llvmorg-17.0.6)
