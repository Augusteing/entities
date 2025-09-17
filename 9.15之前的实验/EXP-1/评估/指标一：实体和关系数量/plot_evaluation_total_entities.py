import argparse
import csv
from pathlib import Path
from typing import Dict, List


DEFAULT_COLORS = {
    "gemini": "#925EB0",    # 紫 - 调整gemini为第一位
    "deepseek": "#7E99F4",  # 蓝
    "kimi": "#7AB656",      # 绿
}


def safe_write_text(path: Path, content: str):
    try:
        path.write_text(content, encoding="utf-8")
    except PermissionError:
        fallback = path.with_name(path.stem + ".new" + path.suffix)
        fallback.write_text(content, encoding="utf-8")
        print(f"文件被占用，已改写到: {fallback}")


def load_type_counts_and_sum(csv_path: Path, models: List[str]) -> Dict[str, int]:
    """从实体类型统计CSV中计算每个模型的总实体数量"""
    totals: Dict[str, int] = {m: 0 for m in models}
    
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for model in models:
                try:
                    count = int(str(row.get(model, "0")).strip() or 0)
                    totals[model] += count
                except Exception:
                    pass
    
    return totals


def save_totals_csv(out_csv: Path, totals: Dict[str, int]):
    lines = ["model,total_entities\n"]
    for m in ["gemini", "deepseek", "kimi"]:  # 固定顺序
        if m in totals:
            lines.append(f"{m},{totals[m]}\n")
    try:
        out_csv.write_text("".join(lines), encoding="utf-8")
    except PermissionError:
        fallback = out_csv.with_name(out_csv.stem + ".new" + out_csv.suffix)
        fallback.write_text("".join(lines), encoding="utf-8")
        print(f"文件被占用，已改写到: {fallback}")


def save_totals_md(out_md: Path, totals: Dict[str, int], n_docs: int, color_map: Dict[str, str], bar_image_name: str):
    lines = []
    lines.append("# 三模型实体总量汇总 (50篇评估论文)\n")
    lines.append(f"- 评估论文数量: {n_docs}\n")
    for m in ["gemini", "deepseek", "kimi"]:  # 固定顺序
        if m in totals:
            lines.append(f"- {m.capitalize()}: {totals[m]} (颜色 {color_map.get(m, '')})\n")
    lines.append("\n")
    lines.append(f"![总量柱状图]({bar_image_name})\n")
    safe_write_text(out_md, "\n".join(lines))


def plot_bar(out_path: Path, totals: Dict[str, int], n_docs: int, color_map: Dict[str, str]):
    try:
        import matplotlib.pyplot as plt
        import matplotlib as mpl
    except Exception as e:
        print("未安装 matplotlib 或加载失败，跳过绘图。", e)
        return False

    labels = ["gemini", "deepseek", "kimi"]  # 调整顺序
    values = [totals.get(k, 0) for k in labels]
    colors = [color_map.get(k, "#888888") for k in labels]

    # 全局字体设置为 Times New Roman
    try:
        mpl.rcParams['font.family'] = 'Times New Roman'
    except Exception:
        pass

    plt.figure(figsize=(8, 5))
    bars = plt.bar([l.capitalize() for l in labels], values, color=colors, edgecolor="#333333")
    plt.title(f"Total Extracted Entities (50 Evaluation Papers)")
    plt.ylabel("Total Entities")

    # 在柱子上方标注数值
    for b, v in zip(bars, values):
        plt.text(b.get_x() + b.get_width()/2, b.get_height(), f"{v}", ha='center', va='bottom', fontfamily='Times New Roman')

    # 保存
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        plt.tight_layout()
        plt.savefig(out_path, dpi=200)
        plt.close()
        return True
    except PermissionError:
        fallback = out_path.with_name(out_path.stem + ".new" + out_path.suffix)
        plt.tight_layout()
        plt.savefig(fallback, dpi=200)
        plt.close()
        print(f"文件被占用，已改写到: {fallback}")
        return True
    except Exception as e:
        print("保存图片失败：", e)
        try:
            svg_path = out_path.with_suffix('.svg')
            plt.tight_layout()
            plt.savefig(svg_path)
            plt.close()
            print(f"已改为保存SVG: {svg_path}")
            return True
        except Exception as e2:
            print("保存SVG也失败：", e2)
            plt.close()
            return False


def main():
    # 设置文件路径 - 使用50篇评估论文的数据
    eval_dir = Path(__file__).resolve().parent
    counts_csv = eval_dir / "evaluation_papers_entity_type_counts.csv"
    outdir = eval_dir

    if not counts_csv.exists():
        print(f"错误：找不到数据文件 {counts_csv}")
        return

    models = ["gemini", "deepseek", "kimi"]
    totals = load_type_counts_and_sum(counts_csv, models)
    n_docs = 50  # 固定为50篇评估论文

    out_csv = outdir / "evaluation_papers_total_entities.csv"
    out_md = outdir / "evaluation_papers_total_entities.md"
    out_img = outdir / "evaluation_papers_total_entities.png"

    save_totals_csv(out_csv, totals)
    save_totals_md(out_md, totals, n_docs, DEFAULT_COLORS, out_img.name)
    ok = plot_bar(out_img, totals, n_docs, DEFAULT_COLORS)
    if ok:
        print(f"已输出: {out_csv}")
        print(f"已输出: {out_md}")
        print(f"已输出: {out_img}")
    else:
        print(f"已输出: {out_csv}")
        print(f"已输出: {out_md}")
        print("未能生成柱状图，请安装 matplotlib 后重试：pip install matplotlib")


if __name__ == "__main__":
    main()