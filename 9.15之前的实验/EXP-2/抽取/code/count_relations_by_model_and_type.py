import json
import os
import csv
from collections import Counter


TARGET_ROOT = os.path.join(
    'e:\\知识图谱构建\\9.15之前的实验\\EXP-3',
    '抽取', '数据结果', '需要评估论文的抽取结果'
)
OUT_DIR = os.path.join('e:\\知识图谱构建\\9.15之前的实验\\EXP-3', '抽取', '数据结果', '统计')
MODELS = ['deepseek', 'gemini', 'kimi']
MAX_FILES_PER_MODEL = 50


def list_json_files(folder: str):
    files = [f for f in os.listdir(folder) if f.lower().endswith('.json')]
    files.sort()
    return [os.path.join(folder, f) for f in files]


def load_relations(json_path: str):
    try:
        with open(json_path, 'r', encoding='utf-8') as fp:
            data = json.load(fp)
        relations = data.get('relations', [])
        return [r for r in relations if isinstance(r, dict) and 'type' in r]
    except Exception as e:
        print(f"读取失败: {json_path} -> {e}")
        return []


def count_by_type_for_model(model_dir: str, limit: int = MAX_FILES_PER_MODEL):
    files = list_json_files(model_dir)
    selected = files[:limit]
    type_counter = Counter()
    total = 0
    for fp in selected:
        rels = load_relations(fp)
        total += len(rels)
        type_counter.update([r['type'] for r in rels])
    return {
        'total_files_counted': len(selected),
        'relation_total': total,
        'relation_type_counts': dict(type_counter),
    }


def main():
    if not os.path.isdir(TARGET_ROOT):
        raise SystemExit(f"目标目录不存在: {TARGET_ROOT}")
    os.makedirs(OUT_DIR, exist_ok=True)

    results = {}
    all_types = set()
    for model in MODELS:
        model_dir = os.path.join(TARGET_ROOT, model)
        if not os.path.isdir(model_dir):
            print(f"警告: 模型目录不存在 -> {model_dir}")
            continue
        stats = count_by_type_for_model(model_dir)
        results[model] = stats
        all_types.update(stats['relation_type_counts'].keys())

    # 保存JSON
    json_out = os.path.join(OUT_DIR, '关系类型统计_按模型汇总.json')
    with open(json_out, 'w', encoding='utf-8') as fp:
        json.dump(results, fp, ensure_ascii=False, indent=2)

    # 保存CSV（模型 × 关系类型）
    types_sorted = sorted(all_types)
    csv_out = os.path.join(OUT_DIR, '关系类型统计_按模型汇总.csv')
    with open(csv_out, 'w', encoding='utf-8', newline='') as fp:
        writer = csv.writer(fp)
        header = ['model', 'total_files', 'relation_total', 'relation_type_count'] + types_sorted
        writer.writerow(header)
        for model in MODELS:
            if model not in results:
                continue
            stats = results[model]
            row = [model, stats['total_files_counted'], stats['relation_total'], len(stats['relation_type_counts'])]
            for t in types_sorted:
                row.append(stats['relation_type_counts'].get(t, 0))
            writer.writerow(row)

    # 控制台摘要
    print('关系统计完成:')
    for model in MODELS:
        if model not in results:
            continue
        stats = results[model]
        print(f"- {model}: files={stats['total_files_counted']}, relation_total={stats['relation_total']}, relation_type_count={len(stats['relation_type_counts'])}")
    print('输出:', json_out)
    print('输出:', csv_out)


if __name__ == '__main__':
    main()
