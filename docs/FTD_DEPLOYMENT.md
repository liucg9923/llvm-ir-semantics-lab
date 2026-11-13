# 社区 FTD 模型部署与复现

本轮按项目所有者要求增加 `second-state/llm-compiler-7b-ftd-GGUF`。使用其中 **F16、未作 Q4/Q5 量化**的文件，以保持与 Qwen FP16 相同的权重精度。模型和运行时版本、SHA-256、上下文与采样设置在 `configs/compiler-ftd.json`、`configs/llama-cpp.json` 及其独立 lock 中固定。原 `configs/models.json` 和任务 lock 保留，以避免改写已经完成的 v2 实验。

源仓库公开提供下载；无需把个人账号 token 放入脚本。公开下载不改变 Meta 模型条款。GGUF 来自社区转换，来源归属由转换者声明，项目未与门控的官方原始权重逐位核对。

## 运行环境

在 Linux x86_64 云端项目根目录运行。已经准备好 LLVM/Alive2、核心及推理 Python 环境后，安装带 nvcc 的 CUDA 工具链、CMake、Ninja、C++ 编译器。脚本默认使用 `/usr/local/cuda`，也支持 `CUDA_HOME`。本轮 CUDA 12.1、Ada GPU，编译目标固定为 89；换架构需要另建运行时配置和实验记录。

F16 GGUF 文件约 13.48GB；模型下载前要求另有至少 3GiB 磁盘余量。运行时要求至少 22000MiB 空闲显存，采用一个槽位和 F16 KV cache。本轮云设备报告 32760MiB 显存。

```bash
bash scripts/setup_llama_cpp.sh
HF_HUB_DISABLE_XET=1 .venv-inference/bin/python scripts/download_gguf.py
```

下载会先向 Hugging Face 查询固定版本元数据，再校验文件大小及完整 SHA-256。网络需要时，可给该公开模型指定 `--public-mirror`；镜像请求始终不带账号 token，文件仍须匹配官方 Hub 的固定版本哈希。慢速大文件可在停止前一个下载进程后运行 `scripts/download_gguf_ranges.py`，它以最多 16 个并行 Range 请求写入同一缓存文件，保存分段进度，并在接受文件之前重新校验完整 SHA-256；随后重跑普通下载脚本写入最终验证清单。分段过程中不要同时启动普通下载器。

```bash
.venv/bin/irsem check-lock
.venv/bin/irsem accept-toolchain
IRSEM_NATIVE_TESTS=1 LLVM_BIN="$PWD/.toolchain/bin" \
  ALIVE_TV="$PWD/.toolchain/bin/alive-tv" \
  .venv/bin/python -m unittest discover -s tests -v

# 开发集检查后，按冻结协议运行。已存在的运行目录拒绝覆盖。
bash scripts/run_ftd.sh dev
bash scripts/run_ftd.sh formal
bash scripts/run_ftd.sh feedback
```

推理服务只监听云端 `127.0.0.1` 的临时端口，由生成进程启动并关闭。无需向公网开放模型 API。精确输入 token、wire prompt、输出 token、服务返回的生成设置、EOS/截断状态和耗时均随候选保存。没有语法约束解码，也不使用 opt 修复模型答案。

## 与已有结果合并

增加后端改变了共享 runner 的源码哈希；`scripts/recheck_runs.py` 用新验收记录重新评估旧的原始候选，不再调用旧模型，并逐项核对评分是否变化。重评结果单独保存，原 v2 记录不覆盖。

```bash
.venv/bin/python scripts/recheck_runs.py
.venv/bin/python scripts/collect_comparison.py
.venv/bin/python scripts/replay_safe_selection.py \
  --initial compiler-ftd-v1 --feedback compiler-ftd-feedback-v1 \
  --out results/campaign-ftd-v1/analysis/application_replay/compiler_ftd
.venv-report/bin/python scripts/plot_comparison.py \
  --analysis results/campaign-ftd-v1/analysis \
  --out results/campaign-ftd-v1/figures
```

FTD 的公开下游训练任务包括 pass 选择和反汇编。本项目给定 pass、要求模型直接生成 IR，是固定接口下的任务迁移评测，不是原论文 pass 选择/二进制体积实验的复现。FTD 与 Qwen 的模型年代、训练目标、tokenizer 和推理后端均不同，即使权重精度相同，也不能把成绩差异只归因于是否专用训练。

## 本轮补充诊断及完整归档顺序

事后去示例诊断只用开发集，不替换正式评分。需要复现完整补充包时，在正式与反馈运行完成后执行：

```bash
flock -n .cache/gpu.lock .venv-inference/bin/python scripts/diagnose_prompt_examples.py
.venv/bin/python scripts/diagnostic_replays.py
.venv/bin/python scripts/case_evidence.py
```

`diagnostic_replays.py` 对指定原始候选直接重放，不恢复目标、不移除属性或元数据，且不更改正式分类。`write_comparison_findings.py` 的文字解释绑定本轮观察；若新环境复现结果发生变化，它会拒绝沿用不符的文字，需先审阅数据更新解读。

完整公开包的逐项校验命令：

```bash
.venv/bin/python scripts/verify_evidence.py results/published/compiler-ftd-v1/evidence/experiment-evidence.tar.gz
.venv/bin/python scripts/verify_comparison.py results/published/compiler-ftd-v1
```

完整执行记录另保存在证据包的 stages、manifest、源码快照与配置中。下载失败或慢速连接重试属于基础设施过程，模型评分只统计已提交的候选及其明确失败状态。
