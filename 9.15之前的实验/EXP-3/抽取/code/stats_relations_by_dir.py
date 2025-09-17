import json
import csv
import argparse
from pathlib import Path
from collections import Counter


def load_relations(path: Path):
    try:
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list) and data:
            item = data[0]
        elif isinstance(data, dict):
            item = data
        else:
            return []
        rels = item.get('relations', [])
        norm = []
        for r in rels:
            if isinstance(r, dict):
                rtype = r.get('type') or r.get('label')
                head = r.get('head')
                tail = r.get('tail')
                if rtype is None:
                    continue
                norm.append({'type': str(rtype), 'head': head, 'tail': tail})
        return norm
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return []


def run(input_dir: Path, out_dir: Path, out_prefix: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    per_article_csv = out_dir / f'{out_prefix}_relations_per_article.csv'
    type_counts_csv = out_dir / f'{out_prefix}_relations_by_type.csv'
    summary_json = out_dir / f'{out_prefix}_relations_summary.json'

    files = sorted(input_dir.glob('*.json'))
    per_article_rows = []
    global_type_counter = Counter()
    total_relations = 0

    for fp in files:
        rels = load_relations(fp)
        cnt = len(rels)
        total_relations += cnt
        type_counter = Counter(r['type'] for r in rels)
        global_type_counter.update(type_counter)
        per_article_rows.append({
            'file': fp.name,
            'relations_count': cnt,
            'unique_relation_types_count': len(type_counter),
        })

    with per_article_csv.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['file', 'relations_count', 'unique_relation_types_count'])
        writer.writeheader()
        writer.writerows(per_article_rows)

    with type_counts_csv.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['type', 'count'])
        writer.writeheader()
        for t, c in sorted(global_type_counter.items(), key=lambda x: (-x[1], x[0])):
            writer.writerow({'type': t, 'count': c})

    summary = {
        'articles_count': len(per_article_rows),
        'total_relations': total_relations,
        'unique_relation_types_total': len(global_type_counter),
        'top_relation_types': [{ 'type': t, 'count': c } for t, c in global_type_counter.most_common(20)],
    }

    with summary_json.open('w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        'prefix': out_prefix,
        **summary
    }, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir', required=True, help='目录：包含各文章的JSON抽取结果')
    parser.add_argument('--out-dir', required=False, default=None, help='输出目录，默认与输入同级的父目录/数据结果')
    parser.add_argument('--prefix', required=True, help='输出文件名前缀，如 gemini / kimi / deepseek')
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    if not input_dir.exists():
        raise SystemExit(f'Input dir not found: {input_dir}')

    if args.out_dir:
        out_dir = Path(args.out_dir).resolve()
    else:
        # 默认写到输入目录的上级目录（数据结果）
        out_dir = input_dir.parent

    run(input_dir, out_dir, args.prefix)


if __name__ == '__main__':
    main()
