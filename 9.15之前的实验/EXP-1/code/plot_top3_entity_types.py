import argparse
import csv
from pathlib import Path
from typing import Dict, List, Tuple


RANK_COLORS = {
    1: "#925EB0",  # Top1 紫
    2: "#7E99F4",  # Top2 蓝
    3: "#7AB656",  # Top3 绿
}

TYPE_EN_MAP: Dict[str, str] = {
    # 常见类型中英映射，未命中则回退原文
    "算法": "Algorithm",
    "技术": "Technology",
    "模型": "Model",
    "性能指标": "Metric",
    "系统": "System",
    "方法": "Method",
    "参数": "Parameter",
    "概念": "Concept",
    "组织": "Organization",
    "机构": "Organization",
}


def safe_write_text(path: Path, content: str):
    try:
        path.write_text(content, encoding="utf-8")
    except PermissionError:
        fallback = path.with_name(path.stem + ".new" + path.suffix)
        fallback.write_text(content, encoding="utf-8")
        print(f"文件被占用，已改写到: {fallback}")


def read_type_counts_csv(csv_path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = [r for r in reader]
    return fieldnames, rows


def compute_top3_by_model(rows: List[Dict[str, str]], models: List[str]) -> Dict[str, List[Tuple[str, int]]]:
    result: Dict[str, List[Tuple[str, int]]] = {}
    for m in models:
        pairs: List[Tuple[str, int]] = []
        for r in rows:
            t = r.get("type", "")
            try:
                val = int(str(r.get(m, "0")).strip() or 0)
            except Exception:
                val = 0
            if val > 0:
                pairs.append((t, val))
        pairs.sort(key=lambda x: x[1], reverse=True)
        result[m] = pairs[:3]
    return result


def load_n_docs(per_article_csv: Path) -> int:
    try:
        with per_article_csv.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return sum(1 for _ in reader)
    except Exception:
        return 0


def save_top3_csv(out_csv: Path, top3: Dict[str, List[Tuple[str, int]]]):
    lines = ["model,rank,type,count\n"]
    for m, items in top3.items():
        for i, (t, c) in enumerate(items, start=1):
            lines.append(f"{m},{i},{t},{c}\n")
    try:
        out_csv.write_text("".join(lines), encoding="utf-8")
    except PermissionError:
        fallback = out_csv.with_name(out_csv.stem + ".new" + out_csv.suffix)
        fallback.write_text("".join(lines), encoding="utf-8")
        print(f"文件被占用，已改写到: {fallback}")


def save_top3_md(out_md: Path, top3: Dict[str, List[Tuple[str, int]]], n_docs: int, img_name: str):
    lines = []
    lines.append("# Top-3 Entity Types per Model\n")
    if n_docs:
        lines.append(f"- Common docs: {n_docs}\n")
    for m in ["deepseek", "gemini", "kimi"]:
        if m in top3:
            items = top3[m]
            lines.append(f"\n## {m}\n")
            lines.append("Rank | Type | Count\n")
            lines.append("---|---|---\n")
            for i, (t, c) in enumerate(items, start=1):
                lines.append(f"Top{i} | {t} | {c}\n")
    lines.append("\n")
    lines.append(f"![Top-3 Types per Model]({img_name})\n")
    safe_write_text(out_md, "\n".join(lines))


def plot_grouped_bar(out_img: Path, top3: Dict[str, List[Tuple[str, int]]], n_docs: int):
    try:
        import matplotlib.pyplot as plt
        import matplotlib as mpl
        import numpy as np
    except Exception as e:
        print("未安装绘图库，跳过绘图：", e)
        return False

    # 字体设为 Times New Roman
    try:
        mpl.rcParams['font.family'] = 'Times New Roman'
    except Exception:
        pass

    models = ["deepseek", "gemini", "kimi"]
    # 准备数据，确保缺项用0补齐
    heights = []  # shape: (3 ranks, len(models))
    labels_rank = ["Top1", "Top2", "Top3"]
    type_labels_per_model = {m: ["", "", ""] for m in models}
    for rank in [1, 2, 3]:
        row = []
        for m in models:
            items = top3.get(m, [])
            if len(items) >= rank:
                t, c = items[rank - 1]
                row.append(c)
                type_labels_per_model[m][rank - 1] = t
            else:
                row.append(0)
        heights.append(row)

    x = np.arange(len(models))
    width = 0.22

    plt.figure(figsize=(9, 5))
    # 每组三柱分别用紫、蓝、绿
    for idx, rank in enumerate([1, 2, 3]):
        plt.bar(x + (idx - 1) * width, heights[idx], width=width, color=RANK_COLORS[rank], edgecolor="#333333", label=labels_rank[idx])

    plt.xticks(x, models)
    plt.ylabel("Count")
    title = f"Top-3 Entity Types per Model (Common Docs N={n_docs})" if n_docs else "Top-3 Entity Types per Model"
    plt.title(title)
    plt.legend()

    # 在每个柱上方标注：英文类型 + 计数，例如 "Algorithm (533)"
    for idx, (rank, h) in enumerate(zip([1, 2, 3], heights)):
        for j, (xi, val) in enumerate(zip(x + (idx - 1) * width, h)):
            m = models[j]
            t_cn = type_labels_per_model[m][rank - 1]
            t_en = TYPE_EN_MAP.get(t_cn, t_cn)
            label = f"{t_en} ({val})" if val else ""
            if not label:
                continue
            # 针对 deepseek 组（索引0）的三柱做微调：左右轻微错位，并在点数坐标系上上移，避免遮挡
            if m == "deepseek":
                # 更强的左右分离：Top1 明显左移，Top2 轻微右移，Top3 轻微右移
                if rank == 1:  # Algorithm(533)
                    h_shift = -width * 0.38
                    v_points = 10
                elif rank == 2:  # Technology(525)
                    h_shift = width * 0.18
                    v_points = 12
                else:  # rank == 3
                    h_shift = width * 0.28
                    v_points = 10
                plt.annotate(label, xy=(xi + h_shift, val), xytext=(0, v_points),
                             textcoords='offset points', ha='center', va='bottom', fontsize=9)
            else:
                # 其它组统一上移 6pt，减少与柱顶重合风险
                plt.annotate(label, xy=(xi, val), xytext=(0, 6), textcoords='offset points',
                             ha='center', va='bottom', fontsize=9)

    try:
        out_img.parent.mkdir(parents=True, exist_ok=True)
        plt.tight_layout()
        plt.savefig(out_img, dpi=200)
        plt.close()
        return True
    except PermissionError:
        fallback = out_img.with_name(out_img.stem + ".new" + out_img.suffix)
        plt.tight_layout()
        plt.savefig(fallback, dpi=200)
        plt.close()
        print(f"文件被占用，已改写到: {fallback}")
        return True
    except Exception as e:
        print("保存图片失败：", e)
        try:
            svg_path = out_img.with_suffix('.svg')
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
    parser = argparse.ArgumentParser(description="绘制每模型Top-3实体类型分组柱状图")
    parser.add_argument("--counts", type=str, default=None, help="输入类型计数CSV，默认: 数据结果/统计/common_docs_entity_type_counts.csv")
    parser.add_argument("--perdoc", type=str, default=None, help="输入每文档计数CSV(用于N)，默认: 数据结果/统计/common_docs_per_article_entity_counts.csv")
    parser.add_argument("--outdir", type=str, default=None, help="输出目录，默认: 数据结果/统计")
    args = parser.parse_args()

    exp1_root = Path(__file__).resolve().parent.parent
    stat_dir = exp1_root / "数据结果" / "统计"
    counts_csv = Path(args.counts) if args.counts else (stat_dir / "common_docs_entity_type_counts.csv")
    perdoc_csv = Path(args.perdoc) if args.perdoc else (stat_dir / "common_docs_per_article_entity_counts.csv")
    outdir = Path(args.outdir) if args.outdir else stat_dir

    _, rows = read_type_counts_csv(counts_csv)
    models = ["deepseek", "gemini", "kimi"]
    top3 = compute_top3_by_model(rows, models)
    n_docs = load_n_docs(perdoc_csv)

    out_csv = outdir / "top3_entity_types_by_model.csv"
    out_md = outdir / "top3_entity_types_by_model.md"
    out_img = outdir / "top3_entity_types_by_model.png"

    save_top3_csv(out_csv, top3)
    save_top3_md(out_md, top3, n_docs, out_img.name)
    ok = plot_grouped_bar(out_img, top3, n_docs)
    if ok:
        print(f"已输出: {out_csv}")
        print(f"已输出: {out_md}")
        print(f"已输出: {out_img}")
    else:
        print(f"已输出: {out_csv}")
        print(f"已输出: {out_md}")
        print("未能生成分组柱状图，请安装 matplotlib 后重试：pip install matplotlib numpy")


if __name__ == "__main__":
    main()
