import os
import json
from collections import defaultdict

def count_relations_and_types(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    relations = data.get('relations', [])
    num_relations = len(relations)
    relation_types = set(rel['type'] for rel in relations)
    num_types = len(relation_types)
    return num_relations, num_types

def main():
    base_dir = r'e:\知识图谱构建\9.15之前的实验\EXP-1\数据结果'
    models = ['deepseek', 'gemini', 'kimi']
    results = {}

    for model in models:
        in_scope_dir = os.path.join(base_dir, f'提取结果_by_{model}', 'in_scope')
        if not os.path.exists(in_scope_dir):
            print(f"Directory not found: {in_scope_dir}")
            continue

        total_relations = 0
        total_unique_types = set()
        paper_stats = []

        for file in os.listdir(in_scope_dir):
            if file.endswith('.json'):
                file_path = os.path.join(in_scope_dir, file)
                num_rel, num_types = count_relations_and_types(file_path)
                total_relations += num_rel
                total_unique_types.update([f"{rel['type']}" for rel in json.load(open(file_path, 'r', encoding='utf-8')).get('relations', [])])
                paper_stats.append((file, num_rel, num_types))

        results[model] = {
            'total_relations': total_relations,
            'total_unique_types': len(total_unique_types),
            'paper_stats': paper_stats
        }

    # Print results
    for model, stats in results.items():
        print(f"\nModel: {model}")
        print(f"Total relations: {stats['total_relations']}")
        print(f"Total unique relation types: {stats['total_unique_types']}")
        print("Per paper stats (first 5):")
        for paper, rel, typ in stats['paper_stats'][:5]:
            print(f"  {paper}: relations={rel}, types={typ}")

if __name__ == "__main__":
    main()