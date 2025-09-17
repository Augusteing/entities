import json
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple

BASE_DIR = Path(r"e:\知识图谱构建\9.15之前的实验\EXP-2\抽取\评估\数据结果\发送结果_by_gemini")


def safe_list(d: Dict[str, Any], key: str) -> List[Dict[str, Any]]:
    v = d.get(key)
    if isinstance(v, list):
        return v
    return []


def count_eval(items: List[Dict[str, Any]]) -> Tuple[int, int]:
    correct = sum(1 for x in items if isinstance(x, dict) and x.get("evaluation") == "正确")
    total = sum(1 for x in items if isinstance(x, dict) and x.get("evaluation") in {"正确", "错误"})
    return correct, total


def main():
    if not BASE_DIR.exists():
        print(f"目录不存在: {BASE_DIR}")
        return

    files = sorted([p for p in BASE_DIR.glob("*.json") if p.is_file()])
    if not files:
        print("未找到任何 JSON 文件。")
        return

    # 汇总统计
    sum_ent_correct = 0
    sum_ent_total = 0
    sum_rel_correct = 0
    sum_rel_total = 0

    print("文件, 实体-正确数, 实体-错误数, 实体-正确率(%), 关系-正确数, 关系-错误数, 关系-正确率(%)")

    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"{fp.name}, 读取失败: {e}")
            continue

        entities = safe_list(data, "entities")
        relations = safe_list(data, "relations")

        ent_correct, ent_total = count_eval(entities)
        rel_correct, rel_total = count_eval(relations)

        sum_ent_correct += ent_correct
        sum_ent_total += ent_total
        sum_rel_correct += rel_correct
        sum_rel_total += rel_total

        ent_wrong = max(ent_total - ent_correct, 0)
        rel_wrong = max(rel_total - rel_correct, 0)

        ent_acc = (ent_correct / ent_total * 100) if ent_total else 0.0
        rel_acc = (rel_correct / rel_total * 100) if rel_total else 0.0

        print(f"{fp.name}, {ent_correct}, {ent_wrong}, {ent_acc:.2f}, {rel_correct}, {rel_wrong}, {rel_acc:.2f}")

    # 总体
    total_ent_wrong = max(sum_ent_total - sum_ent_correct, 0)
    total_rel_wrong = max(sum_rel_total - sum_rel_correct, 0)

    total_ent_acc = (sum_ent_correct / sum_ent_total * 100) if sum_ent_total else 0.0
    total_rel_acc = (sum_rel_correct / sum_rel_total * 100) if sum_rel_total else 0.0

    print("---- 汇总 ----")
    print(f"实体: 正确 {sum_ent_correct}, 错误 {total_ent_wrong}, 正确率 {total_ent_acc:.2f}% (共 {sum_ent_total})")
    print(f"关系: 正确 {sum_rel_correct}, 错误 {total_rel_wrong}, 正确率 {total_rel_acc:.2f}% (共 {sum_rel_total})")


if __name__ == "__main__":
    main()
