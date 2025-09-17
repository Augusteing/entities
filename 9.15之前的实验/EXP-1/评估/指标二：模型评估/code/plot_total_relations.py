#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
from pathlib import Path


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    model_eval_dir = script_dir.parent  # 评估/指标二：模型评估
    output_dir = model_eval_dir / '结果'
    output_dir.mkdir(parents=True, exist_ok=True)

    data_root = model_eval_dir.parent.parent / '数据结果'
    csv_path = data_root / 'total_relations_by_model.csv'
    if not csv_path.exists():
        raise SystemExit(f'未找到统计文件: {csv_path}')

    # 读取数据
    rows = []
    with csv_path.open('r', encoding='utf-8') as f:
        for i, r in enumerate(csv.DictReader(f)):
            try:
                rows.append((r['model'], int(r['total_relations'])))
            except Exception:
                pass

    # 按固定顺序排版
    order = ['gemini', 'deepseek', 'kimi']
    data = [(m, next((v for mm, v in rows if mm == m), 0)) for m in order]

    # 绘图
    try:
        import matplotlib.pyplot as plt
        import matplotlib as mpl
    except Exception as e:
        print('缺少 matplotlib，跳过出图：', e)
        return

    # 字体设置：Times New Roman
    try:
        mpl.rcParams['font.family'] = 'Times New Roman'
        mpl.rcParams['axes.unicode_minus'] = False
    except Exception:
        pass

    labels = [m.capitalize() for m, _ in data]
    values = [v for _, v in data]
    colors = ['#7E99F4', '#925EB0', '#7AB656']  # 蓝/紫/绿

    plt.figure(figsize=(8, 5))
    bars = plt.bar(labels, values, color=colors, edgecolor='#333333')
    plt.ylabel('Total Relations')
    plt.title('Total Relations by Model (Evaluation Papers)')

    # 数值标注
    for bar, val in zip(bars, values):
        plt.annotate(f'{val}', xy=(bar.get_x() + bar.get_width() / 2, val),
                     xytext=(0, 6), textcoords='offset points', ha='center', va='bottom')

    out_img = output_dir / 'chart_total_relations_by_model.png'
    plt.tight_layout()
    plt.savefig(out_img, dpi=200)
    plt.close()
    print(f'已输出: {out_img}')


if __name__ == '__main__':
    main()
