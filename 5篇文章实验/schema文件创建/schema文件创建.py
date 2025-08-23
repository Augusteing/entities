#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
从依存路径统计结果 CSV 生成规范化的 schema JSON：
- 读取列："语义模式 (Semantic Pattern)", "总频次 (Total Freq)", "句法实现路径 (Syntactic Realizations)"
- 过滤：最小频次阈值（默认 2）
- 排序并截断：Top-K 语义模式（默认 10）
- 解析语义模式为 subject_type / relation / object_type
 - 解析句法路径条目，提取示例对（from/to）与频次 freq（不再包含路径字符串）
- 输出：schema文件/llm_few_shot_schema_YYYY-MM-DD_HHMMSS.json

可选参数：
  --input CSV 输入文件路径（默认：依存路径提取结果/5篇文章的路径结果.csv）
  --output-dir 输出目录（默认：schema文件）
  --min-freq 最小频次阈值（默认：2）
  --top-k Top K 模式数（默认：10）
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional


def parse_int(value: Any, default: int = 0) -> int:
	if isinstance(value, int):
		return value
	if value is None:
		return default
	s = str(value).strip()
	# 提取第一个连续数字
	m = re.search(r"\d+", s)
	return int(m.group(0)) if m else default


SEMANTIC_SPLITTER = "→"


def parse_semantic_pattern(text: str) -> Dict[str, Optional[str]]:
	text = (text or "").strip()
	parts = [p.strip() for p in text.split(SEMANTIC_SPLITTER)]
	subject_type = parts[0] if len(parts) > 0 else None
	relation = parts[1] if len(parts) > 1 else None
	object_type = parts[2] if len(parts) > 2 else None
	return {
		"semantic_pattern": text,
		"subject_type": subject_type,
		"relation": relation,
		"object_type": object_type,
	}


RE_PATH_LINE = re.compile(
	r"句法路径:\s*(.+?)\s*\(\s*频次:\s*(\d+)\s*,\s*样例:\s*\[(.*?)\]\s*→\s*\[(.*?)\]\s*\)"
)


def parse_syntactic_realizations(block: str) -> List[Dict[str, Any]]:
	results: List[Dict[str, Any]] = []
	if not block:
		return results
	# 保留换行，逐行解析
	for raw_line in block.splitlines():
		line = raw_line.strip()
		if not line:
			continue
		# 去掉可能的列表前缀符号，例如 “- ”、“• ” 等
		line = re.sub(r"^[\-•·]\s*", "", line)
		if "句法路径:" not in line:
			# 非标准行，作为备注保留
			results.append({"raw": line})
			continue
		m = RE_PATH_LINE.search(line)
		if m:
			path, freq, ex_from, ex_to = m.groups()
			results.append(
				{
					"path": path.strip(),
					"freq": parse_int(freq, 1),
					"example": {"from": ex_from.strip(), "to": ex_to.strip()},
				}
			)
		else:
			# 兜底：仅提取“句法路径: …”后面的内容
			try:
				path_text = line.split("句法路径:", 1)[1].strip()
			except Exception:
				path_text = line
			results.append({"path": path_text})
	return results


def load_csv_rows(csv_path: str) -> List[Dict[str, Any]]:
	if not os.path.exists(csv_path):
		raise FileNotFoundError(f"CSV 文件未找到: {csv_path}")
	rows: List[Dict[str, Any]] = []
	# 优先使用 utf-8-sig 以处理可能的 BOM
	with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
		reader = csv.DictReader(f)
		# 兼容中英列名
		# 预处理列名，去空格
		field_map = {}
		for k in reader.fieldnames or []:
			key = (k or "").strip()
			# 标准化几个关键列的可能名称
			lower = key.lower()
			if "语义" in key or "semantic" in lower:
				field_map["semantic"] = key
			elif "总频次" in key or "total" in lower:
				field_map["freq"] = key
			elif "句法" in key or "syntactic" in lower:
				field_map["paths"] = key
		for r in reader:
			rows.append(r)
	# 如果没有识别到必要列，给出提示
	if not {"semantic", "freq", "paths"}.issubset(field_map.keys()):
		raise ValueError(
			"CSV 列名不匹配：需要包含 '语义模式 (Semantic Pattern)', '总频次 (Total Freq)', '句法实现路径 (Syntactic Realizations)'"
		)
	# 映射与清洗
	normalized: List[Dict[str, Any]] = []
	for r in rows:
		semantic_text = r.get(field_map["semantic"], "")
		freq_val = r.get(field_map["freq"], "")
		paths_text = r.get(field_map["paths"], "")
		freq = parse_int(freq_val, 0)
		normalized.append(
			{
				**parse_semantic_pattern(semantic_text),
				"total_freq": freq,
				"syntactic_realizations_raw": paths_text,
			}
		)
	return normalized


def build_schema(
	items: List[Dict[str, Any]],
	min_freq: int = 2,
	top_k: int = 10,
	source_file: Optional[str] = None,
	*,
	compact: bool = True,
	max_examples: int = 2,
	include_meta: bool = True,
) -> Dict[str, Any]:
	# 过滤 + 排序
	filtered = [it for it in items if parse_int(it.get("total_freq", 0), 0) >= min_freq]
	filtered.sort(key=lambda x: (-parse_int(x.get("total_freq", 0), 0), x.get("semantic_pattern", "")))
	selected = filtered[:top_k] if top_k and top_k > 0 else filtered

	# 解析句法路径
	for it in selected:
		raw = it.pop("syntactic_realizations_raw", "")
		syntactic = parse_syntactic_realizations(raw)
		# 排序以挑选示例（按 freq 降序）
		def freq_key(d: Dict[str, Any]) -> int:
			return parse_int(d.get("freq", 0), 0)

		syntactic.sort(key=lambda d: (-freq_key(d), d.get("path", "")))
		it["syntactic_realizations"] = syntactic

		# 收集最多 max_examples 条路径示例（仅保留 from/to 与 freq，不包含路径）
		examples: List[Dict[str, Any]] = []
		for pr in syntactic:
			if len(examples) >= max_examples:
				break
			ex = pr.get("example")
			if isinstance(ex, dict):
				examples.append(
					{
						"from": ex.get("from"),
						"to": ex.get("to"),
						"freq": parse_int(pr.get("freq", 0), 0) or None,
					}
				)
		it["examples"] = examples

	# 构建输出
	meta_common = {
		"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
		"min_freq_threshold": min_freq,
		"top_k": top_k,
		"source_file": source_file,
		"total_patterns": len(items),
		"included_patterns_count": len(selected),
	}

	if not compact:
		return ({"meta": meta_common, "patterns": selected} if include_meta else {"patterns": selected})

	# 精简版：仅保留必要字段 + 最多两个路径示例
	compact_patterns: List[Dict[str, Any]] = []
	for it in selected:
		compact_patterns.append(
			{
				"semantic_pattern": it.get("semantic_pattern"),
				"subject_type": it.get("subject_type"),
				"relation": it.get("relation"),
				"object_type": it.get("object_type"),
				"total_freq": parse_int(it.get("total_freq", 0), 0),
				"examples": it.get("examples", [])[:max_examples],
			}
		)

	meta_obj = {
		**meta_common,
		"format": "compact",
		"max_examples_per_pattern": max_examples,
	}
	return ({"meta": meta_obj, "patterns": compact_patterns} if include_meta else {"patterns": compact_patterns})


def ensure_dir(path: str) -> None:
	if path and not os.path.exists(path):
		os.makedirs(path, exist_ok=True)


def save_schema(schema: Dict[str, Any], output_dir: str) -> str:
	ensure_dir(output_dir)
	ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
	filename = f"llm_few_shot_schema_{ts}.json"
	out_path = os.path.join(output_dir, filename)
	with open(out_path, "w", encoding="utf-8") as f:
		json.dump(schema, f, ensure_ascii=False, indent=2)
	return out_path


def main(argv: Optional[List[str]] = None) -> int:
	parser = argparse.ArgumentParser(description="从依存路径统计 CSV 生成 schema JSON")
	parser.add_argument(
		"--input",
		default=os.path.join("依存路径提取结果", "5篇文章的路径结果.csv"),
		help="CSV 输入文件路径",
	)
	parser.add_argument(
		"--output-dir",
		default=os.path.join("schema文件"),
		help="输出目录",
	)
	parser.add_argument("--min-freq", type=int, default=2, help="最小频次阈值")
	parser.add_argument("--top-k", type=int, default=10, help="Top-K 模式数")
	parser.add_argument("--compact", action="store_true", default=True, help="输出精简格式 JSON")
	parser.add_argument("--max-examples", type=int, default=2, help="每个模式最多的路径示例条数")
	parser.add_argument("--no-meta", action="store_true", help="移除输出中的 meta 字段，仅保留 patterns")

	args = parser.parse_args(argv)

	try:
		items = load_csv_rows(args.input)

		# 统计信息用于打印（不依赖 meta）
		total_patterns = len(items)
		filtered = [it for it in items if parse_int(it.get("total_freq", 0), 0) >= args.min_freq]
		filtered.sort(key=lambda x: (-parse_int(x.get("total_freq", 0), 0), x.get("semantic_pattern", "")))
		included_count = len(filtered[: args.top_k]) if args.top_k and args.top_k > 0 else len(filtered)

		schema = build_schema(
			items,
			min_freq=args.min_freq,
			top_k=args.top_k,
			source_file=args.input,
			compact=args.compact,
			max_examples=args.max_examples,
			include_meta=not args.no_meta,
		)
		out_path = save_schema(schema, args.output_dir)
		print(f"Schema 文件已生成: {out_path}")
		extra = f"；每个模式示例 ≤ {args.max_examples}" if args.compact else ""
		print(f"共 {total_patterns} 个模式，入选 {included_count} 个 (阈值={args.min_freq}, Top-K={args.top_k}){extra}")
		return 0
	except Exception as e:
		print(f"生成失败: {e}")
		return 1


if __name__ == "__main__":
	sys.exit(main())

