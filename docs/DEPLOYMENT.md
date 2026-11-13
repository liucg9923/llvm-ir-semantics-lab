# 云端部署

推荐 Ubuntu 22.04 x86_64，单卡报告至少 22GiB 显存，约 64GB RAM。代码与缓存放在数据盘，先检查剩余空间。当前任务不需要在 Mac 上启动虚拟机、模型或编译进程。

## CPU 工具链

scripts/bootstrap_validator.sh 会安装系统构建依赖和 LLVM 17.0.6，然后构建固定历史提交的 Alive2。若发行包缺少 EH，脚本明确停止，使用 scripts/build_llvm_source.sh 构建带 EH/RTTI 的 LLVM，再设置 LLVM_BIN 到该 build/bin。

Alive2 提交在 configs/toolchain.json 中先标为 candidate；构建完成不自动获得“验证可用”标志。只有验收成功才允许正式运行。验收文件保存在 .toolchain/accepted.json，并绑定二进制和任务集哈希。安装的 Z3/系统包版本也会记录，不能仅凭下载成功声称部署完毕。

Dockerfile.validator 是可选的独立 CPU 部署入口。AutoDL 等平台通常已经是容器，不必为了使用本项目再强行安装嵌套 Docker。在该云容器中可直接使用脚本、独立 Python 环境和测试过的执行限制。

## Python 和模型

核心评测仅依赖 Python 标准库；pytest 是开发选项。setup_python.sh 使用 HTTPS PyPI，为避免镜像默认 HTTP 失败，不修改全局 pip 配置。测试也可以通过 PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v 运行。

setup_inference.sh 建立独立 .venv-inference，安装锁定的 torch/transformers/accelerate/safetensors 版本并保存实际 pip freeze。GPU 驱动与 CUDA 可用性仍须通过预检。模型 revision 已锁定，首次下载需联网与足够空间；Meta 模型需用户在官方渠道取得访问权限。代码不会代替用户接受许可，不打印或保存访问 token。

建议先在 dev split 验证两个模型输入模板和生成长度，确认后保留冻结设置再跑 test。没有下载模型之前，不把模型推理模块的静态检查称为真实推理验证。

## 运行与中断

每题生成后立即保存原始答案和元数据。运行目录不允许覆盖；中断后它会保留 generating 状态。当前版本需另起新运行名重跑，不能把不同提示词/配置的局部结果拼成一个首轮结果。evaluate 会把缺失候选明确记为 generation_error，report 拒绝未完成评估的运行。

部署日志在 .build，模型/编译缓存、验收记录和运行数据默认被 Git 忽略。不要把下载权重、凭据、SSH 配置或整台服务器镜像提交到仓库。云服务器地址与密码属于部署信息，不属于项目文档。

### 下载源可选项

如果所在区域访问默认源很慢，可以只给本次命令指定镜像，不改全局 pip：

```bash
IRSEM_PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple bash scripts/setup_inference.sh
IRSEM_LLVM_APT_BASE=https://mirrors.tuna.tsinghua.edu.cn/llvm-apt bash scripts/bootstrap_validator.sh
```

LLVM 镜像仍使用 LLVM 官方签名密钥验证软件包。AutoDL 的可选 GitHub 加速可通过
`IRSEM_USE_PROVIDER_PROXY=1` 启用已有 `/etc/network_turbo`，只影响 Alive2 构建脚本的进程环境，不保存代理地址或认证信息。

网络和镜像的可用性不是实验结果。安装失败时应排除环境问题，不能把它记为模型错误。
