#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


RANK_COLORS = {
    1: '#925EB0',  # 紫
    2: '#7E99F4',  # 蓝
    3: '#7AB656',  # 绿
}


def read_top3_csv(csv_path: Path) -> Dict[str, List[Tuple[str, int]]]:
    by_model: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
    with csv_path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                m = r['model']
                t = r['type']
                c = int(r['count'])
                rank = int(r['rank'])
            except Exception:
                continue
            by_model[m].append((rank, t, c))
    # 按 rank 排序并只保留 type,count
    result: Dict[str, List[Tuple[str, int]]] = {}
    for m, items in by_model.items():
        items.sort(key=lambda x: x[0])
        result[m] = [(t, c) for _, t, c in items[:3]]
    return result


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    model_eval_dir = script_dir.parent  # 评估/指标二：模型评估
    output_dir = model_eval_dir / '结果'
    output_dir.mkdir(parents=True, exist_ok=True)

    data_root = model_eval_dir.parent.parent / '数据结果'
    csv_path = data_root / 'top3_relation_types_by_model.csv'
    if not csv_path.exists():
        raise SystemExit(f'未找到统计文件: {csv_path}')

    top3 = read_top3_csv(csv_path)

    try:
        import matplotlib.pyplot as plt
        import numpy as np
        import matplotlib as mpl
    except Exception as e:
        print('缺少 matplotlib/numpy，跳过出图：', e)
        return

    # 字体设置：Times New Roman
    try:
        mpl.rcParams['font.family'] = 'Times New Roman'
        mpl.rcParams['axes.unicode_minus'] = False
    except Exception:
        pass

    models = ['gemini', 'deepseek', 'kimi']
    labels_rank = ['Top1', 'Top2', 'Top3']

    # 组装高度数组 [rank][model]
    heights = []
    type_labels_per_model = {m: ['', '', ''] for m in models}
    for rank in [1, 2, 3]:
        row = []
        for m in models:
            items = top3.get(m, [])
            if len(items) >= rank:
                t, c = items[rank - 1]
                row.append(c)
                type_labels_per_model[m][rank - 1] = t
            else:
                row.append(0)
        heights.append(row)

    x = np.arange(len(models))
    width = 0.22
    plt.figure(figsize=(10, 6))
    for idx, rank in enumerate([1, 2, 3]):
        plt.bar(x + (idx - 1) * width, heights[idx], width=width, color=RANK_COLORS[rank], edgecolor='#333333', label=labels_rank[idx])

    plt.xticks(x, [m.capitalize() for m in models])
    plt.ylabel('Count')
    plt.title('Top-3 Relation Types per Model (Evaluation Papers)')
    plt.legend()

    # 中文关系类型 -> 英文映射（未命中则原样显示）
    TYPE_EN_MAP: Dict[str, str] = {
        '用于': 'used for',
        '基于': 'based on',
        '包括': 'include',
        '包含': 'contain',
        '属于': 'belong to',
        '得出': 'derive',
        '评价指标是': 'metric is',
        '提出': 'propose',
        '定义为': 'define as',
        '描述': 'describe',
        '验证': 'verify',
        '使用': 'use',
        '修正': 'revise',
        '适用于': 'applicable to',
        '用于…求解': 'solve for',
        '计算': 'compute',
        '构成': 'constitute',
        '连接': 'connect',
    }

    # 标注 type + count（使用英文标签）
    for idx, (rank, h) in enumerate(zip([1, 2, 3], heights)):
        for j, (xi, val) in enumerate(zip(x + (idx - 1) * width, h)):
            t_cn = type_labels_per_model[models[j]][rank - 1]
            t_en = TYPE_EN_MAP.get(t_cn, t_cn)
            label = f'{t_en} ({val})' if val else ''
            if not label:
                continue
            plt.annotate(label, xy=(xi, val), xytext=(0, 8), textcoords='offset points', ha='center', va='bottom', fontsize=9)

    out_img = output_dir / 'chart_top3_relation_types_by_model.png'
    plt.tight_layout()
    plt.savefig(out_img, dpi=200)
    plt.close()
    print(f'已输出: {out_img}')


if __name__ == '__main__':
    main()
