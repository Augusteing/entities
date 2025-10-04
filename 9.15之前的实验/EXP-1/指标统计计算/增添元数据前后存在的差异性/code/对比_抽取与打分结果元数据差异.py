# -*- coding: utf-8 -*-
"""对比 抽取/数据结果 与 指标三：模型打分/打分结果 中同一模型同名 JSON 的实体差异。

用例: 查找为什么 kimi 在抽取结果注入后总实体 1252 而打分结果注入后为 1253。

比较内容:
  1. 全部实体 (按 (type, text) 归一化签名)
  2. 元数据实体子集: {论文, 作者, 发表单位, 发表时间}
输出:
  差异明细 CSV: 结果/抽取_vs_打分_实体差异_<model>.csv
    列: 文件, 抽取实体数, 打分实体数, 差值(打分-抽取), 抽取元数据数, 打分元数据数, 元数据差值,
        仅在打分存在的实体(前若干;完整写文件), 仅在抽取存在的实体(前若干)
  仅在打分存在完整列表: 结果/抽取_vs_打分_仅打分存在实体_<model>.csv
  仅在抽取存在完整列表: 结果/抽取_vs_打分_仅抽取存在实体_<model>.csv
  汇总: 结果/抽取_vs_打分_实体差异汇总_<model>.txt

签名归一化: type 原样; text -> 去首尾空白, 全角空白, lower()。

运行:
  python 对比_抽取与打分结果元数据差异.py --model kimi
"""
from __future__ import annotations
import argparse, json, csv
from pathlib import Path
from typing import Dict, List, Tuple, Set

ROOT = Path(r"e:\知识图谱构建\9.15之前的实验\EXP-1")
EXTRACT_BASE = ROOT / '抽取' / '数据结果'
SCORE_BASE = ROOT / '指标统计计算' / '指标三：模型打分' / '打分结果'
OUT_DIR = ROOT / '指标统计计算' / '增添元数据前后存在的差异性' / '结果'
OUT_DIR.mkdir(parents=True, exist_ok=True)

META_TYPES = {"论文","作者","发表单位","发表时间"}

MODEL_MAP_EXTRACT = lambda m: EXTRACT_BASE / f'提取结果_by_{m}' / 'in_scope'
MODEL_MAP_SCORE = lambda m: SCORE_BASE / m

def load_entities(path: Path):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return []
    if isinstance(data, dict):
        ents = data.get('entities') or []
    elif isinstance(data, list) and data and isinstance(data[0], dict):
        ents = data[0].get('entities') or []
    else:
        return []
    if not isinstance(ents, list):
        return []
    return ents

import re
SPACE_RE = re.compile(r"\s+")

def norm_text(s: str) -> str:
    return SPACE_RE.sub('', s.strip()).lower()

def build_sig_sets(ents):
    all_set: Set[Tuple[str,str]] = set()
    meta_set: Set[Tuple[str,str]] = set()
    for e in ents:
        t = e.get('type')
        txt = e.get('text') or e.get('name') or ''
        if not t or not txt:
            continue
        sig = (t, norm_text(str(txt)))
        all_set.add(sig)
        if t in META_TYPES:
            meta_set.add(sig)
    return all_set, meta_set

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default='kimi')
    ap.add_argument('--limit-diff-preview', type=int, default=10, help='明细 CSV 里显示的差异实体预览条数')
    args = ap.parse_args()

    model = args.model
    ext_dir = MODEL_MAP_EXTRACT(model)
    sc_dir = MODEL_MAP_SCORE(model)
    if not ext_dir.exists() or not sc_dir.exists():
        print('[ERROR] 目录不存在:', ext_dir, sc_dir)
        return

    ext_files = {p.name: p for p in ext_dir.glob('*.json')}
    sc_files = {p.name: p for p in sc_dir.glob('*.json')}
    common = sorted(set(ext_files.keys()) & set(sc_files.keys()))
    if not common:
        print('[WARN] 没有公共文件名。')
        return

    diff_rows: List[List[str]] = []
    only_score_full: List[List[str]] = []
    only_ext_full: List[List[str]] = []

    total_ext = total_sc = 0
    total_ext_meta = total_sc_meta = 0
    total_only_score = total_only_ext = 0

    preview_n = args.limit_diff_preview

    for fname in common:
        ents_ext = load_entities(ext_files[fname])
        ents_sc = load_entities(sc_files[fname])
        set_ext_all, set_ext_meta = build_sig_sets(ents_ext)
        set_sc_all, set_sc_meta = build_sig_sets(ents_sc)

        total_ext += len(set_ext_all)
        total_sc += len(set_sc_all)
        total_ext_meta += len(set_ext_meta)
        total_sc_meta += len(set_sc_meta)

        only_score = sorted(set_sc_all - set_ext_all)
        only_ext = sorted(set_ext_all - set_sc_all)

        total_only_score += len(only_score)
        total_only_ext += len(only_ext)

        preview_score = ';'.join([f"{t}:{txt}" for t,txt in only_score[:preview_n]])
        preview_ext = ';'.join([f"{t}:{txt}" for t,txt in only_ext[:preview_n]])

        diff_rows.append([
            fname,
            len(set_ext_all), len(set_sc_all), len(set_sc_all)-len(set_ext_all),
            len(set_ext_meta), len(set_sc_meta), len(set_sc_meta)-len(set_ext_meta),
            preview_score, preview_ext
        ])

        for t,txt in only_score:
            only_score_full.append([fname, t, txt])
        for t,txt in only_ext:
            only_ext_full.append([fname, t, txt])

    # 写明细 CSV
    diff_csv = OUT_DIR / f'抽取_vs_打分_实体差异_{model}.csv'
    with diff_csv.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['文件','抽取实体数','打分实体数','实体差值','抽取元数据实体数','打分元数据实体数','元数据差值','仅打分存在预览','仅抽取存在预览'])
        w.writerows(diff_rows)
    score_only_csv = OUT_DIR / f'抽取_vs_打分_仅打分存在实体_{model}.csv'
    with score_only_csv.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['文件','类型','文本(归一后)'])
        w.writerows(only_score_full)
    ext_only_csv = OUT_DIR / f'抽取_vs_打分_仅抽取存在实体_{model}.csv'
    with ext_only_csv.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['文件','类型','文本(归一后)'])
        w.writerows(only_ext_full)

    summary_txt = OUT_DIR / f'抽取_vs_打分_实体差异汇总_{model}.txt'
    with summary_txt.open('w', encoding='utf-8') as f:
        f.write(f"模型: {model}\n")
        f.write(f"公共文件数: {len(common)}\n")
        f.write(f"抽取总实体(去重签名后): {total_ext}\n")
        f.write(f"打分总实体(去重签名后): {total_sc}\n")
        f.write(f"差值(打分-抽取): {total_sc - total_ext}\n")
        f.write(f"抽取元数据实体: {total_ext_meta} 打分元数据实体: {total_sc_meta} 元数据差值: {total_sc_meta - total_ext_meta}\n")
        f.write(f"仅打分存在实体总数: {total_only_score}\n")
        f.write(f"仅抽取存在实体总数: {total_only_ext}\n")
        f.write(f"明细表: {diff_csv.name}\n")
        f.write(f"仅打分存在: {score_only_csv.name}\n")
        f.write(f"仅抽取存在: {ext_only_csv.name}\n")
    print('[INFO] 对比完成。差异汇总写出 ->', summary_txt)
    print('[HINT] 请先查看 summary 与 仅打分存在 CSV，锁定那 +1 的具体实体。')

if __name__ == '__main__':
    main()
