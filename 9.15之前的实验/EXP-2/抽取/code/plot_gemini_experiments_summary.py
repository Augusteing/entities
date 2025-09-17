import os
import matplotlib.pyplot as plt


OUT_DIR = os.path.join('e:\\知识图谱构建\\9.15之前的实验\\EXP-3', '抽取', '数据结果', '统计')

# 颜色：实验1紫、实验2蓝、实验3绿（与之前Top1/2/3一致）
COLORS = ['#925EB0', '#7E99F4', '#7AB656']

# 使用者给定数据（本脚本可直接运行）
METRICS = [
    ('Entity Total', [1373, 2685, 2504]),
    ('Entity Type Count', [85, 265, 349]),
    ('Relation Total', [416, 1873, 1402]),
    ('Relation Type Count', [91, 654, 636]),
]
EXPS = ['Exp1', 'Exp2', 'Exp3']


def setup_style():
    plt.rcParams['font.family'] = 'Times New Roman'
    plt.rcParams['axes.unicode_minus'] = False


def plot_summary(out_path: str):
    setup_style()
    n_groups = len(METRICS)
    x = range(n_groups)
    width = 0.22

    fig, ax = plt.subplots(figsize=(14, 6), dpi=300)

    # 组内位移
    offsets = [-(width), 0.0, width]

    # 计算最大值用于顶部留白
    max_val = max(max(vals) for _, vals in METRICS)

    bars_by_exp = []
    for exp_idx, exp_name in enumerate(EXPS):
        vals = [vals[exp_idx] for _, vals in METRICS]
        xs = [i + offsets[exp_idx] for i in x]
        bars = ax.bar(xs, vals, width=width, color=COLORS[exp_idx],
                      edgecolor='#333333', linewidth=0.6, label=exp_name)
        bars_by_exp.append(bars)
        # 顶部数值
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + max_val * 0.02,
                    f'{v}', ha='center', va='bottom', fontsize=11)

    ax.set_xticks(list(x))
    ax.set_xticklabels([name for name, _ in METRICS], fontsize=12)
    ax.set_ylabel('Count', fontsize=14)
    ax.set_title('Gemini Results Across Experiments', fontsize=18)
    ax.legend(loc='upper right', frameon=True, fontsize=11)
    ax.set_ylim(0, max_val * 1.25)
    ax.grid(False)

    fig.tight_layout()
    fig.savefig(out_path, bbox_inches='tight')
    plt.close(fig)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, 'gemini_experiments_summary.png')
    plot_summary(out_path)
    print('Saved:', out_path)


if __name__ == '__main__':
    main()
