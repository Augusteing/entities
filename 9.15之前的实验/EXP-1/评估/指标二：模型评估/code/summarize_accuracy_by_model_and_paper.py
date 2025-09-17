import os
import json
import csv
from pathlib import Path
from typing import Tuple, Dict, Any


BASE_DIR = Path(__file__).resolve().parents[1]
# 结果根目录与输入、输出目录
RESULTS_ROOT = BASE_DIR / "结果分三个模型保存"
OUTPUT_DIR = BASE_DIR / "结果"
OUTPUT_CSV = OUTPUT_DIR / "model_paper_accuracy.csv"


def safe_count(items: Any) -> Tuple[int, int]:
    """统计列表中 evaluation 为“正确/错误”的数量。

    返回 (correct, total)。若 evaluation 缺失或不是上述值，则不计入 total。
    """
    correct = 0
    total = 0
    if not isinstance(items, list):
        return 0, 0
    for x in items:
        if not isinstance(x, dict):
            continue
        val = x.get("evaluation")
        if val in ("正确", "错误"):
            total += 1
            if val == "正确":
                correct += 1
    return correct, total


def compute_metrics_for_file(fp: Path) -> Dict[str, Any]:
    """读取单个结果 JSON，计算实体、关系与总体准确率。"""
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
    except Exception as e:
        return {
            "paper": fp.stem,
            "error": f"读取失败: {e}",
        }

    ent_c, ent_t = safe_count(data.get("entities"))
    rel_c, rel_t = safe_count(data.get("relations"))
    all_c = ent_c + rel_c
    all_t = ent_t + rel_t

    def acc(c: int, t: int):
        return round(c / t, 4) if t > 0 else None

    return {
        "paper": fp.stem,
        "entity_correct": ent_c,
        "entity_total": ent_t,
        "entity_accuracy": acc(ent_c, ent_t),
        "relation_correct": rel_c,
        "relation_total": rel_t,
        "relation_accuracy": acc(rel_c, rel_t),
        "overall_correct": all_c,
        "overall_total": all_t,
        "overall_accuracy": acc(all_c, all_t),
    }


def main():
    if not RESULTS_ROOT.exists():
        raise SystemExit(f"未找到目录: {RESULTS_ROOT}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 模型子目录（自动枚举）
    model_dirs = [p for p in RESULTS_ROOT.iterdir() if p.is_dir()]
    model_dirs.sort()

    rows = []
    for model_dir in model_dirs:
        model_name = model_dir.name
        # 遍历该模型下所有 json 文件
        for fp in sorted(model_dir.glob("*.json")):
            m = compute_metrics_for_file(fp)
            row = {
                "model": model_name,
                **m,
            }
            rows.append(row)

    # 写出 CSV
    fieldnames = [
        "model",
        "paper",
        "entity_correct",
        "entity_total",
        "entity_accuracy",
        "relation_correct",
        "relation_total",
        "relation_accuracy",
        "overall_correct",
        "overall_total",
        "overall_accuracy",
        "error",
    ]

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            # 确保缺失字段存在
            for k in fieldnames:
                r.setdefault(k, None)
            writer.writerow(r)

    print(f"已生成: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
