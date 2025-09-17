import json
import os
import csv
from collections import Counter, defaultdict


TARGET_ROOT = os.path.join(
    'e:\\知识图谱构建\\9.15之前的实验\\EXP-3',
    '抽取', '数据结果', '需要评估论文的抽取结果'
)

MODELS = ['deepseek', 'gemini', 'kimi']
MAX_FILES_PER_MODEL = 50


def list_json_files(folder: str):
    files = [f for f in os.listdir(folder) if f.lower().endswith('.json')]
    files.sort()  # 稳定排序，确保前50一致
    return [os.path.join(folder, f) for f in files]


def load_entities(json_path: str):
    try:
        with open(json_path, 'r', encoding='utf-8') as fp:
            data = json.load(fp)
        entities = data.get('entities', [])
        # 规范化：仅接受包含type的项
        return [e for e in entities if isinstance(e, dict) and 'type' in e]
    except Exception as e:
        print(f"读取失败: {json_path} -> {e}")
        return []


def count_by_type_for_model(model_dir: str, limit: int = MAX_FILES_PER_MODEL):
    files = list_json_files(model_dir)
    selected = files[:limit]

    type_counter = Counter()
    per_file_counts = {}

    for fp in selected:
        ents = load_entities(fp)
        c = Counter(e['type'] for e in ents)
        per_file_counts[os.path.basename(fp)] = dict(c)
        type_counter.update(c)

    return {
        'total_files_counted': len(selected),
        'type_counts': dict(type_counter),
        'per_file_counts': per_file_counts,
    }


def main():
    if not os.path.isdir(TARGET_ROOT):
        raise SystemExit(f"目标目录不存在: {TARGET_ROOT}")

    results = {}
    all_types = set()

    for model in MODELS:
        model_dir = os.path.join(TARGET_ROOT, model)
        if not os.path.isdir(model_dir):
            print(f"警告: 模型目录不存在 -> {model_dir}")
            continue
        stats = count_by_type_for_model(model_dir)
        results[model] = stats
        all_types.update(stats['type_counts'].keys())

    # 输出目录
    out_dir = os.path.join('e:\\知识图谱构建\\9.15之前的实验\\EXP-3', '抽取', '数据结果', '统计')
    os.makedirs(out_dir, exist_ok=True)

    # 保存JSON汇总
    json_out = os.path.join(out_dir, '实体类型统计_按模型汇总.json')
    with open(json_out, 'w', encoding='utf-8') as fp:
        json.dump(results, fp, ensure_ascii=False, indent=2)

    # 保存CSV（按模型×类型的矩阵）
    all_types_sorted = sorted(all_types)
    csv_out = os.path.join(out_dir, '实体类型统计_按模型汇总.csv')
    with open(csv_out, 'w', encoding='utf-8', newline='') as fp:
        writer = csv.writer(fp)
        header = ['model', 'total_files'] + all_types_sorted
        writer.writerow(header)
        for model in MODELS:
            if model not in results:
                continue
            row = [model, results[model]['total_files_counted']]
            for t in all_types_sorted:
                row.append(results[model]['type_counts'].get(t, 0))
            writer.writerow(row)

    # 控制台打印简要摘要
    print('统计完成:')
    for model in MODELS:
        stats = results.get(model)
        if not stats:
            continue
        print(f"- {model}: 文件数={stats['total_files_counted']}, 实体类型数={len(stats['type_counts'])}, 实体总数={sum(stats['type_counts'].values())}")
    print(f"输出: {json_out}\n     {csv_out}")


if __name__ == '__main__':
    main()
