import json
import csv
from pathlib import Path
from collections import Counter, defaultdict

# Config
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / '数据结果' / '提取结果_by_gemini'
OUT_DIR = ROOT / '数据结果'
OUT_DIR.mkdir(parents=True, exist_ok=True)

PER_ARTICLE_CSV = OUT_DIR / 'gemini_entities_per_article.csv'
TYPE_COUNTS_CSV = OUT_DIR / 'gemini_entities_by_type.csv'
SUMMARY_JSON = OUT_DIR / 'gemini_entities_summary.json'


def load_entities(path: Path):
    try:
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        # Expect list with first item containing 'entities'
        if isinstance(data, list) and data:
            item = data[0]
        elif isinstance(data, dict):
            item = data
        else:
            return []
        entities = item.get('entities', [])
        # Normalize: keep dicts with keys 'type' and optional 'text'
        norm = []
        for e in entities:
            if isinstance(e, dict):
                etype = e.get('type')
                text = e.get('text')
                if etype is None and 'label' in e:
                    etype = e['label']
                if etype is None:
                    # skip malformed entity
                    continue
                norm.append({'type': str(etype), 'text': text})
        return norm
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return []


def main():
    files = sorted(DATA_DIR.glob('*.json'))
    per_article_rows = []
    global_type_counter = Counter()
    total_entities = 0

    for fp in files:
        ents = load_entities(fp)
        cnt = len(ents)
        total_entities += cnt
        type_counter = Counter(e['type'] for e in ents)
        # accumulate global type counts
        global_type_counter.update(type_counter)

        per_article_rows.append({
            'file': fp.name,
            'entities_count': cnt,
            'unique_types_count': len(type_counter),
        })

    # write per-article counts
    with PER_ARTICLE_CSV.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['file', 'entities_count', 'unique_types_count'])
        writer.writeheader()
        writer.writerows(per_article_rows)

    # write type counts
    with TYPE_COUNTS_CSV.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['type', 'count'])
        writer.writeheader()
        for t, c in sorted(global_type_counter.items(), key=lambda x: (-x[1], x[0])):
            writer.writerow({'type': t, 'count': c})

    summary = {
        'articles_count': len(per_article_rows),
        'total_entities': total_entities,
        'unique_types_total': len(global_type_counter),
        'top_types': [{ 'type': t, 'count': c } for t, c in global_type_counter.most_common(20)],
    }

    with SUMMARY_JSON.open('w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
