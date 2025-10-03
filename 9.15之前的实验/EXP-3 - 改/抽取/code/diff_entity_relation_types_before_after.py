import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / '数据结果'
# 根据用户要求：
# 增补前 数据目录 = 提取结果_by_gemini
# 增补后 数据目录 = 提取结果_by_gemini/存档
BEFORE_DIR = DATA_DIR / '提取结果_by_gemini'
AFTER_DIR = BEFORE_DIR / '存档'
EVAL_PAPERS_DIR = ROOT / '评估' / '需要评估的论文'


def load_json_merge(path: Path):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None
    if isinstance(data, dict):
        ents = data.get('entities') or []
        rels = data.get('relations') or []
        return {'entities': ents if isinstance(ents, list) else [], 'relations': rels if isinstance(rels, list) else []}
    if isinstance(data, list):
        merged = {'entities': [], 'relations': []}
        for it in data:
            if isinstance(it, dict):
                ents = it.get('entities') or []
                rels = it.get('relations') or []
                if isinstance(ents, list):
                    merged['entities'].extend(ents)
                if isinstance(rels, list):
                    merged['relations'].extend(rels)
        return merged
    return None


def collect_types(dir_path: Path, stems: set[str]):
    e_types = set()
    r_types = set()
    for s in stems:
        p = dir_path / f'{s}.json'
        if not p.exists():
            # 评估发送结果等命名差异不处理，这里仅比较提取结果
            continue
        data = load_json_merge(p)
        if not data:
            continue
        for e in data['entities']:
            t = e.get('type')
            if isinstance(t, str) and t:
                e_types.add(t)
        for r in data['relations']:
            t = r.get('type') or r.get('relation')
            if isinstance(t, str) and t:
                r_types.add(t)
    return e_types, r_types


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
    if not AFTER_DIR.exists():
        print('[WARN] 未找到增补后目录(存档):', AFTER_DIR)
        print('      仍将仅统计增补前目录。')

    before_e, before_r = collect_types(BEFORE_DIR, stems)
    after_e, after_r = (set(), set())
    if AFTER_DIR.exists():
        after_e, after_r = collect_types(AFTER_DIR, stems)

    print('[COUNT] 增补前(提取结果_by_gemini) 实体类型数:', len(before_e), '关系类型数:', len(before_r))
    print('[COUNT] 增补后(存档) 实体类型数:', len(after_e), '关系类型数:', len(after_r))

    # 交集
    inter_e = before_e & after_e
    inter_r = before_r & after_r
    # 各自独有（不在交集中的）
    before_only_e = before_e - inter_e
    before_only_r = before_r - inter_r
    after_only_e = after_e - inter_e
    after_only_r = after_r - inter_r

    print('\n[INTERSECTION] 实体类型交集数量:', len(inter_e))
    print('[INTERSECTION] 关系类型交集数量:', len(inter_r))
    print('\n[UNIQUE BEFORE] 仅增补前有的实体类型(数量 {}):'.format(len(before_only_e)))
    print(sorted(before_only_e))
    print('[UNIQUE BEFORE] 仅增补前有的关系类型(数量 {}):'.format(len(before_only_r)))
    print(sorted(before_only_r))
    print('\n[UNIQUE AFTER] 仅增补后有的实体类型(数量 {}):'.format(len(after_only_e)))
    print(sorted(after_only_e))
    print('[UNIQUE AFTER] 仅增补后有的关系类型(数量 {}):'.format(len(after_only_r)))
    print(sorted(after_only_r))


if __name__ == '__main__':
    main()
