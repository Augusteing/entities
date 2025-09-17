import argparse
import csv
from pathlib import Path
from typing import Dict, List


DEFAULT_COLORS = {
    "deepseek": "#925EB0",  # 紫
    "gemini": "#7E99F4",    # 蓝
    "kimi": "#7AB656",      # 绿
}


def safe_write_text(path: Path, content: str):
    try:
        path.write_text(content, encoding="utf-8")
    except PermissionError:
        fallback = path.with_name(path.stem + ".new" + path.suffix)
        fallback.write_text(content, encoding="utf-8")
        print(f"文件被占用，已改写到: {fallback}")


def load_per_article_counts(csv_path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def sum_totals(rows: List[Dict[str, str]], model_cols: List[str]) -> Dict[str, int]:
    totals: Dict[str, int] = {m: 0 for m in model_cols}
    for r in rows:
        for m in model_cols:
            try:
                totals[m] += int(str(r.get(m, "0")).strip() or 0)
            except Exception:
                pass
    return totals


def save_totals_csv(out_csv: Path, totals: Dict[str, int]):
    lines = ["model,total_entities\n"]
    for m, v in totals.items():
        lines.append(f"{m},{v}\n")
    try:
        out_csv.write_text("".join(lines), encoding="utf-8")
    except PermissionError:
        fallback = out_csv.with_name(out_csv.stem + ".new" + out_csv.suffix)
        fallback.write_text("".join(lines), encoding="utf-8")
        print(f"文件被占用，已改写到: {fallback}")


def save_totals_md(out_md: Path, totals: Dict[str, int], n_docs: int, color_map: Dict[str, str], bar_image_name: str):
    lines = []
    lines.append("# 三模型实体总量汇总\n")
    lines.append(f"- 共同文章数量: {n_docs}\n")
    for m in ["deepseek", "gemini", "kimi"]:
        if m in totals:
            lines.append(f"- {m}: {totals[m]} (颜色 {color_map.get(m, '')})\n")
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

    labels = ["deepseek", "gemini", "kimi"]
    values = [totals.get(k, 0) for k in labels]
    colors = [color_map.get(k, "#888888") for k in labels]

    # 全局字体设置为 Times New Roman
    try:
        mpl.rcParams['font.family'] = 'Times New Roman'
    except Exception:
        pass

    plt.figure(figsize=(6, 4))
    bars = plt.bar(labels, values, color=colors, edgecolor="#333333")
    plt.title(f"Total Extracted Entities (Common Docs N={n_docs})")
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
    parser = argparse.ArgumentParser(description="汇总三模型实体总量并绘制柱状图")
    parser.add_argument("--input", type=str, default=None, help="输入 per-article CSV，默认使用项目内统计文件")
    parser.add_argument("--outdir", type=str, default=None, help="输出目录，默认 数据结果/统计")
    args = parser.parse_args()

    exp1_root = Path(__file__).resolve().parent.parent
    stat_dir = exp1_root / "数据结果" / "统计"
    in_csv = Path(args.input) if args.input else (stat_dir / "common_docs_per_article_entity_counts.csv")
    outdir = Path(args.outdir) if args.outdir else stat_dir

    rows = load_per_article_counts(in_csv)
    n_docs = len(rows)
    model_cols = [c for c in ("deepseek", "gemini", "kimi") if (rows and c in rows[0])]
    totals = sum_totals(rows, model_cols)

    out_csv = outdir / "total_entities_by_model.csv"
    out_md = outdir / "total_entities_by_model.md"
    out_img = outdir / "total_entities_by_model.png"

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
