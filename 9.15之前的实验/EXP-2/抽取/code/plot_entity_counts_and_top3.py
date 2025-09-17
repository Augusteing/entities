import json
import os
from collections import Counter
import matplotlib.pyplot as plt
from matplotlib import font_manager


STAT_DIR = os.path.join('e:\\知识图谱构建\\9.15之前的实验\\EXP-3', '抽取', '数据结果', '统计')
STAT_JSON = os.path.join(STAT_DIR, '实体类型统计_按模型汇总.json')

# 指定颜色（Top1 紫、Top2 蓝、Top3 绿）
RANK_COLORS = {
    1: '#925EB0',
    2: '#7E99F4',
    3: '#7AB656',
}

# 显示顺序与展示名（与示例图一致）
MODELS = ['gemini', 'deepseek', 'kimi']
DISPLAY_NAME = {
    'gemini': 'Gemini',
    'deepseek': 'Deepseek',
    'kimi': 'Kimi',
}

# 中文类型到英文的映射（覆盖常见类型；未知类型回退为 Other-*）
CH2EN = {
    '系统': 'System',
    '方法': 'Method',
    '平台': 'Platform',
    '标准': 'Standard',
    '架构': 'Architecture',
    '功能': 'Function',
    '模块': 'Module',
    '语言': 'Language',
    '软件': 'Software',
    '测试': 'Test',
    '参数': 'Parameter',
    '问题': 'Issue',
    '流程': 'Process',
    '思想': 'Concept',
    '思路': 'Approach',
    '模型': 'Model',
    '概念': 'Concept',
    '组织': 'Organization',
    '方案': 'Plan',
    '机制': 'Mechanism',
    '硬件': 'Hardware',
    '算法': 'Algorithm',
    '传感器': 'Sensor',
    '接口': 'Interface',
    '网络': 'Network',
    '数据': 'Data',
    '系统架构': 'System Architecture',
    '部件': 'Component',
    '设备': 'Device',
    '实验': 'Experiment',
    '材料': 'Material',
    '结构': 'Structure',
    '指标': 'Metric',
    '案例': 'Case',
    '规则': 'Rule',
    '流程图': 'Flowchart',
    '语言模型': 'Language Model',
    '框架': 'Framework',
    '模型架构': 'Model Architecture',
}

def to_english(label: str, fallback_index: int | None = None) -> str:
    if not label:
        return 'Other' if fallback_index is None else f'Other-{fallback_index}'
    if label in CH2EN:
        return CH2EN[label]
    # 去除非ASCII字符，若结果为空，则回退Other
    ascii_label = ''.join(ch for ch in label if ord(ch) < 128).strip()
    if ascii_label:
        return ascii_label
    return 'Other' if fallback_index is None else f'Other-{fallback_index}'


def set_fonts():
    # 将全局字体设为 Times New Roman，若系统未安装则回退到默认
    plt.rcParams['font.family'] = 'Times New Roman'
    plt.rcParams['axes.unicode_minus'] = False


def load_stats(path: str):
    with open(path, 'r', encoding='utf-8') as fp:
        return json.load(fp)


def plot_totals(results: dict, out_path: str):
    # 计算每个模型的实体总数
    totals = []
    for m in MODELS:
        tc = results.get(m, {}).get('type_counts', {})
        totals.append(sum(tc.values()))

    fig, ax = plt.subplots(figsize=(12, 6), dpi=300)
    colors = ['#925EB0', '#7E99F4', '#7AB656']
    xlabels = [DISPLAY_NAME[m] for m in MODELS]
    bars = ax.bar(xlabels, totals, color=colors, edgecolor='#333333', linewidth=0.6)

    # 标题与轴标签（英文；示例风格）
    # 取样本数（通常为50）
    n_files = results.get(MODELS[0], {}).get('total_files_counted', 50)
    ax.set_title(f'Total Extracted Entities ({n_files} Evaluation Papers)', fontsize=18)
    ax.set_xlabel('')
    ax.set_ylabel('Total Entities', fontsize=14)
    ax.set_ylim(0, max(totals) * 1.15)
    ax.grid(False)

    # 顶部数值标注
    for b, v in zip(bars, totals):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + max(totals) * 0.015, f'{v}',
                ha='center', va='bottom', fontsize=12)

    fig.tight_layout()
    fig.savefig(out_path, bbox_inches='tight')
    plt.close(fig)


def plot_top3(results: dict, out_path: str):
    # 找出每个模型 type_counts 的 Top-3
    top_data = {}
    all_top_types = set()
    for m in MODELS:
        type_counts = results.get(m, {}).get('type_counts', {})
        c = Counter(type_counts)
        top3 = c.most_common(3)
        top_data[m] = top3
        for t, _ in top3:
            all_top_types.add(t)

    # 画分组条形图：每个模型3个条，颜色对应Top1/Top2/Top3
    fig, ax = plt.subplots(figsize=(16, 6), dpi=300)
    x = range(len(MODELS))
    width = 0.22

    # 计算范围用于留白
    max_val = 1
    for m in MODELS:
        for _, v in top_data[m]:
            max_val = max(max_val, v)

    for rank in [1, 2, 3]:
        xs = [i + (rank - 2) * width for i in x]  # 居中排列
        vals = []
        labels = []
        for m in MODELS:
            pair = top_data[m][rank - 1] if len(top_data[m]) >= rank else ('N/A', 0)
            labels.append(pair[0])
            vals.append(pair[1])
        bars = ax.bar(xs, vals, width=width, color=RANK_COLORS[rank], label=f'Top{rank}',
                      edgecolor='#333333', linewidth=0.6)
        # 在柱子顶部标注“类型 (数量)”
        for i, b in enumerate(bars):
            en_label = to_english(labels[i], rank)
            ax.text(b.get_x() + b.get_width() / 2,
                    b.get_height() + max_val * 0.02,
                    f"{en_label} ({vals[i]})",
                    ha='center', va='bottom', fontsize=11)

    ax.set_xticks(list(x))
    ax.set_xticklabels([DISPLAY_NAME[m] for m in MODELS], fontsize=12)
    n_files = results.get(MODELS[0], {}).get('total_files_counted', 50)
    ax.set_title(f'Top-3 Entity Types per Model ({n_files} Evaluation Papers)', fontsize=18)
    ax.set_xlabel('')
    ax.set_ylabel('Count', fontsize=14)
    ax.legend(loc='upper right', frameon=True, fontsize=11)
    ax.set_ylim(0, max_val * 1.25)
    ax.grid(False)

    fig.tight_layout()
    fig.savefig(out_path, bbox_inches='tight')
    plt.close(fig)


def main():
    set_fonts()
    if not os.path.exists(STAT_JSON):
        raise SystemExit(f'Missing summary json: {STAT_JSON}')
    results = load_stats(STAT_JSON)

    os.makedirs(STAT_DIR, exist_ok=True)
    out1 = os.path.join(STAT_DIR, 'entity_totals_by_model.png')
    out2 = os.path.join(STAT_DIR, 'top3_entity_types_by_model.png')

    plot_totals(results, out1)
    plot_top3(results, out2)
    print('Saved:', out1)
    print('Saved:', out2)


if __name__ == '__main__':
    main()
