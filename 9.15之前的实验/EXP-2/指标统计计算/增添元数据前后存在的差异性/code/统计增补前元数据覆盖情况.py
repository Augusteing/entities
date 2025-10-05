# -*- coding: utf-8 -*-
"""统计增补前各模型已包含的元数据实体/关系覆盖情况

数据来源：E:/知识图谱构建/9.15之前的实验/EXP-1/抽取/数据结果/增补前/提取结果_by_<model>/in_scope/*.json
  需要存在一个 "增补前" 目录快照；脚本不修改任何文件。

统计内容：
  per-model:
    - 覆盖论文数(有匹配JSON)
    - 题名实体是否存在 (type=论文)
    - 作者实体个数 (type=作者)
    - 发表单位实体个数 (type=发表单位)
    - 发表时间实体个数 (type=发表时间)
    - 撰写关系个数 (type=撰写)
    - 隶属关系是否存在 (作者→单位)
    - 发表于关系是否存在
  输出：
    1) 每模型详情 CSV: <model>_增补前元数据详情.csv
    2) 汇总 CSV: 模型_增补前元数据统计汇总.csv

匹配论文集合：使用 增补前/in_scope 下的 JSON 文件名 stem（与已补充版本保持一致）。

使用示例：
  python 统计增补前元数据覆盖情况.py --models deepseek,gemini,kimi
"""
from __future__ import annotations
import json
import csv
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(r"e:\知识图谱构建\9.15之前的实验\EXP-1")
PRE_BASE = ROOT / '抽取' / '数据结果' / '增补前'
OUT_BASE = ROOT / '指标统计计算' / '增添元数据前后存在的差异性' / '结果'
OUT_BASE.mkdir(parents=True, exist_ok=True)

META_ENTITY_TYPES = {
    '论文': 'title_present',
    '作者': 'author_count',
    '发表单位': 'org_count',
    '发表时间': 'pub_time_count',
}

REL_TYPES = {
    '撰写': 'write_count',
    '隶属': 'affiliation_present',
    '发表于': 'publish_present',
}

def load_json(path: Path):
    try:
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def iter_model_files(model: str) -> List[Path]:
    mdir = PRE_BASE / f'提取结果_by_{model}' / 'in_scope'
    if not mdir.exists():
        return []
    return sorted(mdir.glob('*.json'))

def analyze_json(path: Path) -> Dict[str, object]:
    data = load_json(path)
    if not isinstance(data, dict):
        return {}
    ents = data.get('entities', []) or []
    rels = data.get('relations', []) or []
    res = {
        'file': path.name,
        'title_present': 0,
        'author_count': 0,
        'org_count': 0,
        'pub_time_count': 0,
        'write_count': 0,
        'affiliation_present': 0,
        'publish_present': 0,
    }
    # 实体统计
    for e in ents:
        et = e.get('type')
        if et == '论文':
            res['title_present'] = 1
        elif et == '作者':
            res['author_count'] += 1
        elif et == '发表单位':
            res['org_count'] += 1
        elif et == '发表时间':
            res['pub_time_count'] += 1
    # 关系统计
    for r in rels:
        rt = r.get('type') or r.get('relation')
        if rt == '撰写':
            res['write_count'] += 1
        elif rt == '隶属':
            res['affiliation_present'] = 1
        elif rt == '发表于':
            res['publish_present'] = 1
    return res

def summarize(details: List[Dict[str, object]]) -> Dict[str, object]:
    if not details:
        return {k:0 for k in ['files','title_files','total_authors','total_orgs','total_pub_times','total_write_rels','affiliation_files','publish_files']}
    s = {
        'files': len(details),
        'title_files': sum(d['title_present'] for d in details),
        'total_authors': sum(d['author_count'] for d in details),
        'total_orgs': sum(d['org_count'] for d in details),
        'total_pub_times': sum(d['pub_time_count'] for d in details),
        'total_write_rels': sum(d['write_count'] for d in details),
        'affiliation_files': sum(d['affiliation_present'] for d in details),
        'publish_files': sum(d['publish_present'] for d in details),
    }
    return s

def main():
    parser = argparse.ArgumentParser(description='统计增补前各模型元数据覆盖率')
    parser.add_argument('--models', default='deepseek,gemini,kimi', help='模型列表, 逗号分隔')
    args = parser.parse_args()
    models = [m.strip() for m in args.models.split(',') if m.strip()]
    summary_rows = []

    for model in models:
        files = iter_model_files(model)
        if not files:
            print(f'[WARN] 模型 {model} 未找到增补前目录: {PRE_BASE / f"提取结果_by_{model}" / "in_scope"}')
            continue
        details = [analyze_json(p) for p in files]
        # 写详情
        detail_path = OUT_BASE / f'{model}_增补前元数据详情.csv'
        with detail_path.open('w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['文件','是否有题名实体','作者实体数','发表单位实体数','发表时间实体数','撰写关系数','是否有隶属关系','是否有发表于关系'])
            for d in details:
                w.writerow([
                    d['file'], d['title_present'], d['author_count'], d['org_count'], d['pub_time_count'], d['write_count'], d['affiliation_present'], d['publish_present']
                ])
        print(f'[INFO] 详情写出: {detail_path}')
        s = summarize(details)
        summary_rows.append([
            model,
            s['files'], s['title_files'], s['total_authors'], s['total_orgs'], s['total_pub_times'],
            s['total_write_rels'], s['affiliation_files'], s['publish_files']
        ])

    # 汇总
    sum_path = OUT_BASE / '模型_增补前元数据统计汇总.csv'
    with sum_path.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['模型','文件数','含题名实体文件数','作者实体总数','发表单位实体总数','发表时间实体总数','撰写关系总数','含隶属关系文件数','含发表于关系文件数'])
        for row in summary_rows:
            w.writerow(row)
    print('[INFO] 汇总写出:', sum_path)

if __name__ == '__main__':
    main()
