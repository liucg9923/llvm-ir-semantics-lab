# 参考文献与阅读用途

以下链接是资料入口；论文中报告的指标不是本项目的实验成绩。仓库不打包第三方论文全文或模型权重。

| 资料 | 本项目中的用途 |
|---|---|
| [Meta Large Language Model Compiler: Foundation Models of Compiler Optimization](https://arxiv.org/abs/2407.02524) | 理解 IR 编译器模拟、优化参数选择和反汇编三个不同任务；选择基础编译模拟模型，而非混用 FTD 的任务指标 |
| [LLM Compiler 7B 官方模型与许可](https://huggingface.co/facebook/llm-compiler-7b) | 模型版本、输入模板、访问条件和使用条款 |
| [Qwen2.5-Coder-7B-Instruct 官方模型](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct) | 通用代码模型的版本、模板和许可 |
| [Alive2: Bounded Translation Validation for LLVM](https://web.tecnico.ulisboa.pt/nuno.lopes/pubs.php?id=alive2-pldi21) | 理解 translation validation、refinement 与有界验证的限制 |
| [Alive2 官方代码](https://github.com/AliveToolkit/alive2) | 构建和验证行为，部署时锁定实际提交和二进制 |
| [LLVM 17.0.6 Language Reference](https://github.com/llvm/llvm-project/blob/llvmorg-17.0.6/llvm/docs/LangRef.rst) | 整数、poison/undef、内存、指针属性和 IR 语义 |
| [LLVM 17.0.6 New Pass Manager](https://github.com/llvm/llvm-project/blob/llvmorg-17.0.6/llvm/docs/NewPassManager.rst) | 任务中 pass pipeline 的组织方式 |
| [Compiler generated feedback for Large Language Models](https://arxiv.org/abs/2403.14714) | 工具反馈实验的相关研究背景；本项目实现是小规模独立设计 |
| [VEGA 作者项目页](https://wihn2021.github.io/vega-web/) | 原课堂 PPT 中的编译器后端生成资料，与当前 IR 变换实验分开解释 |

阅读原论文时要区分完全匹配、可编译、语义验证和实际优化效果。2024 年论文对当时 GPT-4 Turbo/Code Llama 的观测，也不能直接当作本项目 Qwen 模型的预期成绩。
