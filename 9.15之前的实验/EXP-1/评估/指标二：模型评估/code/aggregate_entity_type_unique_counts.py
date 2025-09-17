#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
from pathlib import Path


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    model_eval_dir = script_dir.parent  # 评估/指标二：模型评估
    src_csv = model_eval_dir / 'entity_types_summary.csv'
    if not src_csv.exists():
        raise SystemExit(f'未找到文件: {src_csv}')

    workspace_root = model_eval_dir.parent.parent  # EXP-1 根
    out_dir = workspace_root / '数据结果'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / 'unique_entity_types_by_model.csv'

    # 统计每模型非零类型行数
    counts = { 'deepseek': 0, 'gemini': 0, 'kimi': 0 }
    with src_csv.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        # 兼容可能的BOM或不同表头
        fields = reader.fieldnames or []
        # 标题名定位
        def find_col(name_substrs):
            for col in fields:
                for s in name_substrs:
                    if s in col:
                        return col
            return None

        col_ds = find_col(['deepseek']) or 'deepseek数量'
        col_ge = find_col(['gemini']) or 'gemini数量'
        col_km = find_col(['kimi']) or 'kimi数量'

        for row in reader:
            try:
                ds = int(str(row.get(col_ds, '0')).strip() or 0)
            except Exception:
                ds = 0
            try:
                ge = int(str(row.get(col_ge, '0')).strip() or 0)
            except Exception:
                ge = 0
            try:
                km = int(str(row.get(col_km, '0')).strip() or 0)
            except Exception:
                km = 0
            if ds > 0:
                counts['deepseek'] += 1
            if ge > 0:
                counts['gemini'] += 1
            if km > 0:
                counts['kimi'] += 1

    with out_csv.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['model', 'unique_entity_types'])
        writer.writeheader()
        for m in ['deepseek', 'gemini', 'kimi']:
            writer.writerow({'model': m, 'unique_entity_types': counts[m]})

    print(f'已生成: {out_csv}')


if __name__ == '__main__':
    main()
