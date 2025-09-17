import json
import csv
from pathlib import Path
from collections import Counter

# Config
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / '数据结果' / '提取结果_by_gemini'
OUT_DIR = ROOT / '数据结果'
OUT_DIR.mkdir(parents=True, exist_ok=True)

PER_ARTICLE_CSV = OUT_DIR / 'gemini_relations_per_article.csv'
TYPE_COUNTS_CSV = OUT_DIR / 'gemini_relations_by_type.csv'
SUMMARY_JSON = OUT_DIR / 'gemini_relations_summary.json'


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
        # normalize
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


def main():
    files = sorted(DATA_DIR.glob('*.json'))
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

    with PER_ARTICLE_CSV.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['file', 'relations_count', 'unique_relation_types_count'])
        writer.writeheader()
        writer.writerows(per_article_rows)

    with TYPE_COUNTS_CSV.open('w', newline='', encoding='utf-8') as f:
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

    with SUMMARY_JSON.open('w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
