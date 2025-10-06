# -*- coding: utf-8 -*-
"""向 指标三：模型打分/打分结果 中注入摘要元数据 (论文/作者/发表单位/发表时间)

逻辑与抽取阶段的 `填充元数据.py` 类似，但有差异:
 1. 目标目录: ROOT/指标统计计算/指标三：模型打分/打分结果/<model>/*.json
 2. 所有新增实体与关系均添加字段 evaluation="正确"
 3. 仅当同 type+text (不区分大小写) 不存在时才新增 (幂等)
 4. 关系新增去重依据 (head, tail, type) 不区分大小写
 5. 可选写入 source="metadata_rule" 标识 (默认开启, 可通过 --no-source 关闭)

新增实体类型: 论文 / 作者 / 发表单位 / 发表时间
新增关系类型: 撰写(作者->论文) / 隶属(首作者->首机构) / 发表于(论文->发表时间)

输出: 终端汇总 + 可选 CSV (开启 --write-csv)
  CSV 路径: 指标统计计算/指标三：模型打分/统计结果/打分结果_元数据填充汇总.csv

用法:
  python 填充打分结果元数据.py --metadata-file "E:/.../PHM-217篇摘要.txt"
  python 填充打分结果元数据.py --models deepseek,gemini --dry-run

幂等: 重复执行第二次新增=0
"""
from __future__ import annotations
import argparse, json, re, csv
from pathlib import Path
from typing import List, Dict, Tuple, Any

"""
通用化改造说明 (不改变填充/去重/注入逻辑):
1. 去除硬编码 ROOT=EXP-1, 新增 auto_detect_root(): 自下而上寻找包含
   '指标统计计算/指标三：模型打分/打分结果' 目录的根。
2. 新增 CLI 参数:
   --root <path>            手动指定实验根 (包含 指标统计计算)
   --score-base <path>      直接指定打分结果根 (覆盖 root 下默认路径)
   --out-stat-dir <path>    指定统计输出目录 (默认 root/指标统计计算/指标三：模型打分/统计结果)
   --debug                  输出调试信息
3. 其它填充逻辑 (evaluation='正确'、幂等、source 字段) 原样保留。
4. 兼容旧调用: 不加 --root 时自动探测; 不加 --score-base 时按标准结构。
"""

def auto_detect_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / '指标统计计算' / '指标三：模型打分' / '打分结果').is_dir():
            return p
    # fallback: 返回脚本上三级 (尽量模拟旧结构)
    try:
        return start.parents[3]
    except Exception:
        return start

# 延迟初始化这两个路径 (在 main 中赋值)
SCORED_BASE: Path | None = None
OUT_STAT_DIR: Path | None = None

# ---------------- Metadata parse (复用抽取脚本逻辑) ----------------
RE_TITLE = re.compile(r"(?m)^Title-题名:\s*(.+)")
RE_AUTHOR = re.compile(r"(?m)^Author-作者:\s*(.+)")
RE_ORGAN = re.compile(r"(?m)^Organ-机构:\s*(.+)")
RE_PUB = re.compile(r"(?m)^PubTime-出版时间:\s*(.+)")
RE_RECORD = re.compile(r"(?m)^Title-题名:.*?(?=^Title-题名:|\Z)", re.DOTALL)

SEP_SPLIT = re.compile(r"[;；、，,]+")
STRIP_BULLET = re.compile(r"^[\-—·•]\s*")

def _split_items(s: str) -> List[str]:
    parts = SEP_SPLIT.split(s)
    items = []
    for p in parts:
        t = STRIP_BULLET.sub('', p.strip())
        if t:
            items.append(t)
    return items

def parse_metadata_file(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"元数据文件不存在: {path}")
    txt = path.read_text(encoding='utf-8', errors='ignore')
    recs = []
    for block in RE_RECORD.findall(txt):
        m_title = RE_TITLE.search(block)
        if not m_title:
            continue
        title = m_title.group(1).strip()
        authors = _split_items(RE_AUTHOR.search(block).group(1)) if RE_AUTHOR.search(block) else []
        orgs = _split_items(RE_ORGAN.search(block).group(1)) if RE_ORGAN.search(block) else []
        pub = RE_PUB.search(block).group(1).strip() if RE_PUB.search(block) else ''
        if title:
            recs.append({
                'title': title,
                'authors': authors,
                'orgs': orgs,
                'pub_time': pub,
            })
    return recs

NORMALIZE_RE = re.compile(r"[\s_\-—:：,，；;·•.!！?？'\"()（）\[\]【】]")

def normalize_name(s: str) -> str:
    return NORMALIZE_RE.sub('', s).lower()

def build_index(records: List[Dict[str, Any]]) -> List[Tuple[str, Dict[str, Any]]]:
    pairs = []
    for r in records:
        t = r.get('title','')
        if t:
            pairs.append((normalize_name(str(t)), r))
    # 长标题优先
    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    return pairs

def match_meta(stem: str, indexed: List[Tuple[str, Dict[str, Any]]]) -> Dict[str, Any] | None:
    ns = normalize_name(stem)
    for nt, meta in indexed:
        if ns.startswith(nt):
            return meta
    return None

# ---------------- Injection helpers ----------------

def dedup_entities(existing: List[Dict[str, Any]], new_items: List[Dict[str, Any]]):
    seen = {( (e.get('text','').strip().lower(), e.get('type','')) ): True for e in existing}
    appended = []
    for e in new_items:
        key = (e['text'].strip().lower(), e['type'])
        if key in seen:
            continue
        seen[key] = True
        appended.append(e)
    return appended

def dedup_relations(existing: List[Dict[str, Any]], new_items: List[Dict[str, Any]]):
    def _norm(s: str): return s.strip().lower()
    seen = {( _norm(r.get('head','')), _norm(r.get('tail','')), r.get('type','') ): True for r in existing}
    appended = []
    for r in new_items:
        key = (_norm(r['head']), _norm(r['tail']), r['type'])
        if key in seen:
            continue
        seen[key] = True
        appended.append(r)
    return appended

# ---------------- Process one JSON ----------------

def inject_one(json_path: Path, meta: Dict[str, Any], add_source: bool) -> Tuple[int,int]:
    try:
        raw = json.loads(json_path.read_text(encoding='utf-8'))
    except Exception:
        return 0,0
    if isinstance(raw, dict):
        item = raw
    elif isinstance(raw, list) and raw and isinstance(raw[0], dict):
        item = raw[0]
    else:
        return 0,0
    ents = item.get('entities') or []
    rels = item.get('relations') or []
    if not isinstance(ents,list) or not isinstance(rels,list):
        return 0,0

    title = str(meta.get('title',''))
    authors: List[str] = meta.get('authors', [])  # type: ignore
    orgs: List[str] = meta.get('orgs', [])  # type: ignore
    pub = str(meta.get('pub_time',''))

    new_entities: List[Dict[str,Any]] = []
    def _ent(t, txt):
        d = { 'type': t, 'text': txt, 'evaluation': '正确' }
        if add_source: d['source'] = 'metadata_rule'
        return d
    if title:
        new_entities.append(_ent('论文', title))
    for a in authors:
        if a: new_entities.append(_ent('作者', a))
    for o in orgs:
        if o: new_entities.append(_ent('发表单位', o))
    if pub:
        new_entities.append(_ent('发表时间', pub))

    new_relations: List[Dict[str,Any]] = []
    def _rel(t, h, ta):
        d = { 'type': t, 'head': h, 'tail': ta, 'evaluation': '正确' }
        if add_source: d['source'] = 'metadata_rule'
        return d
    for a in authors:
        if a and title:
            new_relations.append(_rel('撰写', a, title))
    if authors and orgs and authors[0] and orgs[0]:
        new_relations.append(_rel('隶属', authors[0], orgs[0]))
    if title and pub:
        new_relations.append(_rel('发表于', title, pub))

    appended_entities = dedup_entities(ents, new_entities)
    appended_relations = dedup_relations(rels, new_relations)
    if appended_entities or appended_relations:
        ents.extend(appended_entities)
        rels.extend(appended_relations)
        item['entities'] = ents
        item['relations'] = rels
        json_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding='utf-8')
    return len(appended_entities), len(appended_relations)

# ---------------- Main ----------------

def main():
    ap = argparse.ArgumentParser(description='向打分结果 JSON 注入摘要元数据 (evaluation=正确)')
    ap.add_argument('--metadata-file', required=True, help='聚合元数据 txt 路径')
    ap.add_argument('--models', default='deepseek,gemini,kimi', help='模型列表, 逗号分隔')
    ap.add_argument('--dry-run', action='store_true', help='仅统计不写入')
    ap.add_argument('--no-source', action='store_true', help='不写入 source=metadata_rule')
    ap.add_argument('--write-csv', action='store_true', help='输出汇总 CSV')
    ap.add_argument('--limit', type=int, default=0, help='每模型最大处理文件数 (0=全部)')
    ap.add_argument('--root', type=Path, help='实验根目录 (包含 指标统计计算)')
    ap.add_argument('--score-base', type=Path, help='直接指定打分结果根目录 (包含各模型子目录)')
    ap.add_argument('--out-stat-dir', type=Path, help='统计输出目录 (默认 root/指标统计计算/指标三：模型打分/统计结果)')
    ap.add_argument('--debug', action='store_true', help='输出调试信息')
    args = ap.parse_args()

    script_dir = Path(__file__).resolve().parent
    root_dir = args.root if args.root else auto_detect_root(script_dir)
    score_base = args.score_base if args.score_base else (root_dir / '指标统计计算' / '指标三：模型打分' / '打分结果')
    out_stat_dir = args.out_stat_dir if args.out_stat_dir else (root_dir / '指标统计计算' / '指标三：模型打分' / '统计结果')
    out_stat_dir.mkdir(parents=True, exist_ok=True)

    if args.debug:
        print(f'[调试] root_dir     = {root_dir}')
        print(f'[调试] score_base   = {score_base}')
        print(f'[调试] out_stat_dir = {out_stat_dir}')

    meta_file = Path(args.metadata_file)
    records = parse_metadata_file(meta_file)
    indexed = build_index(records)
    models = [m.strip() for m in args.models.split(',') if m.strip()]

    summary: List[List[Any]] = []

    for model in models:
        mdir = score_base / model
        if not mdir.exists():
            print(f"[WARN] 模型目录不存在: {mdir}")
            continue
        files = sorted(mdir.glob('*.json'))
        if args.limit > 0:
            files = files[:args.limit]
        added_e_total = 0
        added_r_total = 0
        matched_files = 0
        for f in files:
            meta = match_meta(f.stem, indexed)
            if not meta:
                continue
            matched_files += 1
            if args.dry_run:
                # 预估：执行一次 inject_one 但不写 (复制原逻辑, 未改动填充方式)
                try:
                    raw = json.loads(f.read_text(encoding='utf-8'))
                except Exception:
                    continue
                if isinstance(raw, dict):
                    ents = raw.get('entities') or []
                    rels = raw.get('relations') or []
                elif isinstance(raw, list) and raw and isinstance(raw[0], dict):
                    ents = raw[0].get('entities') or []
                    rels = raw[0].get('relations') or []
                else:
                    continue
                existing_e_keys = { (e.get('text','').strip().lower(), e.get('type','')) for e in ents }
                existing_r_keys = { (str(r.get('head','')).strip().lower(), str(r.get('tail','')).strip().lower(), r.get('type','')) for r in rels }
                title = meta.get('title','')
                authors = meta.get('authors', [])
                orgs = meta.get('orgs', [])
                pub = meta.get('pub_time','')
                cand_e = []
                if title: cand_e.append((title.strip().lower(),'论文'))
                for a in authors: cand_e.append((str(a).strip().lower(),'作者'))
                for o in orgs: cand_e.append((str(o).strip().lower(),'发表单位'))
                if pub: cand_e.append((str(pub).strip().lower(),'发表时间'))
                new_e_count = sum(1 for k in cand_e if k not in existing_e_keys)
                cand_r = []
                for a in authors:
                    if a and title: cand_r.append((a.strip().lower(), title.strip().lower(), '撰写'))
                if authors and orgs and authors[0] and orgs[0]:
                    cand_r.append((authors[0].strip().lower(), orgs[0].strip().lower(),'隶属'))
                if title and pub:
                    cand_r.append((title.strip().lower(), str(pub).strip().lower(),'发表于'))
                new_r_count = sum(1 for k in cand_r if k not in existing_r_keys)
                added_e_total += new_e_count
                added_r_total += new_r_count
            else:
                e_add, r_add = inject_one(f, meta, add_source=not args.no_source)
                added_e_total += e_add
                added_r_total += r_add
        summary.append([model, len(files), matched_files, added_e_total, added_r_total])
        mode = 'DRY-RUN' if args.dry_run else 'WRITE'
        print(f"[SUMMARY][{model}][{mode}] files={len(files)} matched={matched_files} addE={added_e_total} addR={added_r_total}")
    if args.write_csv and summary:
        out_csv = out_stat_dir / '打分结果_元数据填充汇总.csv'
        with out_csv.open('w', newline='', encoding='utf-8-sig') as fw:
            w = csv.writer(fw)
            w.writerow(['模型','文件总数','匹配到元数据文件数','新增实体数','新增关系数'])
            for r in summary:
                w.writerow(r)
        print('[INFO] 汇总 CSV 写出:', out_csv)

if __name__ == '__main__':
    main()
