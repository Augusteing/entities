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
    "研究结果": "Research Result",
    "函数": "Function",
    "飞机型号": "Aircraft Model",
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
    # 处理BOM字符问题
    type_key = "type"
    if rows and "type" not in rows[0]:
        for key in rows[0].keys():
            if "type" in key:
                type_key = key
                break
    
    for m in models:
        pairs: List[Tuple[str, int]] = []
        for r in rows:
            t = r.get(type_key, "")
            try:
                val = int(str(r.get(m, "0")).strip() or 0)
            except Exception:
                val = 0
            if val > 0 and t:  # 确保类型名称不为空
                pairs.append((t, val))
        pairs.sort(key=lambda x: x[1], reverse=True)
        result[m] = pairs[:3]
    return result


def save_top3_csv(out_csv: Path, top3: Dict[str, List[Tuple[str, int]]]):
    lines = ["model,rank,type,count\n"]
    for m, items in top3.items():
        for i, (t, c) in enumerate(items, start=1):
            # 确保实体类型名称被正确保存
            type_name = t.replace(',', '，')  # 替换逗号避免CSV格式问题
            lines.append(f"{m},{i},{type_name},{c}\n")
    try:
        out_csv.write_text("".join(lines), encoding="utf-8")
    except PermissionError:
        fallback = out_csv.with_name(out_csv.stem + ".new" + out_csv.suffix)
        fallback.write_text("".join(lines), encoding="utf-8")
        print(f"文件被占用，已改写到: {fallback}")


def save_top3_md(out_md: Path, top3: Dict[str, List[Tuple[str, int]]], n_docs: int, img_name: str):
    lines = []
    lines.append("# Top-3 Entity Types per Model (50 Evaluation Papers)\n")
    lines.append(f"- Evaluation Papers: {n_docs}\n")
    for m in ["gemini", "deepseek", "kimi"]:  # 调整顺序，gemini第一
        if m in top3:
            items = top3[m]
            lines.append(f"\n## {m.capitalize()}\n")
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

    models = ["gemini", "deepseek", "kimi"]  # 调整顺序，gemini第一
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

    plt.figure(figsize=(10, 6))
    # 每组三柱分别用紫、蓝、绿
    for idx, rank in enumerate([1, 2, 3]):
        plt.bar(x + (idx - 1) * width, heights[idx], width=width, color=RANK_COLORS[rank], edgecolor="#333333", label=labels_rank[idx])

    plt.xticks(x, [m.capitalize() for m in models])
    plt.ylabel("Count")
    title = f"Top-3 Entity Types per Model (50 Evaluation Papers)"
    plt.title(title)
    plt.legend()

    # 在每个柱上方标注：英文类型 + 计数
    for idx, (rank, h) in enumerate(zip([1, 2, 3], heights)):
        for j, (xi, val) in enumerate(zip(x + (idx - 1) * width, h)):
            m = models[j]
            t_cn = type_labels_per_model[m][rank - 1]
            t_en = TYPE_EN_MAP.get(t_cn, t_cn)
            label = f"{t_en} ({val})" if val else ""
            if not label:
                continue
            
            # 标注位置微调
            plt.annotate(label, xy=(xi, val), xytext=(0, 8), textcoords='offset points',
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
    # 设置文件路径 - 使用50篇评估论文的数据
    eval_dir = Path(__file__).resolve().parent
    counts_csv = eval_dir / "evaluation_papers_entity_type_counts.csv"
    outdir = eval_dir

    if not counts_csv.exists():
        print(f"错误：找不到数据文件 {counts_csv}")
        return

    _, rows = read_type_counts_csv(counts_csv)
    models = ["gemini", "deepseek", "kimi"]
    top3 = compute_top3_by_model(rows, models)
    n_docs = 50  # 固定为50篇评估论文

    out_csv = outdir / "evaluation_papers_top3_entity_types.csv"
    out_md = outdir / "evaluation_papers_top3_entity_types.md"
    out_img = outdir / "evaluation_papers_top3_entity_types.png"

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