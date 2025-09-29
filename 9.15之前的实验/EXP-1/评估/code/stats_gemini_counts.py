import json
import os
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib

# 颜色
COLORS = ["#CC7C71", "#925EB0", "#7E99F4", "#7AB656"]

# 目标目录（评估/gemini 或 gemini的结果）
candidate_dirs = [
    Path(__file__).resolve().parents[1] / 'gemini',
    Path(__file__).resolve().parents[1] / 'gemini的结果'
]
BASE_DIR = None
for d in candidate_dirs:
    if d.exists():
        BASE_DIR = d
        break
if BASE_DIR is None:
    existing = [p.name for p in Path(__file__).resolve().parents[1].iterdir() if p.is_dir()]
    raise SystemExit(f"未找到目标目录, 已有子目录: {existing}")

rows = []
for fp in BASE_DIR.glob('*.json'):
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取失败 {fp}: {e}")
        continue
    entities = data.get('entities', []) or []
    relations = data.get('relations', []) or []
    entity_types = {e.get('type') for e in entities if isinstance(e, dict) and e.get('type')}
    relation_types = {r.get('type') for r in relations if isinstance(r, dict) and r.get('type')}
    rows.append({
        'file': fp.name,
        'entity_count': len(entities),
        'entity_type_count': len(entity_types),
        'relation_count': len(relations),
        'relation_type_count': len(relation_types)
    })

if not rows:
    raise SystemExit('没有统计到任何数据')

df = pd.DataFrame(rows)
# 总计行
summary = {
    'file': 'TOTAL',
    'entity_count': df['entity_count'].sum(),
    'entity_type_count': df['entity_type_count'].sum(),  # 这里是各文件类型数量之和
    'relation_count': df['relation_count'].sum(),
    'relation_type_count': df['relation_type_count'].sum()
}
# 也计算全局唯一类型数量
all_entity_types = set()
all_relation_types = set()
for fp in BASE_DIR.glob('*.json'):
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        continue
    for e in data.get('entities', []) or []:
        if isinstance(e, dict) and e.get('type'):
            all_entity_types.add(e['type'])
    for r in data.get('relations', []) or []:
        if isinstance(r, dict) and r.get('type'):
            all_relation_types.add(r['type'])
summary['global_entity_type_unique'] = len(all_entity_types)
summary['global_relation_type_unique'] = len(all_relation_types)

summary_df = pd.DataFrame([summary])
print('汇总统计:')
print(summary_df.to_string(index=False))

# ================= 生成示例风格图 =================
# 统计文件篇数
total_files = len(df)

# 设置中文字体（优先黑体/微软雅黑）
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False

# 按示例的颜色顺序：紫、蓝、绿、肉粉
STYLE_COLORS = ["#925EB0", "#7E99F4", "#7AB656", "#CC7C71"]
labels = ['实体数量', '实体类型数量', '关系数量', '关系类型数量']
values = [
    summary['entity_count'],
    summary['global_entity_type_unique'],
    summary['relation_count'],
    summary['global_relation_type_unique']
]

plt.figure(figsize=(9,5))
bars = plt.bar(range(len(labels)), values, color=STYLE_COLORS, width=0.55)
for bar, v in zip(bars, values):
    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height()+max(values)*0.01, str(v),
             ha='center', va='bottom', fontsize=11)
plt.xticks(range(len(labels)), labels, fontsize=12)
plt.ylabel('数量', fontsize=12)
plt.title(f'gemini 模型实体和关系抽取数量统计（{total_files}篇）', fontsize=14, pad=12)
plt.ylim(0, max(values)*1.12)
plt.grid(axis='y', linestyle='--', alpha=0.3)
plt.tight_layout()
styled_png = BASE_DIR / 'gemini_overall_counts_styled.png'
plt.savefig(styled_png, dpi=150)
print(f'保存图表(示例风格): {styled_png}')

# 另存 CSV
out_csv = BASE_DIR / 'gemini_file_level_counts.csv'
df.to_csv(out_csv, index=False, encoding='utf-8-sig')
print(f'按文件统计已保存: {out_csv}')
