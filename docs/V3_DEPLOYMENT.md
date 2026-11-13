# V3 复现与实验控制

正式方案使用 18 道新任务、两个已固定检查点和同一套 LLVM 17.0.6 / Alive2 评测。开发修订记录与结果都保留；原 V2 和社区 FTD 首轮资料不覆盖。

## 准备云端环境

在 Linux x86_64 项目根目录执行，Mac 不需要模型、虚拟机或编译环境。

```bash
bash scripts/setup_python.sh
bash scripts/bootstrap_validator.sh
# 如果 LLVM 发行包未启用 EH，使用已有脚本构建：
IRSEM_USE_PROVIDER_PROXY=1 IRSEM_BUILD_JOBS=12 bash scripts/build_llvm_source.sh
bash scripts/build_v3_inspector.sh
bash scripts/setup_inference.sh
bash scripts/setup_llama_cpp.sh
```

需要 CUDA 编译器、LLVM 17 开发头文件、Z3 和 libseccomp。构建脚本会记录实际版本。模型生成顺序执行，GPU 锁避免两个检查点争用资源。

## 模型文件与完整性

```bash
.venv-inference/bin/python scripts/download_models_v3.py --model compiler-ftd
.venv-inference/bin/python scripts/download_models_v3.py --model qwen
```

文件身份由官方 Hugging Face 固定提交的大小和哈希控制。网络端点只负责传输，不允许替换检查点。Qwen 的 ModelScope 传输只在四个 safetensors 分片的 SHA-256 和大小全部匹配时使用，并记录对应的不可变文件版本。最终必须重新验证完整文件；已下载的分段可以续传。

本轮 FTD 使用社区 F16 文件，Qwen 使用官方 HF FP16 文件。F16 并不意味着每个张量/内核都使用完全相同的数值实现，且两模型基座、tokenizer 和推理后端不同。结果不是对“专用训练”单一因素的因果实验。

## 最终方案的全流程

准备完环境与权重后，在尚无同名运行数据的检出中执行：

```bash
bash scripts/run_controlled_v3.sh
```

脚本先构建固定的共同语义提示，验收评分器，冻结任务/代码/配置，再做两个模型的开发预检。它重新计算门槛，不接受孤立的 passed 标志。门槛是完整生成、可判定覆盖和指针题覆盖，不要求模型一定答对。

最终适配方式：FTD 使用原生单任务 `[INST]`；Qwen 使用相同语义任务文本和官方 chat template，并在 system 消息中要求唯一 IR 代码块。该 system 消息不提供答案、优化规则或反例。没有固定函数体前缀，没有在输出后补写或修复指令。

任一主预检不通过时，脚本停止正式模型生成。共同语义提示条件也先做独立预检；任一模型不通过时，双方都不开展该正式条件，未运行不记零分。

现有目录拒绝覆盖；新实验应使用新的检出或明确的新运行命名空间。不得根据正式任务结果修改提示或筛掉难题。

## 评分与数据保存

LLVM 解析器处理结构和 SSA。上下文继承/等价规范化有明确记录；不修改函数体、溢出标志或属性来替模型修复。真实接口冲突、未证明的假设、不支持、语义反例与验证通过分别统计。

Alive2 结论与 -O0、-O2 两种编译设置的独立执行共同记录。诊断输入与保留输入分开，实际输入、源/候选输出、工具日志和精确模型提示均保存。模型只收到共同诊断反例的简洁数值信息，保留输入不进入提示。

```bash
.venv/bin/python scripts/collect_v3.py
.venv/bin/python scripts/replay_v3_verified_selection.py
.venv/bin/python scripts/v3_case_evidence.py
bash scripts/setup_reports.sh
.venv-report/bin/python scripts/plot_v3.py
```

当前汇总脚本同时支持本轮保留的 A/B 开发记录；从头复现最终 B 方案时不会凭空生成已经不存在的中间方案成绩。最终主表只使用同一冻结下的 18 个正式任务。

应用回放只根据支持范围和 Alive2 证明选择模型候选，否则回退原程序；选择不读保留测试结果。随后重新执行保留验证，不能把回退成功算作模型准确率或模型优化贡献。

## 本轮的开发修订记录

A 方案的原始提示、回答、门槛、代码和冻结记录位于证据包的 calibration-A 及 v3-pilot-*。FTD 原生 6/6 验证通过；Qwen 原生无唯一输出约束时有两题返回多代码块，指针题没有进入语义检查，正式生成被阻止。

B 方案只调整 Qwen 的系统格式约束。评分实现、任务、数值生成设置和 FTD 实际 wire prompt 保持一致，并有逐文件/逐输出复核。FTD 开发候选重评不算新调用；Qwen 使用新适配重新预检。所有正式模型任务均在 B 的共同门槛通过之后才生成。
