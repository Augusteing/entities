import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / '数据结果'
BEFORE_DIR = DATA_DIR / '提取结果_by_gemini'
EVAL_PAPERS_DIR = ROOT / '评估' / '需要评估的论文'


def load_json_merge(path: Path):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None
    if isinstance(data, dict):
        ents = data.get('entities') or []
        return {'entities': ents if isinstance(ents, list) else []}
    if isinstance(data, list):
        merged = {'entities': []}
        for it in data:
            if isinstance(it, dict):
                ents = it.get('entities') or []
                if isinstance(ents, list):
                    merged['entities'].extend(ents)
        return merged
    return None


def main():
    if not EVAL_PAPERS_DIR.exists():
        print('[ERROR] 缺少评估论文目录:', EVAL_PAPERS_DIR)
        return
    stems = {p.stem for p in EVAL_PAPERS_DIR.glob('*.md')}
    if not stems:
        print('[ERROR] 未找到评估论文文件')
        return
    if not BEFORE_DIR.exists():
        print('[ERROR] 缺少增补前目录:', BEFORE_DIR)
        return

    target_entity_type = '作者'
    hit_files: list[tuple[str, list[str]]] = []  # (stem, author_texts)
    miss_files: list[str] = []

    for stem in sorted(stems):
        p = BEFORE_DIR / f'{stem}.json'
        if not p.exists():
            miss_files.append(stem)
            continue
        data = load_json_merge(p)
        if not data:
            miss_files.append(stem)
            continue
        authors = []
        for e in data['entities']:
            t = e.get('type')
            if t == target_entity_type:
                txt = e.get('text') or e.get('name') or ''
                if isinstance(txt, str) and txt:
                    authors.append(txt)
        if authors:
            hit_files.append((stem, authors))

    print(f'在增补前即包含“{target_entity_type}”实体的论文数量: {len(hit_files)} / {len(stems)}')
    if hit_files:
        print('\n文件清单（stem -> 作者实体样例）:')
        for stem, authors in hit_files:
            # 仅展示前3个作者文本以免过长
            sample = authors[:3]
            # 明确逐行打印，避免某些控制台合并输出
            print('-', stem, '->', sample)
        # 同时给出仅stem的汇总，便于复制
        stems_only = [s for s, _ in hit_files]
        print('\n命中的stem清单:')
        print(','.join(stems_only))

    if miss_files:
        # 这些是因找不到JSON或读入失败而未统计到的stem，供参考
        print('\n[提示] 以下stem未能参与统计（缺文件或结构异常）:')
        for s in miss_files:
            print('-', s)


if __name__ == '__main__':
    main()
