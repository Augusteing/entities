import pandas as pd

# 读取CSV文件
df = pd.read_csv('common_docs_entity_type_counts.csv')

# 统计每个模型抽取了多少种不同类别的实体（只计算数值大于0的情况）
models = ['gemini', 'deepseek', 'kimi']
results = {}

for model in models:
    # 计算该模型中数值大于0的实体类型数量
    count = (df[model] > 0).sum()
    results[model] = count

# 打印结果
print("各模型抽取的实体类型数量统计：")
print("=" * 40)
for model, count in results.items():
    print(f"{model.capitalize()}: {count} 种实体类型")

print("\n详细说明：")
print("- 只有当模型对某个实体类型的抽取数量大于0时，才计算为该模型抽取过该类型")
print("- 例如：Agent类型中，gemini为0（不计入），deepseek为23（计入），kimi为7（计入）")

# 可选：显示每个模型抽取的具体实体类型
print("\n" + "=" * 50)
print("每个模型抽取的具体实体类型：")

for model in models:
    extracted_types = df[df[model] > 0]['type'].tolist()
    print(f"\n{model.capitalize()} 抽取的实体类型 ({len(extracted_types)} 种):")
    for i, entity_type in enumerate(extracted_types[:10], 1):  # 只显示前10个
        print(f"  {i}. {entity_type}")
    if len(extracted_types) > 10:
        print(f"  ... 还有 {len(extracted_types) - 10} 种类型")

# 创建对比表格
comparison_df = pd.DataFrame({
    'Model': models,
    'Entity Types Count': [results[model] for model in models]
})

print(f"\n{'='*30}")
print("汇总对比表：")
print(comparison_df.to_string(index=False))