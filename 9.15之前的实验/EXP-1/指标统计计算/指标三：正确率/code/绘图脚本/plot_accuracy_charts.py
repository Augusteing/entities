# -*- coding: utf-8 -*-
import os
import json
from pathlib import Path
from typing import Dict, Tuple

import matplotlib
import matplotlib.pyplot as plt
import csv


# 根目录
ROOT = Path(r"e:\知识图谱构建\9.15之前的实验\EXP-1")

# 输入：评估标注后的结果目录（包含 evaluation 字段）
EVAL_BASE = ROOT / "评估" / "数据结果"

# 三个模型目录
MODEL_DIRS = {
    "deepseek": EVAL_BASE / "deepseek",
    "gemini": EVAL_BASE / "gemini",
    "kimi": EVAL_BASE / "kimi",
}

# 输出：表格与图片
OUT_DIR_IMG = ROOT / "实验过程图" / "指标二：模型评估" / "正确率"
OUT_DIR_IMG.mkdir(parents=True, exist_ok=True)
OUT_DIR_CSV = ROOT / "评估" / "数据结果" / "表格结果"
OUT_DIR_CSV.mkdir(parents=True, exist_ok=True)
CSV_PATH = OUT_DIR_CSV / "模型_实体关系_正确率统计.csv"

# 颜色（按需求两种）
COLOR_ENTITY_ACC = "#925EB0"  # 紫（实体正确率）
COLOR_REL_ACC = "#7AB656"     # 绿（关系正确率）


def set_chinese_font():
    """设置中文字体，避免中文乱码。"""
    matplotlib.rcParams['axes.unicode_minus'] = False
    preferred = ['Microsoft YaHei', 'SimHei', 'STHeiti', 'Songti SC', 'Arial Unicode MS']
    try:
        from matplotlib import font_manager
        available = {f.name for f in font_manager.fontManager.ttflist}
        for name in preferred:
            if name in available:
                matplotlib.rcParams['font.sans-serif'] = [name]
                return
    except Exception:
        pass
    matplotlib.rcParams['font.sans-serif'] = ['sans-serif']


def _is_correct(val) -> bool:
    """统一判断 evaluation 是否为正确。"""
    if val is None:
        return False
    if isinstance(val, bool):
        return bool(val)
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        v = val.strip().lower()
        return v in {"正确", "correct", "true", "yes", "y", "是"}
    return False


def read_json(path: Path):
    try:
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def accumulate_for_model(model_dir: Path) -> Tuple[int, int, int, int]:
    """
    返回：(实体总数, 实体正确数, 关系总数, 关系正确数)
    缺 evaluation 视为不正确。
    """
    ent_total = ent_correct = 0
    rel_total = rel_correct = 0
    if not model_dir.exists():
        return 0, 0, 0, 0
    for fp in model_dir.glob('*.json'):
        data = read_json(fp)
        if not isinstance(data, dict):
            continue
        entities = data.get('entities', []) or []
        relations = data.get('relations', []) or []
        # 实体
        ent_total += len(entities)
        for e in entities:
            if isinstance(e, dict) and _is_correct(e.get('evaluation')):
                ent_correct += 1
        # 关系
        rel_total += len(relations)
        for r in relations:
            if isinstance(r, dict) and _is_correct(r.get('evaluation')):
                rel_correct += 1
    return ent_total, ent_correct, rel_total, rel_correct


def pct(numer: int, denom: int) -> float:
    if not denom:
        return 0.0
    return (numer / denom) * 100.0


def save_csv(rows: Dict[str, Dict[str, str]]):
    headers = [
        "模型", "实体总数", "实体正确数量", "实体正确率", "关系总数", "关系正确数量", "关系正确率"
    ]
    with CSV_PATH.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for model_key in ["deepseek", "gemini", "kimi"]:
            r = rows.get(model_key) or {}
            writer.writerow([
                r.get("模型", model_key),
                r.get("实体总数", 0),
                r.get("实体正确数量", 0),
                r.get("实体正确率", "0.00%"),
                r.get("关系总数", 0),
                r.get("关系正确数量", 0),
                r.get("关系正确率", "0.00%"),
            ])


def plot_model_chart(model_key: str, ent_acc: float, rel_acc: float):
    # 两个柱：实体正确率、关系正确率
    labels = ["实体正确率", "关系正确率"]
    values = [ent_acc, rel_acc]
    colors = [COLOR_ENTITY_ACC, COLOR_REL_ACC]

    plt.figure(figsize=(6.5, 4.5), dpi=150)
    # 取消背景虚线：不画网格
    bars = plt.bar(labels, values, color=colors, edgecolor="#333333")
    # 标注百分比（两位小数）
    for bar, v in zip(bars, values):
        top = max(values)
        offset = top * 0.01 if top > 0 else 1
        plt.text(bar.get_x() + bar.get_width()/2, v + offset, f"{v:.2f}%", ha='center', va='bottom', fontsize=11)

    title_map = {"deepseek": "DeepSeek", "gemini": "Gemini", "kimi": "Kimi"}
    title = f"{title_map.get(model_key, model_key)} 实体/关系正确率（全量结果）"
    plt.title(title, fontsize=14, pad=10)
    plt.ylabel("正确率 (%)", fontsize=12)
    plt.ylim(0, max(100, max(values) * 1.12 if max(values) > 0 else 100))
    # 移除顶部和右侧脊柱，让画面更简洁
    ax = plt.gca()
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    out_path = OUT_DIR_IMG / f"{model_key}_实体关系正确率.png"
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()
    print(f"保存图表: {out_path}")


def main():
    set_chinese_font()

    rows: Dict[str, Dict[str, str]] = {}
    for model_key, model_dir in MODEL_DIRS.items():
        ent_total, ent_correct, rel_total, rel_correct = accumulate_for_model(model_dir)
        ent_acc = pct(ent_correct, ent_total)
        rel_acc = pct(rel_correct, rel_total)
        rows[model_key] = {
            "模型": {"deepseek": "DeepSeek", "gemini": "Gemini", "kimi": "Kimi"}.get(model_key, model_key),
            "实体总数": ent_total,
            "实体正确数量": ent_correct,
            "实体正确率": f"{ent_acc:.2f}%",
            "关系总数": rel_total,
            "关系正确数量": rel_correct,
            "关系正确率": f"{rel_acc:.2f}%",
        }

        plot_model_chart(model_key, ent_acc, rel_acc)

    save_csv(rows)
    print(f"统计表已保存: {CSV_PATH}")


if __name__ == "__main__":
    main()
