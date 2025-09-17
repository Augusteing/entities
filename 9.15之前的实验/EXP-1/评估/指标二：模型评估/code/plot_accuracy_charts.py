import csv
from pathlib import Path
from collections import defaultdict
from statistics import mean
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np


BASE_DIR = Path(__file__).resolve().parents[1]
INPUT_CSV = BASE_DIR / "结果" / "model_paper_accuracy.csv"
OUTPUT_DIR = BASE_DIR / "结果"

# 颜色方案（来自用户提供截图）
COLORS = {
    "grey": "#A5AEB7",
    "purple": "#925EB0",
    "blue": "#7E99F4",
    "red": "#CC7C71",
    "green": "#7AB656",
}

# Use English font: Times New Roman
plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["axes.unicode_minus"] = False

def annotate_bars(rects, vals, fmt: str = "{:.2f}", skip_eq_one: bool = True, ax=None):
    """在柱顶部添加数值标注。
    - rects: bar 容器
    - vals: 对应的数值列表
    - skip_eq_one: 若值为 1.0 则不标注
    """
    if ax is None:
        ax = plt.gca()
    for rect, val in zip(rects, vals):
        if val is None:
            continue
        try:
            if np.isnan(val):
                continue
        except TypeError:
            pass
        if skip_eq_one and abs(val - 1.0) < 1e-9:
            continue
        height = rect.get_height()
        ax.annotate(
            fmt.format(val),
            xy=(rect.get_x() + rect.get_width() / 2.0, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
        )


def read_rows() -> List[Dict]:
    rows: List[Dict] = []
    with INPUT_CSV.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # 将数字列转换类型
            for k in [
                "entity_correct", "entity_total", "relation_correct", "relation_total",
                "overall_correct", "overall_total"
            ]:
                if r.get(k):
                    r[k] = int(float(r[k])) if r[k] not in ("", None) else 0
                else:
                    r[k] = 0
            for k in ["entity_accuracy", "relation_accuracy", "overall_accuracy"]:
                if r.get(k) not in ("", None, "None"):
                    r[k] = float(r[k])
                else:
                    r[k] = None
            rows.append(r)
    return rows


def agg_by_model(rows: List[Dict]) -> Dict[str, Dict[str, float]]:
    accs: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        model = r["model"]
        for key in ("entity_accuracy", "relation_accuracy", "overall_accuracy"):
            if r[key] is not None:
                accs[model][key].append(r[key])
    out: Dict[str, Dict[str, float]] = {}
    for m, d in accs.items():
        out[m] = {k: mean(v) if v else None for k, v in d.items()}
    return out


def plot_model_mean_bar(agg: Dict[str, Dict[str, float]]):
    # 模型平均准确率：实体/关系/总体 三组分组柱形
    metrics = ["entity_accuracy", "relation_accuracy", "overall_accuracy"]
    metric_labels = ["Entities", "Relations", "Overall"]
    models = sorted(agg.keys())
    x = np.arange(len(metrics))
    width = 0.8 / max(len(models), 1)

    color_cycle = [COLORS["purple"], COLORS["blue"], COLORS["green"], COLORS["red"], COLORS["grey"]]

    plt.figure(figsize=(9, 5))
    for i, m in enumerate(models):
        vals = [agg[m].get(k, None) for k in metrics]
        vals = [v if v is not None else 0.0 for v in vals]
        rects = plt.bar(
            x + i * width - (len(models) - 1) * width / 2,
            vals,
            width=width,
            label=m,
            color=color_cycle[i % len(color_cycle)],
        )
        annotate_bars(rects, vals, fmt="{:.2f}")

    plt.xticks(x, metric_labels)
    plt.ylim(0, 1.0)
    plt.ylabel("Mean accuracy")
    plt.title("Average accuracy by model (Entities/Relations/Overall)")
    plt.legend(loc="center left", bbox_to_anchor=(1.0, 0.5))
    plt.grid(axis="y", linestyle=":", alpha=0.3)
    out = OUTPUT_DIR / "chart_model_mean_accuracy.png"
    plt.tight_layout()
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()


def plot_model_overall_box(rows: List[Dict]):
    # 各模型总体准确率箱线图
    model_to_vals: Dict[str, List[float]] = defaultdict(list)
    for r in rows:
        if r["overall_accuracy"] is not None:
            model_to_vals[r["model"]].append(r["overall_accuracy"])

    models = sorted(model_to_vals.keys())
    data = [model_to_vals[m] for m in models]

    plt.figure(figsize=(8, 5))
    bp = plt.boxplot(data, patch_artist=True, tick_labels=models)
    fill_colors = [COLORS["purple"], COLORS["blue"], COLORS["green"], COLORS["red"], COLORS["grey"]]
    for patch, c in zip(bp['boxes'], fill_colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.7)
    plt.ylim(0, 1.0)
    plt.ylabel("Overall accuracy")
    plt.title("Distribution of overall accuracy by model (box plot)")
    plt.grid(axis="y", linestyle=":", alpha=0.3)
    out = OUTPUT_DIR / "chart_model_overall_accuracy_box.png"
    plt.tight_layout()
    plt.savefig(out, dpi=200)
    plt.close()


def plot_worst_papers(rows: List[Dict], topn: int = 15):
    # 找出总体准确率均值最低的前N篇（按跨模型平均）
    paper_to_vals: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for r in rows:
        if r["overall_accuracy"] is not None:
            paper_to_vals[r["paper"]].append((r["model"], r["overall_accuracy"]))

    paper_to_mean = []
    for p, lst in paper_to_vals.items():
        if lst:
            paper_to_mean.append((p, mean([v for _, v in lst])))
    paper_to_mean.sort(key=lambda x: x[1])
    worst = paper_to_mean[:topn]
    selected_papers = [p for p, _ in worst]

    # 准备数据：每个模型在这些论文上的总体准确率
    models = sorted({r["model"] for r in rows})
    model_to_vals: Dict[str, List[float]] = {m: [] for m in models}
    # 建立查找
    index: Dict[Tuple[str, str], float] = {}
    for r in rows:
        if r["paper"] in selected_papers and r["overall_accuracy"] is not None:
            index[(r["paper"], r["model"])] = r["overall_accuracy"]
    for p in selected_papers:
        for m in models:
            model_to_vals[m].append(index.get((p, m), np.nan))

    # 画分组条形图
    x = np.arange(len(selected_papers))
    width = 0.8 / max(len(models), 1)
    color_cycle = [COLORS["purple"], COLORS["blue"], COLORS["green"], COLORS["red"], COLORS["grey"]]

    plt.figure(figsize=(max(10, len(selected_papers) * 0.7), 6))
    for i, m in enumerate(models):
        vals = model_to_vals[m]
        rects = plt.bar(
            x + i * width - (len(models) - 1) * width / 2,
            vals,
            width=width,
            label=m,
            color=color_cycle[i % len(color_cycle)],
        )
        annotate_bars(rects, vals, fmt="{:.2f}")

    # Use English index labels instead of original (possibly non-English) paper names
    index_labels = [f"Paper {i+1}" for i in range(len(selected_papers))]
    plt.xticks(x, index_labels, rotation=45, ha='right')
    plt.ylim(0, 1.0)
    plt.ylabel("Overall accuracy")
    plt.title(f"Bottom {topn} papers by overall accuracy (across models)")
    plt.legend(loc="center left", bbox_to_anchor=(1.0, 0.5))
    plt.grid(axis="y", linestyle=":", alpha=0.3)
    out = OUTPUT_DIR / "chart_worst_papers_overall_accuracy.png"
    plt.tight_layout()
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()

    # Save mapping of index label to original paper name and mean accuracy (for reference)
    mapping_csv = OUTPUT_DIR / "worst_papers_mapping.csv"
    with mapping_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["index_label", "paper", "mean_overall_accuracy"])
        for i, (p, macc) in enumerate(worst, start=1):
            writer.writerow([f"Paper {i}", p, f"{macc:.4f}"])


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = read_rows()
    if not rows:
        print("未读取到任何数据，检查输入CSV是否存在且非空。")
        return

    agg = agg_by_model(rows)
    plot_model_mean_bar(agg)
    plot_model_overall_box(rows)
    plot_worst_papers(rows, topn=15)
    print("已生成图表：\n - chart_model_mean_accuracy.png\n - chart_model_overall_accuracy_box.png\n - chart_worst_papers_overall_accuracy.png")


if __name__ == "__main__":
    main()
