# -*- coding: utf-8 -*-
"""
Rank typical dependency paths using lightweight statistics.
- Input: 依存路径提取结果/*.json (each file produced by dependency_path.py)
- Output: CSV with ranked paths and a JSONL with samples

Score(path) = 0.5 * Assoc + 0.3 * log(1+support) + 0.2 * log(1+doc_freq)
Assoc = mean over edges [max(nPMI,0) * log(1 + bigram_count)]

Path representation by default uses token forms only (no deprel) and filters
path length into a reasonable range. A small synonym map normalizes variants
(e.g., 方法/方案/手段 -> 方法; 解决/处理 -> 解决; 问题/难题/故障 -> 问题).

Usage:
  python rank_typical_paths.py --topk 100 --min-count 3 --min-doc 2
"""

from __future__ import annotations
import os
import json
import math
import argparse
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Iterable, Any

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
RESULT_DIR = os.path.join(BASE_DIR, '依存路径提取结果')
OUT_CSV = os.path.join(RESULT_DIR, 'top_paths.csv')
OUT_JSONL = os.path.join(RESULT_DIR, 'top_path_samples.jsonl')

# --- Normalization helpers ---
SYNONYM_MAP = {
    # 常见近义规范化（按项目需要可扩展）
    '方案': '方法', '手段': '方法', '途径': '方法', '策略': '方法', '流程': '方法',
    '处理': '解决', '应对': '解决', '化解': '解决', '攻克': '解决', '解决方案': '解决',
    '难题': '问题', '故障': '问题', '矛盾': '问题', '挑战': '问题', '痛点': '问题',
}

GENERIC_WORDS = {
    # 语义泛化词（路径若被其主导可降权）
    '是','有','进行','方面','各种','对于','一种','通过','针对','采用','提出','研究','分析','实现','建立','开展','设计','提供','进行','应用'
}


def normalize_token(form: str) -> str:
    if not form:
        return ''
    s = str(form).strip()
    # 中文一般无需大小写；移除空白
    s = s.replace('\u200b', '').replace('\ufeff', '')
    # 统一同义词
    return SYNONYM_MAP.get(s, s)


def path_to_forms(path_entry: Any) -> List[str]:
    """Convert record['path'] into list of forms.
    path could be list of [form, deprel] or list of dicts {form,deprel}.
    """
    forms: List[str] = []
    for node in (path_entry or []):
        if isinstance(node, (list, tuple)):
            form = node[0] if node else ''
        elif isinstance(node, dict):
            form = node.get('form', '')
        else:
            form = str(node)
        nf = normalize_token(form)
        if nf:
            forms.append(nf)
    return forms


def iter_path_files(result_dir: str) -> Iterable[str]:
    for fn in os.listdir(result_dir):
        if fn.endswith('依存路径.json') and not fn.endswith('_paths.json'):
            yield os.path.join(result_dir, fn)


def load_pairs_from_file(fp: str) -> Tuple[str, List[Dict[str, Any]]]:
    with open(fp, 'r', encoding='utf-8') as f:
        data = json.load(f)
    title = ''
    pairs: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        title = data.get('title') or ''
        items = data.get('pairs') or data.get('results') or data.get('items') or []
        if isinstance(items, list):
            pairs = items
    elif isinstance(data, list):
        pairs = data
    if not title:
        # Fallback to filename
        base = os.path.basename(fp)
        title = base.replace('依存路径.json', '')
    return title, pairs


def score_paths(paths: List[Tuple[str, ...]],
                path_docs: Dict[Tuple[str, ...], set],
                min_count: int,
                min_doc: int,
                min_len: int,
                max_len: int) -> List[Dict[str, Any]]:
    path_counts = Counter(paths)

    # Build unigram/bigram counts over edges
    unigram: Counter[str] = Counter()
    bigram: Counter[Tuple[str, str]] = Counter()
    for p in paths:
        if not (min_len <= len(p) <= max_len):
            continue
        for w in p:
            unigram[w] += 1
        for a, b in zip(p, p[1:]):
            bigram[(a, b)] += 1

    total_uni = sum(unigram.values()) or 1
    total_bi = sum(bigram.values()) or 1

    def npmi(a: str, b: str) -> float:
        c_ab = bigram[(a, b)]
        if c_ab <= 0:
            return -1.0
        p_ab = c_ab / total_bi
        p_a = (unigram[a] / total_uni) if unigram[a] else 1e-12
        p_b = (unigram[b] / total_uni) if unigram[b] else 1e-12
        pmi = math.log((p_ab / (p_a * p_b)) + 1e-12)
        return pmi / (-math.log(p_ab + 1e-12))

    def pair_score(a: str, b: str) -> float:
        c_ab = bigram[(a, b)]
        return max(npmi(a, b), 0.0) * math.log(1.0 + c_ab)

    ranked: List[Dict[str, Any]] = []
    for path, c in path_counts.items():
        if not (min_len <= len(path) <= max_len):
            continue
        if c < min_count:
            continue
        df = len(path_docs.get(path, set()))
        if df < min_doc:
            continue
        edges = list(zip(path, path[1:]))
        if not edges:
            continue
        assoc = sum(pair_score(a, b) for a, b in edges) / max(len(edges), 1)
        s_freq = math.log(1.0 + c)
        s_cover = math.log(1.0 + df)
        score = 0.5 * assoc + 0.3 * s_freq + 0.2 * s_cover
        # length penalty
        if len(path) < 3:
            score *= 0.85
        # generic penalty
        gen_ratio = sum(1 for w in path if w in GENERIC_WORDS) / float(len(path))
        if gen_ratio >= 0.5:
            score *= 0.85
        ranked.append({
            'path': list(path),
            'support': c,
            'doc_freq': df,
            'avg_npmi': assoc,
            'len': len(path),
            'score': score,
        })

    ranked.sort(key=lambda x: x['score'], reverse=True)
    return ranked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--result-dir', default=RESULT_DIR)
    ap.add_argument('--topk', type=int, default=200)
    ap.add_argument('--min-count', type=int, default=3)
    ap.add_argument('--min-doc', type=int, default=2)
    ap.add_argument('--min-len', type=int, default=2)
    ap.add_argument('--max-len', type=int, default=6)
    ap.add_argument('--include-cross', action='store_true', help='Include cross-sentence paths (default on)')
    ap.add_argument('--exclude-cross', action='store_true', help='Exclude cross-sentence paths')
    args = ap.parse_args()

    result_dir = args.result_dir
    files = list(iter_path_files(result_dir))
    if not files:
        print('No path JSON files found in', result_dir)
        return

    # Accumulators
    all_paths: List[Tuple[str, ...]] = []
    path_docs: Dict[Tuple[str, ...], set] = defaultdict(set)
    examples: Dict[Tuple[str, ...], List[Dict[str, Any]]] = defaultdict(list)

    include_cross = not args.exclude_cross

    for fp in files:
        title, pairs = load_pairs_from_file(fp)
        for rec in pairs:
            path_entry = rec.get('path')
            ptype = rec.get('path_type')
            if not path_entry:
                continue
            if not include_cross and ptype == 'cross_sentence':
                continue
            forms = path_to_forms(path_entry)
            if not forms:
                continue
            path_t = tuple(forms)
            all_paths.append(path_t)
            path_docs[path_t].add(title)
            # Save up to 5 examples per path
            ex_list = examples[path_t]
            if len(ex_list) < 5:
                ex_list.append({
                    'title': title,
                    'subject': rec.get('subject'),
                    'relation': rec.get('relation'),
                    'object': rec.get('object'),
                    'sentence_index': rec.get('sentence_index'),
                    'path_type': ptype,
                    'path_str': '->'.join(forms),
                })

    ranked = score_paths(
        all_paths,
        path_docs,
        min_count=args.min_count,
        min_doc=args.min_doc,
        min_len=args.min_len,
        max_len=args.max_len,
    )

    # Write CSV
    import csv
    os.makedirs(result_dir, exist_ok=True)
    with open(OUT_CSV, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['rank', 'score', 'support', 'doc_freq', 'avg_npmi', 'len', 'path'])
        for i, item in enumerate(ranked[: args.topk], start=1):
            w.writerow([
                i,
                f"{item['score']:.6f}",
                item['support'],
                item['doc_freq'],
                f"{item['avg_npmi']:.6f}",
                item['len'],
                '->'.join(item['path']),
            ])

    # Write samples JSONL
    with open(OUT_JSONL, 'w', encoding='utf-8') as f:
        for item in ranked[: args.topk]:
            path_t = tuple(item['path'])
            samp = examples.get(path_t, [])
            f.write(json.dumps({
                'path': item['path'],
                'score': item['score'],
                'support': item['support'],
                'doc_freq': item['doc_freq'],
                'avg_npmi': item['avg_npmi'],
                'len': item['len'],
                'samples': samp,
            }, ensure_ascii=False) + '\n')

    print(f"Paths scanned: {len(all_paths)} | Unique: {len(set(all_paths))}")
    print(f"Ranked: {len(ranked)} | Output: {OUT_CSV}, {OUT_JSONL}")


if __name__ == '__main__':
    main()
