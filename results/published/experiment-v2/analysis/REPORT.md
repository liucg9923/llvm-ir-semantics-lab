# 当前可运行组的实验结果

Meta LLM Compiler 的官方访问申请仍待审核，未运行、未计分。以下不是完整三模型结论。

| 运行 | 分支 | 类别 | 合法 IR | 语义验证通过 | 有效优化 | 发现反例 |
|---|---|---|---:|---:|---:|---:|
| opt-v2 | initial | ALL | 24/24 | 24/24 | 12/12 | 0/24 |
| opt-v2 | initial | L0 | 8/8 | 8/8 | 4/4 | 0/8 |
| opt-v2 | initial | L1 | 8/8 | 8/8 | 4/4 | 0/8 |
| opt-v2 | initial | L2 | 8/8 | 8/8 | 4/4 | 0/8 |
| identity-v2 | initial | ALL | 24/24 | 24/24 | 0/12 | 0/24 |
| identity-v2 | initial | L0 | 8/8 | 8/8 | 0/4 | 0/8 |
| identity-v2 | initial | L1 | 8/8 | 8/8 | 0/4 | 0/8 |
| identity-v2 | initial | L2 | 8/8 | 8/8 | 0/4 | 0/8 |
| qwen-v2 | initial | ALL | 22/24 | 15/24 | 7/12 | 7/24 |
| qwen-v2 | initial | L0 | 6/8 | 6/8 | 2/4 | 0/8 |
| qwen-v2 | initial | L1 | 8/8 | 5/8 | 2/4 | 3/8 |
| qwen-v2 | initial | L2 | 8/8 | 4/8 | 3/4 | 4/8 |
| qwen-feedback-v2 | self_review | ALL | 11/12 | 6/12 | 3/6 | 5/12 |
| qwen-feedback-v2 | self_review | L0 | 3/4 | 3/4 | 1/2 | 0/4 |
| qwen-feedback-v2 | self_review | L1 | 4/4 | 2/4 | 1/2 | 2/4 |
| qwen-feedback-v2 | self_review | L2 | 4/4 | 1/4 | 1/2 | 3/4 |
| qwen-feedback-v2 | tool_feedback | ALL | 12/12 | 10/12 | 2/6 | 2/12 |
| qwen-feedback-v2 | tool_feedback | L0 | 4/4 | 4/4 | 0/2 | 0/4 |
| qwen-feedback-v2 | tool_feedback | L1 | 4/4 | 3/4 | 1/2 | 1/4 |
| qwen-feedback-v2 | tool_feedback | L2 | 4/4 | 3/4 | 1/2 | 1/4 |

## 同题配对的修订实验

三种条件都只统计预先选定的 12 题，其中 6 题具有优化目标。

| 条件 | 验证通过 | 有效优化 | 新获验证通过 | 失去验证通过 | 新发现的不安全回归 |
|---|---:|---:|---:|---:|---:|
| initial_matched | 7/12 | 4/6 | 0 | 0 | 0 |
| self_review | 6/12 | 3/6 | 0 | 1 | 1 |
| tool_feedback | 10/12 | 2/6 | 3 | 0 | 0 |

## 可审查的数据

- per_case.csv：每题结果、生成耗时和 token 数。
- paired_feedback.csv：每题修订前后的状态变化。
- summary.json：全部状态分布、汇总和范围限制。

未知、非法 IR、约束失败和工具异常不会混称为已证明的不安全变换。生成 Token 用各模型自身 tokenizer 统计，不当作跨模型完全等价的计算单位。
