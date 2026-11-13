# 开发阶段的解码配置修正

在首次 6 道开发题运行后、正式模型实验之前，检查到 Qwen 检查点自带 repetition_penalty=1.1。为避免模型之间继承不同的默认解码参数，协议 v2 使用独立 GenerationConfig，显式设置 greedy、num_beams=1、repetition_penalty=1.0、no_repeat_ngram_size=0，并保留各模型所需的 BOS/EOS/Pad 标识。

任务、提示词文本、few-shot 例子和优化目标没有调整。原始开发运行 qwen-dev-v1 及其配置快照保留，不计入正式结果。重新冻结配置、重新验收工具链并生成 opt-v2/identity-v2 基线后再运行正式模型组。这是执行控制修正，不是根据正式成绩调参。
