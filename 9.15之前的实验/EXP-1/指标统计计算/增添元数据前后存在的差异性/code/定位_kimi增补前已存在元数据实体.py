"""定位 Kimi 模型增补前就已存在的元数据实体。

输出三个 CSV 到 本目录上级的 结果/ ：
 1) kimi_元数据期望集合.csv              (期望 364 条)
 2) kimi_元数据期望_增补前已存在.csv      (交集，预期 1 条)
 3) kimi_元数据期望_增补前缺失需注入.csv  (差集，预期 363 条)

判定逻辑：
 期望集合来源：抽取端聚合元数据文件 (与抽取阶段 填充元数据.py 使用同一文件)。
 增补前实体集合：抽取/数据结果/增补前/提取结果_by_kimi/in_scope 下所有 JSON 中的实体，按 (text.lower().strip(), type) 去重。

依赖：复用 抽取/code/填充脚本/填充元数据.py 中的 parse_metadata_file 与 normalize 标准，需要复制最小必要逻辑，避免直接 import 相对路径复杂。
"""
from __future__ import annotations
import json, re, csv
from pathlib import Path
from typing import List, Dict, Tuple

# 与原脚本一致的解析正则
RE_TITLE = re.compile(r"(?m)^Title-题名:\s*(.+)")
RE_AUTHOR = re.compile(r"(?m)^Author-作者:\s*(.+)")
RE_ORGAN = re.compile(r"(?m)^Organ-机构:\s*(.+)")
RE_PUB = re.compile(r"(?m)^PubTime-出版时间:\s*(.+)")
RE_RECORD = re.compile(r"(?m)^Title-题名:.*?(?=^Title-题名:|\Z)", re.DOTALL)

def _split_items(s: str) -> List[str]:
    parts = re.split(r"[;；、，,]+", s)
    items = [p.strip() for p in parts if p and p.strip()]
    items = [re.sub(r"^[\-—·•]\s*", "", it) for it in items]
    return items

def parse_metadata_file(path: Path) -> List[Dict[str, object]]:
    text = path.read_text(encoding='utf-8', errors='ignore')
    records = []
    for block in RE_RECORD.findall(text):
        title_m = RE_TITLE.search(block)
        if not title_m:
            continue
        title = title_m.group(1).strip()
        authors_m = RE_AUTHOR.search(block)
        orgs_m = RE_ORGAN.search(block)
        pub_m = RE_PUB.search(block)
        authors = _split_items(authors_m.group(1)) if authors_m else []
        orgs = _split_items(orgs_m.group(1)) if orgs_m else []
        pub_time = pub_m.group(1).strip() if pub_m else ""
        if title:
            records.append({"title": title, "authors": authors, "orgs": orgs, "pub_time": pub_time})
    return records

def entity_sign(text: str, typ: str) -> Tuple[str, str]:
    return (text.strip().lower(), typ.strip())

def normalize_name(s: str) -> str:
    return re.sub(r"[\s_\-—:：,，；;·•.!！?？'""()（）\[\]【】]", "", s).lower()

def build_meta_index(metas: List[Dict[str, object]]):
    pairs = []
    for m in metas:
        t = str(m.get('title','')).strip()
        if not t: continue
        pairs.append((normalize_name(t), m))
    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    return pairs

def find_meta_for_stem(stem: str, indexed) -> Dict[str, object] | None:
    ns = normalize_name(stem)
    for nt, m in indexed:
        if ns.startswith(nt):
            return m
    return None

def main():
    script_dir = Path(__file__).resolve().parent
    root = script_dir.parents[2]
    meta_file = Path(r"E:\知识图谱构建\文献信息\PHM-217篇摘要.txt")
    if not meta_file.exists():
        print('[ERROR] 元数据文件不存在:', meta_file)
        return
    metas = parse_metadata_file(meta_file)
    indexed = build_meta_index(metas)

    pre_dir = root / '抽取' / '数据结果' / '增补前' / '提取结果_by_kimi' / 'in_scope'
    if not pre_dir.exists():
        print('[ERROR] 未找到增补前目录:', pre_dir)
        return

    expected_set = set()  # 只聚合这 50 篇对应的元数据实体
    pre_seen = set()
    file_count = 0
    for jp in sorted(pre_dir.glob('*.json')):
        file_count += 1
        meta = find_meta_for_stem(jp.stem, indexed)
        if meta:
            title = str(meta.get('title','')).strip()
            if title:
                expected_set.add(entity_sign(title,'论文'))
            for a in meta.get('authors', []):  # type: ignore
                if a: expected_set.add(entity_sign(str(a),'作者'))
            for o in meta.get('orgs', []):  # type: ignore
                if o: expected_set.add(entity_sign(str(o),'发表单位'))
            pub = str(meta.get('pub_time','')).strip()
            if pub:
                expected_set.add(entity_sign(pub,'发表时间'))
        # 收集增补前已有
        try:
            data = json.loads(jp.read_text(encoding='utf-8'))
        except Exception:
            continue
        if isinstance(data, list) and data and isinstance(data[0], dict):
            entities = data[0].get('entities') or []
        elif isinstance(data, dict):
            entities = data.get('entities') or []
        else:
            continue
        for e in entities:
            t = str(e.get('text',''))
            ty = str(e.get('type',''))
            if ty in ('论文','作者','发表单位','发表时间') and t.strip():
                pre_seen.add(entity_sign(t, ty))

    already = sorted(expected_set & pre_seen)
    missing = sorted(expected_set - pre_seen)
    final_union = sorted(expected_set)

    out_dir = script_dir.parent / '结果'
    out_dir.mkdir(parents=True, exist_ok=True)

    def write_csv(path: Path, rows: List[Tuple[str,str]], tag: str):
        with path.open('w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f); w.writerow(['文本(归一)','类型', '集合'])
            for ntext, typ in rows:
                w.writerow([ntext, typ, tag])

    write_csv(out_dir / 'kimi_元数据期望集合.csv', final_union, '期望')
    write_csv(out_dir / 'kimi_元数据期望_增补前已存在.csv', already, '增补前已存在')
    write_csv(out_dir / 'kimi_元数据期望_增补前缺失需注入.csv', missing, '增补前缺失')

    # 类型分布
    def dist(rows):
        from collections import Counter
        c = Counter(t for _, t in rows)
        return dict(c)

    print(f'[INFO] 文件数(预期 50): {file_count}')
    print(f'[INFO] 期望唯一实体数: {len(final_union)} 分布: {dist(final_union)}')
    print(f'[INFO] 增补前已存在: {len(already)} 分布: {dist(already)}')
    print(f'[INFO] 增补前缺失需注入: {len(missing)} 分布: {dist(missing)}')
    if len(already) == 1 and len(final_union) == 364 and len(missing) == 363:
        print('[INFO] 数量符合预期 (364 = 1 已有 + 363 缺失)')
    else:
        print('[WARN] 若与预期不符，请核对元数据文件或标题匹配逻辑。')

if __name__ == '__main__':
    main()
