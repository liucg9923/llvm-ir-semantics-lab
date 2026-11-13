# 当前可运行组的结果（协议 v2）

本目录保存 LLVM opt、Qwen2.5-Coder-7B-Instruct 与原样返回控制组的真实结果。Meta LLM Compiler 等待官方授权，未运行、未计分。

- [主要发现与解释](analysis/FINDINGS.md)
- [完整统计表](analysis/REPORT.md)
- [逐题 CSV](analysis/per_case.csv) 与 [同题配对 CSV](analysis/paired_feedback.csv)
- [合法性、语义和有效优化图](figures/correctness_and_optimization.png)
- [12 题配对修订图](figures/paired_feedback.png)
- [原始模型回答、提示词和验证日志](raw/)
- [完整证据包](evidence/experiment-evidence.tar.gz) 与 [归档校验和](evidence/ARCHIVE.sha256)
- [模型文件哈希验证](checkpoint-verification.json)

证据包包括开发记录、正式输出、工具诊断、配置、代码快照、环境信息、图表、逐文件校验和。它不包含模型权重、Hugging Face Token、SSH 凭据或安装缓存。

开发阶段的旧解码配置记录保留但不计分。应用回退演示是事后回放，不能把其通过率写成 Qwen 本身的正确率。原始模型回答用于复核，不应将人工错误样例和真实模型失败混用。

数据来源和第三方许可见仓库 THIRD_PARTY_NOTICES.md。本次没有 Meta 模型输出。
