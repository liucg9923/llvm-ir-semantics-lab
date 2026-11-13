# 验证记录

记录时间（UTC）：2026-11-13T03:16:57.148910+00:00

## 已完成的实际验证

- Linux x86_64 云端运行；LLVM 17.0.6，源码提交 6009708b4367171ccdbf4b5905cb6a803753fe18。
- Alive2 固定提交 e031ebd9c18be1a4fc7f37ab193b4b158b92dd9a，Z3 软件包 4.8.12-1。
- 6 个开发题、24 个正式题；当前活动任务的 90 个 IR 文件通过 LLVM 语法/类型检查。
- 14 项自动化测试全部通过，包含真实原生执行、返回值与内存结果对比、seccomp 阻断网络创建、CLI 缺失输出计分。
- 完整验证器验收共 90 项：60 项原样/参考变换 verified，30 项人工错误变换 refuted。
- 正式 opt 基线：24/24 verified；12/12 预设优化机会完成；7/24 输出未改变。
- 原样返回控制：24/24 verified，0/12 有效优化，24/24 原样返回。
- GPU 依赖无冲突。PyTorch 2.6.0+cu124、Transformers 4.51.3、CUDA 12.4 的小型 FP16 矩阵计算通过。

## 版本绑定

- 数据集锁：`b7e6848a37598f527eace2dc83560b5c28b01db5a8b1bda35569b00c12266de2`
- 验收时评测源码哈希：`ca23c0e9f60e835db087a7b14e4d692c9b749a90c2de00329db0fb42bd9de954`

工具与动态库的完整哈希、验证器日志和沙箱检查结果位于部署目录的 `.toolchain/`。
基线的逐题原始 IR、证明/测试日志和元数据在 `results/opt-v1/`。
控制组在 `results/identity-v1/`。报告在 `reports/generated/baseline/`。
这些运行产物默认不进入 Git；源码包不包含环境、权重或凭据。

## 已知边界与尚未进行的工作

- 本记录没有任何 LLM 成绩。两款模型的权重尚未下载，真实模型推理/修复实验尚未运行。
- Meta 官方模型需要相应 Hugging Face 访问授权。
- 历史 Alive2 不支持参数 noalias；原例保留在 tasks/excluded/noalias_attribute。
  主例改为显式相邻不重叠地址，仍保留可能别名的对照。修订发生在模型实验之前。
- Dockerfile 与 GitHub Actions 已提供，但本次是在云容器内直接运行部署脚本，未另行运行 Docker build 或 GitHub runner。
- 小任务上的验证不能推广为编译器无缺陷，也不能推广为模型的整体能力结论。
