# LLVM IR Semantics Lab

一个面向编译原理课堂的可复现实验：在同一批 LLVM IR 变换任务上，比较 LLVM `opt`、Meta LLM Compiler 7B 和 Qwen2.5-Coder-7B-Instruct。

核心问题：**各自能完成多少安全且有效的变换？真实工具反馈能否改善模型的结果？**

本仓库的人工错误样例是评测器验收材料，不是任何模型的失败记录。没有运行模型时，不报告模型成绩。

## 研究与资料导航

- [研究主线与四个核心问题](docs/RESEARCH_FRAMEWORK.md)
- [实验协议](docs/PROTOCOL.md)与[云端部署](docs/DEPLOYMENT.md)
- [实际验证记录](docs/VALIDATION.md)
- [已公开的编译器基线与原样返回控制组](results/published/baseline-v1/REPORT.md)
- [课堂展示 PPT 草稿](slides/README.md)
- [参考文献与阅读用途](docs/REFERENCES.md)

当前已完成 LLVM opt 与 Qwen 的首轮、同题修订实验及数据归档；Meta LLM Compiler 的官方访问申请仍待审核，未运行、未计分。详见 [当前实验结果](results/published/experiment-v2/README.md)。

## 当前范围

- 6 个开发题，用于环境和提示词调试；24 个正式题，12 对案例。
- L0 局部计算、L1 控制流与值依赖、L2 内存和别名，各 8 题。
- 每层 4 个优化机会题、4 个约束/陷阱题。陷阱题不要求原样返回，任何通过验证的合法改写都可接受。
- 每题有输入、人工参考变换、人工错误变换、输入范围、pass 和可检查的优化目标。
- 首版不含循环、浮点、外部调用、并发或跨函数优化。L0/L1/L2 是项目分类，不是 LLVM 优化等级。
- 不以 `opt` 的输出文本作为语义 oracle，也不把完全匹配率当成正确率。

## 快速开始

以下命令在 Linux x86_64 云服务器的项目目录执行。Mac 仅用于 SSH，不需要启动本地 Docker 或下载模型。

```bash
# 建立轻量 Python 环境。也可 IRSEM_PYTHON=/path/to/python3 bash scripts/setup_python.sh
bash scripts/setup_python.sh
make unit

# 在 Ubuntu 22.04 的独立云实例/容器中安装 LLVM 17 和 Alive2。
# 会安装系统包，需要 root；不会启动模型或改动 SSH 配置。
bash scripts/bootstrap_validator.sh

bash scripts/run_cpu.sh doctor
bash scripts/run_cpu.sh check-dataset
bash scripts/run_cpu.sh check-lock
bash scripts/run_cpu.sh accept-toolchain
```

`accept-toolchain` 必须在全部 90 个 identity/reference/mutant 检查达到预期后才生成验收记录。正式运行会再次核对数据集和二进制哈希。只完成构建不等于验收通过。

任务修改后，先检查和验证，再显式运行 `irsem freeze`，重新验收工具链。不能将两个数据集版本的结果混在一张表里。

## 三组首轮实验（当前固定协议 v2）

```bash
# CPU baseline
bash scripts/run_cpu.sh generate --backend opt --out results/opt-v2
bash scripts/run_cpu.sh evaluate --run results/opt-v2

# 单独准备 GPU 依赖；不会下载权重，也不会替用户接受模型许可。
bash scripts/setup_inference.sh

# 按官方说明在云端配置 Hugging Face 访问权限；不要将凭据写入代码/Git。
bash scripts/run_model.sh generate --backend hf --model compiler --out results/compiler-v2
bash scripts/run_cpu.sh evaluate --run results/compiler-v2
bash scripts/run_model.sh generate --backend hf --model qwen --out results/qwen-v2
bash scripts/run_cpu.sh evaluate --run results/qwen-v2
```

两个模型顺序加载，FP16、batch size 1、贪心解码。当前配置要求 GPU 报告至少 22GiB 显存；不能为让某个模型跑通而悄悄改变其量化精度。首次下载按模型官方访问条款进行。

## 反馈对照与报告

```bash
bash scripts/run_model.sh feedback --parent results/compiler-v2 --out results/compiler-feedback-v2
bash scripts/run_cpu.sh evaluate --run results/compiler-feedback-v2
bash scripts/run_model.sh feedback --parent results/qwen-v2 --out results/qwen-feedback-v2
bash scripts/run_cpu.sh evaluate --run results/qwen-feedback-v2
bash scripts/run_cpu.sh report --runs results/opt-v2 results/compiler-v2 results/qwen-v2 \
  results/compiler-feedback-v2 results/qwen-feedback-v2 --out reports/generated/v1
```

反馈题是预先指定的 12 题。每题从同一个首次候选分成“自行复查”和“工具反馈”两支，每支一次生成。工具反馈只包含语法/约束诊断、Alive2 信息及诊断输入集结果，不包含保留输入集结果。

报告包含 Markdown 表、逐题 CSV、JSON 和浏览器可打开的 HTML 色阶表。`fixture`/`smoke` 结果有显式标记，不能作为模型成绩。

## 结果应怎样读

- `verified`：Alive2 对唯一函数成功验证，差分测试也一致；仍受支持范围和工具语义模型约束。
- `refuted`：发现 Alive2 或有效输入差分反例。
- `unknown` / `tested_only`：没有形式验证结论，后者只表示有限测试通过。
- `invalid_ir` / `format_error` / `contract_violation`：格式、IR 或任务约束不满足。
- `tool_error` / `execution_error` / `oracle_conflict`：工具异常、候选执行异常或检查冲突，不能算成功。
- `verification_only`：形式验证通过，但没有完成差分执行，不计完整成功。
- `generation_error`：生成缺失、超限或被截断。

有效优化只在优化机会题上统计：**验证通过且完成预先定义的目标**。原样返回不会得到优化分。`refuted/N` 是发现错误的比例，不是未知候选的真实错误率。每层只有 8 题，报告分子/分母，避免过度概括。

## 目录与复现

`configs/` 固定模型提交、推理设置和反馈子集；`tasks/` 保存可审查的原始 IR；`src/irsem/` 是执行与评测代码；`tests/` 验证评测器；`scripts/` 和 `docker/` 提供部署入口。

详细约定见 [实验协议](docs/PROTOCOL.md)、[部署说明](docs/DEPLOYMENT.md)、[许可与来源](THIRD_PARTY_NOTICES.md)。原始运行产物默认不进入 Git；经审查的 CPU 基线保存在 results/published。公开代码前不需要把服务器密码、HF Token 或模型权重放进仓库。

## 主要来源

- LLM Compiler: https://arxiv.org/abs/2407.02524
- Meta 官方模型与许可: https://huggingface.co/facebook/llm-compiler-7b
- Qwen 官方模型: https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct
- Alive2: https://github.com/AliveToolkit/alive2
- LLVM 17: https://github.com/llvm/llvm-project/tree/llvmorg-17.0.6

本实验比较具体版本、具体任务上的表现，不代表所有 LLM 的能力上限；两个模型的比较也不是对“专用训练收益”的严格因果消融。

## 本轮结果简表

| 对象 | 合法 IR | 语义验证通过 | 有效优化 |
|---|---:|---:|---:|
| LLVM opt | 24/24 | 24/24 | 12/12 |
| Qwen2.5-Coder-7B-Instruct | 22/24 | 15/24 | 7/12 |
| 原样返回控制 | 24/24 | 24/24 | 0/12 |
| LLM Compiler 7B | 待授权 | 未运行 | 未运行 |

在预选的同一批 12 题中，自行复查的验证通过数为 6/12，工具反馈为 10/12；相应有效优化为 3/6 和 2/6。完整数据与边界说明见当前实验报告。不要将不同分母、人工验收样例或事后应用回放混成模型正确率。
