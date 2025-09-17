# 实体类型计数统计

本目录包含对三个模型（`deepseek`、`gemini`、`kimi`）在50篇论文上的实体抽取结果的统计汇总。

- 输入位置：`E:\知识图谱构建\9.15之前的实验\EXP-3\抽取\数据结果\需要评估论文的抽取结果\{model}/*.json`
- 统计脚本：`E:\知识图谱构建\9.15之前的实验\EXP-3\抽取\code\count_entities_by_model_and_type.py`
- 输出文件：
  - `实体类型统计_按模型汇总.json`
  - `实体类型统计_按模型汇总.csv`

运行（Windows PowerShell）：

```powershell
&e:\conda\envs\prompt_exp\python.exe "E:\知识图谱构建\9.15之前的实验\EXP-3\抽取\code\count_entities_by_model_and_type.py"
```

说明：
- 每个模型按文件名排序后取前50篇进行统计。
- 结果CSV按“模型×实体类型”的矩阵展开，`total_files`列为实际计入的文件数。