# 完整证据包

此包包含所有已运行组的原始提示词、回答、生成元数据、工具日志、反例、代码/配置快照、环境信息、图表和逐文件校验和。开发运行与正式运行分开保存。

模型权重、认证信息、下载缓存和安装环境不在包中。Meta 模型未运行，没有对应成绩。

解压后优先阅读 results/campaign-v1/analysis/FINDINGS.md。完整源码和浏览入口见 GitHub 仓库；归档中的根 README 是采集时的项目快照。

可在仓库根目录验证：

```bash
python scripts/verify_evidence.py results/published/experiment-v2/evidence/experiment-evidence.tar.gz
```

ARCHIVE.sha256 用于校验整个压缩包，FILES.sha256.json 用于校验包内每个文件。校验用于发现内容损坏，不代替科学审查。
