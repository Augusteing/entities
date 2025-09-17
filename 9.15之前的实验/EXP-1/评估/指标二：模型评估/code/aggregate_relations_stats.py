#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
对“需要评估的论文”范围内的三模型（deepseek, gemini, kimi）关系抽取结果进行聚合：
- 输入：评估/指标二：模型评估/结果/<model>/*.json
- 文章范围：评估/需要评估的论文/*.md
- 统计：
  1) 每模型总关系数（不去重）：数据结果/total_relations_by_model.csv（model,total_relations）
  2) 每模型Top3关系类型（按出现次数）：数据结果/top3_relation_types_by_model.csv（model,rank,type,count）
  3) 每模型去重后的关系类型数：数据结果/unique_relation_types_by_model.csv（model,unique_relation_types）

运行：
  python .\评估\指标二：模型评估\code\aggregate_relations_stats.py
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


def iter_relations(json_path: Path) -> List[dict]:
    try:
        if not json_path.exists():
            return []
        with json_path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        rels = data.get('relations', [])
        return rels if isinstance(rels, list) else []
    except Exception:
        return []


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    model_eval_dir = script_dir.parent  # 评估/指标二：模型评估
    eval_results_dir = model_eval_dir / '结果'
    workspace_root = model_eval_dir.parent.parent  # EXP-1 根目录
    papers_dir = workspace_root / '评估' / '需要评估的论文'
    output_dir = workspace_root / '数据结果'
    output_dir.mkdir(parents=True, exist_ok=True)

    model_dirs: Dict[str, Path] = {
        'deepseek': eval_results_dir / 'deepseek',
        'gemini': eval_results_dir / 'gemini',
        'kimi': eval_results_dir / 'kimi',
    }

    # 文章清单
    paper_basenames: List[str] = [p.stem for p in sorted(papers_dir.glob('*.md'))]

    # 统计容器
    total_by_model: Dict[str, int] = defaultdict(int)
    type_counter_by_model: Dict[str, Counter] = {m: Counter() for m in model_dirs}

    for model, mdir in model_dirs.items():
        for bn in paper_basenames:
            rels = iter_relations(mdir / f'{bn}.json')
            total_by_model[model] += len(rels)
            # 统计关系类型次数（按 'type' 字段）
            for r in rels:
                rtype = r.get('type')
                if isinstance(rtype, str) and rtype:
                    type_counter_by_model[model][rtype] += 1

    # 1) 总关系数
    total_csv = output_dir / 'total_relations_by_model.csv'
    with total_csv.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['model', 'total_relations'])
        writer.writeheader()
        for model in model_dirs.keys():
            writer.writerow({'model': model, 'total_relations': total_by_model.get(model, 0)})

    # 2) Top3 关系类型
    top3_csv = output_dir / 'top3_relation_types_by_model.csv'
    with top3_csv.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['model', 'rank', 'type', 'count'])
        writer.writeheader()
        for model in model_dirs.keys():
            for rank, (rtype, cnt) in enumerate(type_counter_by_model[model].most_common(3), start=1):
                writer.writerow({'model': model, 'rank': rank, 'type': rtype, 'count': cnt})

    # 3) 去重的关系类型数量
    unique_csv = output_dir / 'unique_relation_types_by_model.csv'
    with unique_csv.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['model', 'unique_relation_types'])
        writer.writeheader()
        for model in model_dirs.keys():
            writer.writerow({'model': model, 'unique_relation_types': len(type_counter_by_model[model])})

    print(f'已生成: {total_csv}')
    print(f'已生成: {top3_csv}')
    print(f'已生成: {unique_csv}')


if __name__ == '__main__':
    main()
