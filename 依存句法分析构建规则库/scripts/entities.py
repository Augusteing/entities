import pandas as pd
import json

# 读取Excel
df = pd.read_excel("实体定义.xlsx")  # 或csv

# 分组构建结构
result = []
for category, group in df.groupby('类别'):
    types = []
    for _, row in group.iterrows():
        types.append({
            "type": row['实体类型'],
            "label": row['标签'],
            "description": row['说明']
        })
    result.append({
        "category": category,
        "types": types
    })

# 保存为JSON
with open("entities.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

