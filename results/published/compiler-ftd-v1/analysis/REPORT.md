# 三方同题比较

专用组使用社区 LLM Compiler 7B-FTD F16 GGUF；它不同于原计划的官方基础模型，且与 Qwen 的推理后端不同。所有原始输出保留。

| 组别 | 层级 | 合法 IR | 验证通过 | 有效优化 | 已证反例 |
|---|---|---:|---:|---:|---:|
| opt | ALL | 24/24 | 24/24 | 12/12 | 0 |
| opt | L0 | 8/8 | 8/8 | 4/4 | 0 |
| opt | L1 | 8/8 | 8/8 | 4/4 | 0 |
| opt | L2 | 8/8 | 8/8 | 4/4 | 0 |
| identity | ALL | 24/24 | 24/24 | 0/12 | 0 |
| identity | L0 | 8/8 | 8/8 | 0/4 | 0 |
| identity | L1 | 8/8 | 8/8 | 0/4 | 0 |
| identity | L2 | 8/8 | 8/8 | 0/4 | 0 |
| qwen | ALL | 22/24 | 15/24 | 7/12 | 7 |
| qwen | L0 | 6/8 | 6/8 | 2/4 | 0 |
| qwen | L1 | 8/8 | 5/8 | 2/4 | 3 |
| qwen | L2 | 8/8 | 4/8 | 3/4 | 4 |
| compiler_ftd | ALL | 21/24 | 0/24 | 0/12 | 0 |
| compiler_ftd | L0 | 8/8 | 0/8 | 0/4 | 0 |
| compiler_ftd | L1 | 6/8 | 0/8 | 0/4 | 0 |
| compiler_ftd | L2 | 7/8 | 0/8 | 0/4 | 0 |

## 同题反馈（每组 12 题，其中 6 个优化机会）

| 模型 | 条件 | 验证通过 | 有效优化 | 已证反例 |
|---|---|---:|---:|---:|
| qwen | initial_matched | 7/12 | 4/6 | 4 |
| qwen | self_review | 6/12 | 3/6 | 5 |
| qwen | tool_feedback | 10/12 | 2/6 | 2 |
| compiler_ftd | initial_matched | 0/12 | 0/6 | 0 |
| compiler_ftd | self_review | 0/12 | 0/6 | 0 |
| compiler_ftd | tool_feedback | 0/12 | 0/6 | 0 |
