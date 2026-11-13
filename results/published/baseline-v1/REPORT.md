# 实验结果

只将 mode=formal 的 opt/HF 记录作为正式实验；fixture/smoke 记录是评测器检查。
refuted 是已发现反例的比例，不是所有未知候选的真实错误率。每个数值保留分母。

| 选手/运行 | 模式 | 层级 | 分支 | 合法 IR | 验证通过 | 发现反例 | 有效优化 | 原样返回 |
|---|---|---|---|---:|---:|---:|---:|---:|
| opt (opt-v1) | formal | L0 | initial | 8/8 | 8/8 | 0/8 | 4/4 | 1/8 |
| opt (opt-v1) | formal | L1 | initial | 8/8 | 8/8 | 0/8 | 4/4 | 2/8 |
| opt (opt-v1) | formal | L2 | initial | 8/8 | 8/8 | 0/8 | 4/4 | 4/8 |
| identity (identity-v1) | fixture | L0 | initial | 8/8 | 8/8 | 0/8 | 0/4 | 8/8 |
| identity (identity-v1) | fixture | L1 | initial | 8/8 | 8/8 | 0/8 | 0/4 | 8/8 |
| identity (identity-v1) | fixture | L2 | initial | 8/8 | 8/8 | 0/8 | 0/4 | 8/8 |

全部状态分布见 summary.json；逐题记录见 cases.csv。原始 IR、反例和诊断保存在各运行目录。
