import pandas as pd
import json

df = pd.read_excel("关系定义.xlsx")  

# 标准字段重命名，防止中文列名不同步（可根据实际列名调整）
df.columns = ['主语实体', '关系', '标签','宾语实体', '示例']

# 构造 JSON 列表
relations = []
for _, row in df.iterrows():
    relations.append({
        "relation": row['关系'],
        "relation_label": row['标签'],
        "subject_type": row['主语实体'],
        "object_type": row['宾语实体'],
        "example": row['示例']
    })

# 保存为 JSON 文件
with open("relations.json", "w", encoding="utf-8") as f:
    json.dump(relations, f, ensure_ascii=False, indent=2)

print("✅ 关系定义已保存为 relations.json")

