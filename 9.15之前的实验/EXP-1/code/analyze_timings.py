# -*- coding: utf-8 -*-
"""
读取 ndjson 时间日志，统计“真实处理时间”。
- 仅统计 status == "success" 的记录，直接用其中的 duration_seconds。
- 可选：按 paper 聚合，仅取最后一次成功记录（避免重复运行对统计的影响）。
- 支持多个来源目录（如 log_by_kimi / log_by_deepseek）。
- 输出：控制台摘要 + CSV/JSON 报表。

使用示例（Windows PowerShell）：
    python code/analyze_timings.py --roots "数据结果/log_by_kimi/timings.ndjson" "数据结果/log_by_deepseek/timings.ndjson" --unique-latest --out "数据结果/分析/timings"

生成：
    数据结果/分析/timings_summary.csv
    数据结果/分析/timings_summary.json
"""
import os
import csv
import json
import argparse
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INPUTS = [
    os.path.join(BASE_DIR, "数据结果", "log_by_kimi", "timings.ndjson"),
    os.path.join(BASE_DIR, "数据结果", "log_by_deepseek", "timings.ndjson"),
]
DEFAULT_OUT_DIR = os.path.join(BASE_DIR, "数据结果", "分析")


def read_ndjson(path):
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                obj["_source_path"] = path
                rows.append(obj)
            except Exception:
                # 跳过无法解析的行
                continue
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--roots", nargs="*", default=DEFAULT_INPUTS, help="ndjson 文件路径列表")
    parser.add_argument("--unique-latest", action="store_true", help="按 paper 仅保留最后一次成功记录")
    parser.add_argument("--out", default=os.path.join(DEFAULT_OUT_DIR, "timings"), help="输出文件前缀（不含扩展名）")
    args = parser.parse_args()

    # 读取所有文件
    all_rows = []
    for p in args.roots:
        all_rows.extend(read_ndjson(p))

    # 仅保留成功记录
    success_rows = [r for r in all_rows if str(r.get("status")).lower() == "success"]

    # 可选：按 paper 仅取最后一次成功
    if args.unique_latest:
        grouped = defaultdict(list)
        for r in success_rows:
            grouped[r.get("paper")] .append(r)
        success_rows = [sorted(v, key=lambda x: x.get("time", ""))[-1] for v in grouped.values()]

    # 汇总统计
    total = len(success_rows)
    total_duration = sum(float(r.get("duration_seconds", 0) or 0) for r in success_rows)

    # 输出目录
    out_prefix = args.out
    out_dir = os.path.dirname(out_prefix)
    os.makedirs(out_dir, exist_ok=True)

    # 写 CSV
    csv_path = out_prefix + "_summary.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["paper", "provider", "model", "duration_seconds", "attempts", "time", "source_log"])
        for r in sorted(success_rows, key=lambda x: x.get("paper", "")):
            w.writerow([
                r.get("paper"), r.get("provider"), r.get("model"), r.get("duration_seconds"), r.get("attempts"), r.get("time"), r.get("_source_path")
            ])
        w.writerow([])
        w.writerow(["TOTAL_ITEMS", total])
        w.writerow(["TOTAL_DURATION_SECONDS", round(total_duration, 3)])

    # 写 JSON 汇总
    json_path = out_prefix + "_summary.json"
    summary = {
        "total_items": total,
        "total_duration_seconds": round(total_duration, 3),
        "avg_duration_seconds": round(total_duration / total, 3) if total else 0.0,
        "items": success_rows,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # 控制台摘要
    print(f"成功条目: {total}")
    print(f"总处理时长(s): {round(total_duration, 3)}")
    if total:
        print(f"平均时长(s): {round(total_duration / total, 3)}")
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")


if __name__ == "__main__":
    main()
