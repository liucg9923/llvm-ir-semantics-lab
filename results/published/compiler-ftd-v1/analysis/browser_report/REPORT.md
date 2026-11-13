# 实验结果

只将 mode=formal 的 opt/HF 记录作为正式实验；fixture/smoke 记录是评测器检查。
refuted 是已发现反例的比例，不是所有未知候选的真实错误率。每个数值保留分母。

| 选手/运行 | 模式 | 层级 | 分支 | 合法 IR | 验证通过 | 发现反例 | 有效优化 | 原样返回 |
|---|---|---|---|---:|---:|---:|---:|---:|
| opt (opt-v2-rechecked-ftd) | formal | L0 | initial | 8/8 | 8/8 | 0/8 | 4/4 | 1/8 |
| opt (opt-v2-rechecked-ftd) | formal | L1 | initial | 8/8 | 8/8 | 0/8 | 4/4 | 2/8 |
| opt (opt-v2-rechecked-ftd) | formal | L2 | initial | 8/8 | 8/8 | 0/8 | 4/4 | 4/8 |
| second-state/llm-compiler-7b-ftd-GGUF (compiler-ftd-v1) | formal | L0 | initial | 8/8 | 0/8 | 0/8 | 0/4 | 0/8 |
| second-state/llm-compiler-7b-ftd-GGUF (compiler-ftd-v1) | formal | L1 | initial | 6/8 | 0/8 | 0/8 | 0/4 | 0/8 |
| second-state/llm-compiler-7b-ftd-GGUF (compiler-ftd-v1) | formal | L2 | initial | 7/8 | 0/8 | 0/8 | 0/4 | 0/8 |
| Qwen/Qwen2.5-Coder-7B-Instruct (qwen-v2-rechecked-ftd) | formal | L0 | initial | 6/8 | 6/8 | 0/8 | 2/4 | 4/8 |
| Qwen/Qwen2.5-Coder-7B-Instruct (qwen-v2-rechecked-ftd) | formal | L1 | initial | 8/8 | 5/8 | 3/8 | 2/4 | 2/8 |
| Qwen/Qwen2.5-Coder-7B-Instruct (qwen-v2-rechecked-ftd) | formal | L2 | initial | 8/8 | 4/8 | 4/8 | 3/4 | 0/8 |
| identity (identity-v2-rechecked-ftd) | fixture | L0 | initial | 8/8 | 8/8 | 0/8 | 0/4 | 8/8 |
| identity (identity-v2-rechecked-ftd) | fixture | L1 | initial | 8/8 | 8/8 | 0/8 | 0/4 | 8/8 |
| identity (identity-v2-rechecked-ftd) | fixture | L2 | initial | 8/8 | 8/8 | 0/8 | 0/4 | 8/8 |
| second-state/llm-compiler-7b-ftd-GGUF (compiler-ftd-feedback-v1) | formal | L0 | self_review | 0/4 | 0/4 | 0/4 | 0/2 | 0/4 |
| second-state/llm-compiler-7b-ftd-GGUF (compiler-ftd-feedback-v1) | formal | L0 | tool_feedback | 0/4 | 0/4 | 0/4 | 0/2 | 0/4 |
| second-state/llm-compiler-7b-ftd-GGUF (compiler-ftd-feedback-v1) | formal | L1 | self_review | 2/4 | 0/4 | 0/4 | 0/2 | 0/4 |
| second-state/llm-compiler-7b-ftd-GGUF (compiler-ftd-feedback-v1) | formal | L1 | tool_feedback | 0/4 | 0/4 | 0/4 | 0/2 | 0/4 |
| second-state/llm-compiler-7b-ftd-GGUF (compiler-ftd-feedback-v1) | formal | L2 | self_review | 2/4 | 0/4 | 0/4 | 0/2 | 0/4 |
| second-state/llm-compiler-7b-ftd-GGUF (compiler-ftd-feedback-v1) | formal | L2 | tool_feedback | 0/4 | 0/4 | 0/4 | 0/2 | 0/4 |
| Qwen/Qwen2.5-Coder-7B-Instruct (qwen-feedback-v2-rechecked-ftd) | formal | L0 | self_review | 3/4 | 3/4 | 0/4 | 1/2 | 2/4 |
| Qwen/Qwen2.5-Coder-7B-Instruct (qwen-feedback-v2-rechecked-ftd) | formal | L0 | tool_feedback | 4/4 | 4/4 | 0/4 | 0/2 | 4/4 |
| Qwen/Qwen2.5-Coder-7B-Instruct (qwen-feedback-v2-rechecked-ftd) | formal | L1 | self_review | 4/4 | 2/4 | 2/4 | 1/2 | 1/4 |
| Qwen/Qwen2.5-Coder-7B-Instruct (qwen-feedback-v2-rechecked-ftd) | formal | L1 | tool_feedback | 4/4 | 3/4 | 1/4 | 1/2 | 2/4 |
| Qwen/Qwen2.5-Coder-7B-Instruct (qwen-feedback-v2-rechecked-ftd) | formal | L2 | self_review | 4/4 | 1/4 | 3/4 | 1/2 | 0/4 |
| Qwen/Qwen2.5-Coder-7B-Instruct (qwen-feedback-v2-rechecked-ftd) | formal | L2 | tool_feedback | 4/4 | 3/4 | 1/4 | 1/2 | 1/4 |

全部状态分布见 summary.json；逐题记录见 cases.csv。原始 IR、反例和诊断保存在各运行目录。
