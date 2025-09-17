#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
统计“需要评估的论文”中每篇文章在不同模型（deepseek, gemini, kimi）的关系统计：
- 数据来源：评估/指标二：模型评估/结果/<model>/*.json
- 文章清单：评估/需要评估的论文/*.md（仅统计该清单中的文章）
- 统计口径：每文件 JSON 的 relations 列表长度（不去重，不区分正确/错误标签）
- 输出：
  1) 数据结果/relations_count_by_model_and_paper.csv （长表：paper, model, relation_count）
  2) 数据结果/relations_count_by_model_and_paper_wide.csv （宽表：paper, deepseek, gemini, kimi）

运行：
  python .\评估\指标二：模型评估\code\count_relations_by_model_and_paper.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List


def load_relation_count(json_path: Path) -> int:
    """读取单个结果 JSON 并返回 relations 数量；文件不存在或结构异常返回 0。

    期望结构示例：
    {
      "entities": [...],
      "relations": [ {...}, ... ]
    }
    """
    try:
        if not json_path.exists():
            return 0
        with json_path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        rels = data.get('relations', [])
        if isinstance(rels, list):
            return len(rels)
        return 0
    except Exception:
        # 解析失败按 0 计
        return 0


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    model_eval_dir = script_dir.parent  # 评估/指标二：模型评估
    eval_results_dir = model_eval_dir / '结果'
    workspace_root = model_eval_dir.parent.parent  # EXP-1 根目录
    papers_dir = workspace_root / '评估' / '需要评估的论文'
    output_dir = workspace_root / '数据结果'
    output_dir.mkdir(parents=True, exist_ok=True)

    # 确认模型结果目录
    model_dirs: Dict[str, Path] = {
        'deepseek': eval_results_dir / 'deepseek',
        'gemini': eval_results_dir / 'gemini',
        'kimi': eval_results_dir / 'kimi',
    }

    # 从“需要评估的论文”获取文章清单（以 .md 文件名为准，不含扩展名）
    if not papers_dir.exists():
        raise SystemExit(f'未找到论文目录: {papers_dir}')

    paper_basenames: List[str] = []
    for p in sorted(papers_dir.glob('*.md')):
        paper_basenames.append(p.stem)

    if not paper_basenames:
        raise SystemExit('“需要评估的论文”目录下未发现 .md 文件，无法统计。')

    # 统计
    long_rows: List[Dict[str, str | int]] = []
    # 准备宽表数据结构：paper -> {model -> count}
    wide_map: Dict[str, Dict[str, int]] = {bn: {m: 0 for m in model_dirs} for bn in paper_basenames}

    for model, mdir in model_dirs.items():
        if not mdir.exists():
            # 模型目录不存在则所有该模型计数为 0
            for bn in paper_basenames:
                long_rows.append({'paper': bn, 'model': model, 'relation_count': 0})
            continue
        for bn in paper_basenames:
            json_path = mdir / f'{bn}.json'
            count = load_relation_count(json_path)
            long_rows.append({'paper': bn, 'model': model, 'relation_count': count})
            wide_map[bn][model] = count

    # 写出长表 CSV
    long_csv = output_dir / 'relations_count_by_model_and_paper.csv'
    with long_csv.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['paper', 'model', 'relation_count'])
        writer.writeheader()
        writer.writerows(long_rows)

    # 写出宽表 CSV（paper, deepseek, gemini, kimi）
    wide_csv = output_dir / 'relations_count_by_model_and_paper_wide.csv'
    with wide_csv.open('w', newline='', encoding='utf-8') as f:
        fieldnames = ['paper'] + list(model_dirs.keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for bn in paper_basenames:
            row = {'paper': bn}
            row.update(wide_map[bn])
            writer.writerow(row)

    # 控制台摘要
    total_rows = len(long_rows)
    print(f'已生成: {long_csv}')
    print(f'已生成: {wide_csv}')
    print(f'统计完成：共 {total_rows} 条（文章×模型）记录。')


if __name__ == '__main__':
    main()
