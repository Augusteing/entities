import pandas as pd

# 读取数据
df = pd.read_csv('evaluation_papers_entity_type_counts.csv')

# 计算每个模型的top3
models = ['gemini', 'deepseek', 'kimi']

for model in models:
    print(f"\n{model.upper()} Top 3:")
    model_data = df[df[model] > 0].sort_values(model, ascending=False).head(3)
    for i, (idx, row) in enumerate(model_data.iterrows(), 1):
        print(f"  {i}. {row['type']}: {row[model]}")