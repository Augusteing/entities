#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从统计 CSV 中提取高频语义模式，生成 schema.txt（格式参考示例）并可选输出 JSON。

默认会在项目根目录下（本文件所在目录的上上级）寻找 `统计提取结果/semantic_syntactic_patterns_report_*.csv`
中最新的一份，读取列：
  - 语义模式 (Semantic Pattern)
  - 总频次 (Total Freq)
  - 句法实现路径 (Syntactic Realizations)  [用于抽取若干示例，若存在“样例: [X] → [Y]”]

用法（Windows PowerShell）：
  python .\code\make_schema_from_csv.py --minFreq 2 --highFreq 4 \
         --outTxt .\dosc\schema.txt --outJson .\dosc\schema.json

参数：
  --report     手动指定 CSV 路径；默认自动选取统计提取结果中的最新文件
  --minFreq    纳入 schema 的最低频次（含），默认 2
  --highFreq   高置信度阈值（≥highFreq 为高置信度），默认 4
  --maxExamples 每个模式最多展示示例条数，默认 3
  --outTxt     输出的 schema 文本路径，默认 dosc/schema.txt
  --outJson    若提供该路径，同时输出 JSON 结构

输出文本结构：
  ## Schema参考模式
  ### 高置信度模式（频次≥X）
    模式N：S → R → O
      语义模板、主语类型、关系、宾语类型、频次、示例（若有）
  ### 中等置信度模式（频次Y–X-1）
    ...
"""

import argparse
import csv
import glob
import json
import os
import re
from datetime import datetime
from typing import List, Tuple, Optional, Dict

import pandas as pd


# ------------------------- 路径与通用工具 -------------------------
def get_base_dir() -> str:
    """返回项目根目录（包含 统计提取结果/ 与 dosc/ 的目录）。"""
    here = os.path.abspath(os.path.dirname(__file__))
    # 当前文件位于 code/ 下，根目录为其上级目录
    base = os.path.abspath(os.path.join(here, os.pardir))
    return base


def ensure_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def find_latest_report(report_dir: str) -> str:
    pattern = os.path.join(report_dir, 'semantic_syntactic_patterns_report_*.csv')
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError(f"未找到统计 CSV，模式: {pattern}")
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return files[0]


# ------------------------- 模式解析 -------------------------
ARROW_RE = re.compile(r"→|->|➡|⇒")


def split_semantic_pattern(pat: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if not isinstance(pat, str):
        return None, None, None
    parts = [p.strip() for p in ARROW_RE.split(pat)]
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    return None, None, None


EXAMPLE_RE = re.compile(r"样例\s*:\s*\[(?P<s>.+?)\]\s*→\s*\[(?P<o>.+?)\]")


def parse_examples(syntactic_text: str, max_examples: int = 3) -> List[str]:
    """从“句法实现路径”字段中提取若干 [S] → [O] 的样例。
    返回示例字符串列表。
    """
    if not isinstance(syntactic_text, str) or not syntactic_text.strip():
        return []
    examples: List[str] = []
    for line in syntactic_text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = EXAMPLE_RE.search(line)
        if m:
            s = m.group('s').strip()
            o = m.group('o').strip()
            examples.append(f'"{s}" → "{o}"')
            if len(examples) >= max_examples:
                break
    return examples


# 关系到中文语义说明的粗略映射（可按需扩充）
REL_EXPLANATION: Dict[str, str] = {
    '包含': '技术/方法的层次包含关系',
    '结合': '不同技术或方法的融合应用',
    '提升': '对性能指标或能力的提升',
    '提高': '对性能指标或能力的提升',
    '降低': '降低风险或某类不良指标',
    '减少': '降低风险或某类不良指标',
    '解决': '用于解决指定的问题或难题',
    '采用': '在方法/系统中采用某种方法/步骤',
    '基于': '在某种理论/方法/数据的基础上开展',
    '实现': '达成某项结果或目标',
    '应用于': '在具体的应用场景或对象上使用',
    '适用于': '适用的系统/部件范围',
    '预测': '用于预测特定的对象或状态',
    '监测': '对对象的状态或性能进行监测',
    '支持': '提供支持以实现某方法或目标',
    '对比': '比较多个方法/方案的效果',
    '评估': '利用指标或方法开展评估',
}


def build_section_block(rows: List[dict], start_idx: int, max_examples: int) -> Tuple[str, int]:
    """将若干行模式渲染为文本块，带连续的“模式{n}”编号。
    返回 (text, next_index)。
    """
    lines: List[str] = []
    idx = start_idx
    for row in rows:
        pat = str(row['语义模式 (Semantic Pattern)'])
        freq = int(row['总频次 (Total Freq)'])
        s, r, o = split_semantic_pattern(pat)
        if not all([s, r, o]):
            # 跳过无法解析的条目
            continue
        lines.append(f"\n**模式{idx}：{s} → {r} → {o}**")
        lines.append(f"- **语义模板**：\"{pat}\"")
        lines.append(f"- **主语类型**：{s}")
        lines.append(f"- **关系**：{r}")
        lines.append(f"- **宾语类型**：{o}")
        lines.append(f"- **频次**：{freq}")

        # 示例
        examples = parse_examples(row.get('句法实现路径 (Syntactic Realizations)', ''), max_examples=max_examples)
        if examples:
            lines.append(f"- **示例**：")
            for ex in examples:
                lines.append(f"  - {ex}")

        # 简短语义说明（基于关系粗略映射）
        explain = REL_EXPLANATION.get(r)
        if explain:
            lines.append(f"- **语义说明**：{explain}")
        idx += 1
    return "\n".join(lines), idx


def generate_schema_text(df: pd.DataFrame, min_freq: int, high_freq: int, max_examples: int, gt_only: Optional[int] = None) -> str:
    # 只保留需要的列并按频次降序
    required_cols = ['语义模式 (Semantic Pattern)', '总频次 (Total Freq)']
    for c in required_cols:
        if c not in df.columns:
            raise KeyError(f"CSV 缺少必要列: {c}")
    df_use = df.copy()
    df_use['总频次 (Total Freq)'] = pd.to_numeric(df_use['总频次 (Total Freq)'], errors='coerce').fillna(0).astype(int)
    df_use = df_use.sort_values('总频次 (Total Freq)', ascending=False)

    # 过滤低频
    if gt_only is not None:
        # 严格大于阈值
        df_use = df_use[df_use['总频次 (Total Freq)'] > gt_only]
        # 当使用 gt_only 时，更新 min_freq 为 gt_only+1，以便标题文案正确
        min_freq = max(min_freq, gt_only + 1)
    else:
        df_use = df_use[df_use['总频次 (Total Freq)'] >= min_freq]

    # 分段
    high_df = df_use[df_use['总频次 (Total Freq)'] >= high_freq]
    mid_df = df_use[(df_use['总频次 (Total Freq)'] >= min_freq) & (df_use['总频次 (Total Freq)'] < high_freq)]

    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    header = [
        "## Schema参考模式",
        f"以下内容由统计报告自动生成（{ts}）。优先参考但不必严格限制。每个模式包含语义模板、实体类型约束、关系类型和历史频次：",
        "",
        f"### 高置信度模式（频次≥{high_freq}）",
    ]

    text_parts: List[str] = ["\n".join(header)]
    idx = 1
    # 高置信度
    block, idx = build_section_block(high_df.to_dict(orient='records'), idx, max_examples)
    if block.strip():
        text_parts.append(block)
    else:
        text_parts.append("（无符合条件的模式）")

    # 中等置信度
    text_parts.append("")
    if min_freq <= high_freq - 1:
        mid_title = f"### 中等置信度模式（频次{min_freq}–{high_freq-1}）"
    else:
        mid_title = f"### 中等置信度模式（频次≥{min_freq} 且 <{high_freq}）"
    text_parts.append(mid_title)
    block, idx = build_section_block(mid_df.to_dict(orient='records'), idx, max_examples)
    if block.strip():
        text_parts.append(block)
    else:
        text_parts.append("（无符合条件的模式）")

    # 结尾提示
    text_parts.append("")
    text_parts.append("---")
    text_parts.append("注：\n1) 频次越高置信度越高；\n2) 请结合具体上下文审查关系合理性；\n3) 可灵活扩展新关系但建议标注为新模式。")

    return "\n".join(text_parts).strip() + "\n"


def generate_schema_json(df: pd.DataFrame, min_freq: int, high_freq: int, max_examples: int, gt_only: Optional[int] = None) -> dict:
    df_use = df.copy()
    df_use['总频次 (Total Freq)'] = pd.to_numeric(df_use['总频次 (Total Freq)'], errors='coerce').fillna(0).astype(int)
    if gt_only is not None:
        df_use = df_use[df_use['总频次 (Total Freq)'] > gt_only]
        min_freq = max(min_freq, gt_only + 1)
    else:
        df_use = df_use[df_use['总频次 (Total Freq)'] >= min_freq]
    df_use = df_use.sort_values('总频次 (Total Freq)', ascending=False)

    items = []
    for _, row in df_use.iterrows():
        pat = str(row['语义模式 (Semantic Pattern)'])
        freq = int(row['总频次 (Total Freq)'])
        s, r, o = split_semantic_pattern(pat)
        if not all([s, r, o]):
            continue
        examples = parse_examples(row.get('句法实现路径 (Syntactic Realizations)', ''), max_examples=max_examples)
        items.append({
            'template': pat,
            'subject_type': s,
            'relation': r,
            'object_type': o,
            'frequency': freq,
            'confidence': 'high' if freq >= high_freq else 'medium',
            'examples': examples,
        })

    return {
        'generated_at': datetime.now().isoformat(),
        'min_frequency': min_freq,
        'high_frequency': high_freq,
        'greater_than_filter': gt_only,
        'patterns': items,
    }


def main():
    parser = argparse.ArgumentParser(description='从统计 CSV 生成 schema.txt（高频语义模式）')
    parser.add_argument('--report', type=str, default=None, help='CSV 报告路径；缺省自动选择统计提取结果中的最新文件')
    parser.add_argument('--minFreq', type=int, default=2, help='纳入 schema 的最低频次（含）')
    parser.add_argument('--highFreq', type=int, default=4, help='高置信度阈值（≥此值）')
    parser.add_argument('--maxExamples', type=int, default=3, help='每个模式的最大示例数')
    parser.add_argument('--outTxt', type=str, default=None, help='输出 schema 文本路径（默认 dosc/schema.txt）')
    parser.add_argument('--outJson', type=str, default=None, help='若提供则同时输出 JSON 至该路径')
    parser.add_argument('--gt', type=int, default=None, help='仅保留频次严格大于此值的模式（与 --minFreq 互相独立，若提供则优先生效）')
    args = parser.parse_args()

    base_dir = get_base_dir()
    report_dir = os.path.join(base_dir, '统计提取结果')
    out_txt = args.outTxt or os.path.join(base_dir, 'dosc', 'schema.txt')
    out_json = args.outJson  # 可能为 None

    # 读取 CSV
    report_path = args.report or find_latest_report(report_dir)
    print(f"[INFO] 使用统计报告: {report_path}")
    df = pd.read_csv(report_path)

    # 生成文本
    text = generate_schema_text(df, min_freq=args.minFreq, high_freq=args.highFreq, max_examples=args.maxExamples, gt_only=args.gt)
    ensure_dir(out_txt)
    with open(out_txt, 'w', encoding='utf-8', newline='') as f:
        f.write(text)
    print(f"[DONE] schema 文本已保存: {out_txt}")

    # 可选 JSON
    if out_json:
        ensure_dir(out_json)
        payload = generate_schema_json(df, min_freq=args.minFreq, high_freq=args.highFreq, max_examples=args.maxExamples, gt_only=args.gt)
        with open(out_json, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"[DONE] schema JSON 已保存: {out_json}")


if __name__ == '__main__':
    main()
