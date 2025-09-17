import os
import re
import glob
import json
import argparse
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
try:
    import seaborn as sns  # optional
    SEABORN_AVAILABLE = True
except Exception:
    SEABORN_AVAILABLE = False

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except Exception:
    PLOTLY_AVAILABLE = False


def get_base_dir():
    try:
        script_path = os.path.abspath(__file__)
        code_dir = os.path.dirname(script_path)
        base_dir = os.path.dirname(code_dir)
    except NameError:
        base_dir = os.getcwd()
    return base_dir


# ------------------------
# Label translation & utils
# ------------------------
# 常见类型与关系的中英映射（可按需扩展/覆盖）
TYPE_MAP = {
    '研究方法': 'Method',
    '研究问题': 'Problem',
    '系统/部件': 'System/Component',
    '模型': 'Model',
    '研究结果': 'Finding',
    '性能指标': 'Performance Metric',
    '应用场景': 'Application',
    '数据集': 'Dataset',
    '特征/健康指标': 'Sensor/Parameter',
    '组织': 'Organization',
    '活动': 'Activity',
    '管理方法': 'Management Method',
    '方法': 'Method',
    '技术': 'Technology',
    '算法': 'Algorithm',
    '框架': 'Framework',
    '问题': 'Problem',
    '参数': 'Parameter',
    '设备': 'Equipment',
    '装置': 'Device',
    '系统': 'System',
    '理论': 'Theory',
    '流程': 'Process',
    '评估方法': 'Evaluation Method',
    '应用领域': 'Application Domain',
    '领域': 'Domain',
    '数据': 'Data',
    '任务': 'Task',
    '指标': 'Metric',
    '故障': 'Fault',
    '风险': 'Risk',
    '功能': 'Function',
    '接口': 'Interface',
    '信息': 'Information',
    '组件': 'Component',
    '部件': 'Component',
    '属性': 'Attribute',
    '性能': 'Performance',
    '特征': 'Feature',
    '关键技术': 'Key Technology',
    '系统参数': 'System Parameter',
    'problem': 'Problem',
    'method': 'Method',
    'model': 'Model',
    'tool': 'Tool'
}

REL_MAP_DEFAULT = {
    '属于': 'BelongsTo',
    '作用于': 'Affects',
    '提高': 'Improves',
    '降低': 'Decreases',
    '减少': 'Reduces',
    '增强': 'Enhances',
    '影响': 'Influences',
    '预测': 'Predicts',
    '导致': 'Causes',
    '包含': 'Includes',
    '依赖': 'DependsOn',
    '用于': 'UsedFor',
    '等于': 'Equals',
    '使用': 'Uses',
    '利用': 'Utilizes',
    '应用于': 'AppliedTo',
    '应用': 'AppliesTo',
    '基于': 'BasedOn',
    '支持': 'Supports',
    '验证': 'Validates',
    '分析': 'Analyzes',
    '优化': 'Optimizes',
    '建立': 'Builds',
    '提出': 'Proposes',
    '实现': 'Implements',
    '解决': 'Solves',
    '提升': 'Improves',
    '评估': 'Evaluates',
    '研究': 'Studies',
    '实验': 'ExperimentsOn',
    '满足': 'Satisfies',
    '来自': 'ComesFrom',
    '获取': 'Obtains',
    '提供': 'Provides',
    '改进': 'Improves'
}


def load_custom_rel_map(base_dir: str):
    """如存在 `dosc/relation_map.json` 则加载覆盖默认映射。"""
    path = os.path.join(base_dir, 'dosc', 'relation_map.json')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {**REL_MAP_DEFAULT, **data}
        except Exception:
            pass
    return REL_MAP_DEFAULT


def split_semantic_pattern(pat: str):
    parts = [p.strip() for p in re.split(r"→|->|➡|⇒", str(pat))]
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    return None, None, None


def translate_semantic_pattern_en(pat: str, rel_map: dict):
    s, r, o = split_semantic_pattern(pat)
    if s is None:
        return pat
    s_en = TYPE_MAP.get(s, s)
    r_en = rel_map.get(r, r)
    o_en = TYPE_MAP.get(o, o)
    # 强制ASCII，避免残留中文
    s_en = ascii_only(s_en) or 'Type'
    r_en = ascii_only(r_en) or 'Relation'
    o_en = ascii_only(o_en) or 'Type'
    return f"{s_en} -> {r_en} -> {o_en}"


# 基于子串的类型/关系英文化兜底（简单启发式）
TYPE_SUBSTR_RULES = [
    ('方法', 'Method'), ('技术', 'Technology'), ('算法', 'Algorithm'), ('框架', 'Framework'), ('系统', 'System'),
    ('模型', 'Model'), ('指标', 'Metric'), ('问题', 'Problem'), ('参数', 'Parameter'), ('特征', 'Feature'),
    ('流程', 'Process'), ('理论', 'Theory'), ('设备', 'Equipment'), ('装置', 'Device'), ('组件', 'Component'),
    ('部件', 'Component'), ('数据', 'Data'), ('任务', 'Task'), ('领域', 'Domain')
]

REL_SUBSTR_RULES = [
    ('应用于', 'AppliedTo'), ('用于', 'UsedFor'), ('使用', 'Uses'), ('利用', 'Utilizes'), ('提高', 'Improves'), ('提升', 'Improves'),
    ('降低', 'Decreases'), ('减少', 'Reduces'), ('影响', 'Influences'), ('解决', 'Solves'), ('预测', 'Predicts'), ('分析', 'Analyzes'),
    ('优化', 'Optimizes'), ('建立', 'Builds'), ('提出', 'Proposes'), ('实现', 'Implements'), ('验证', 'Validates'), ('支持', 'Supports'),
    ('包含', 'Includes'), ('基于', 'BasedOn'), ('评估', 'Evaluates'), ('提供', 'Provides'), ('获取', 'Obtains'), ('改进', 'Improves')
]


def translate_type_en(text: str) -> str:
    if not isinstance(text, str):
        return 'Type'
    if text in TYPE_MAP:
        return TYPE_MAP[text]
    for zh, en in TYPE_SUBSTR_RULES:
        if zh in text:
            return en
    return text


def translate_relation_en(text: str, rel_map: dict) -> str:
    if not isinstance(text, str):
        return 'Relation'
    if text in rel_map:
        return rel_map[text]
    for zh, en in REL_SUBSTR_RULES:
        if zh in text:
            return en
    return text


def extract_deprel_chain_from_display(display: str) -> str:
    """将 "词(dep) — 词(dep) — ..." 转换为 "dep1->dep2->..."（ASCII），便于英文图例且避免乱码。"""
    if not isinstance(display, str) or '(' not in display:
        return display
    deps = re.findall(r"\(([^()]+)\)", display)
    if not deps:
        return display
    return '->'.join([d.strip().lower() for d in deps if d.strip()])


def find_latest_report(report_dir: str) -> str:
    pattern = os.path.join(report_dir, 'semantic_syntactic_patterns_report_*.csv')
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError(f"No CSV reports found by pattern: {pattern}")
    # 按文件名中的时间戳或修改时间排序
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return files[0]


def setup_matplotlib_style():
    # 统一英文字体和风格，适合SCI投稿
    plt.rcParams.update({
        'font.family': ['Times New Roman', 'DejaVu Sans', 'Arial'],
        'font.size': 12,
        'axes.titlesize': 14,
        'axes.labelsize': 13,
        'xtick.labelsize': 11,
        'ytick.labelsize': 11,
        'legend.fontsize': 11,
        'figure.dpi': 300,
        'savefig.dpi': 600,
        'axes.spines.top': False,
        'axes.spines.right': False,
    })
    if SEABORN_AVAILABLE:
        sns.set_style('whitegrid')


def okabe_ito_colors(n: int):
    base = ['#0072B2', '#E69F00', '#009E73', '#CC79A7', '#D55E00', '#56B4E9', '#F0E442', '#999999']
    # 循环使用，保证色盲友好
    return [base[i % len(base)] for i in range(n)]


def ascii_only(text: str) -> str:
    if not isinstance(text, str):
        return str(text)
    try:
        out = text.encode('ascii', errors='ignore').decode('ascii')
        # 若去除非ASCII后为空，返回空字符串，由调用方或上层逻辑决定占位
        return out if out.strip() else ''
    except Exception:
        return ''


def sanitize_label_list(labels, prefix: str, out_dir: str, mapping_filename: str):
    """将标签列表ASCII化；如发生变化，保存 old->new 映射到 figures 下，便于追溯。"""
    sanitized = []
    changed = False
    mapping = []
    for i, lb in enumerate(labels):
        lb_str = str(lb)
        ascii_lb = ascii_only(lb_str)
        # 如果为空字符串，使用占位
        if not ascii_lb.strip():
            changed = True
            ascii_lb = f'{prefix} #{i+1}'
            mapping.append({'original': lb_str, 'ascii': ascii_lb})
        elif ascii_lb != lb_str:
            changed = True
            mapping.append({'original': lb_str, 'ascii': ascii_lb})
        sanitized.append(ascii_lb)

    if changed:
        try:
            os.makedirs(out_dir, exist_ok=True)
            pd.DataFrame(mapping).to_csv(os.path.join(out_dir, mapping_filename), index=False, encoding='utf_8_sig')
        except Exception:
            pass
    return sanitized


def parse_syntactic_realizations(text: str):
    """从“句法实现路径 (Syntactic Realizations)”字段里解析出 (display_path, count) 列表。
    文本示例：
      - 句法路径: Word1(dep1) — Word2(dep2) (频次: 3, 样例: [A] → [B])
    """
    if not isinstance(text, str) or not text.strip():
        return []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out = []
    for ln in lines:
        # 提取显示路径
        m_path = re.search(r"句法路径:\s*(.+?)\s*\(频次:", ln)
        m_cnt = re.search(r"频次:\s*(\d+)", ln)
        if m_path and m_cnt:
            display = m_path.group(1).strip()
            count = int(m_cnt.group(1))
            out.append((display, count))
    return out


def ensure_out_dir(path: str):
    os.makedirs(path, exist_ok=True)


def fig_top_semantic_patterns(df: pd.DataFrame, out_dir: str, topN: int = 15):
    col_pat = '语义模式 (Semantic Pattern)'
    col_freq = '总频次 (Total Freq)'
    rel_map = load_custom_rel_map(get_base_dir())

    use = df[[col_pat, col_freq]].copy()
    # 翻译为英文，避免中文乱码
    use['Semantic Pattern (EN)'] = use[col_pat].apply(lambda x: translate_semantic_pattern_en(x, rel_map))
    use = use.sort_values(col_freq, ascending=False).head(topN)
    # 再次ASCII化，彻底去除潜在非ASCII字符
    sanitized_labels = sanitize_label_list(use['Semantic Pattern (EN)'].tolist(), prefix='Pattern', out_dir=out_dir, mapping_filename='fig1_label_mapping.csv')
    use['Semantic Pattern (EN)'] = sanitized_labels

    setup_matplotlib_style()
    # 水平柱状图，更利于长标签展示
    fig, ax = plt.subplots(figsize=(8, max(4, 0.35 * len(use) + 1)))
    if SEABORN_AVAILABLE:
        sns.barplot(data=use, y='Semantic Pattern (EN)', x=col_freq, ax=ax, color='#3b82f6')
    else:
        y_labels = use['Semantic Pattern (EN)'].tolist()
        x_vals = use[col_freq].tolist()
        y_pos = range(len(y_labels))
        ax.barh(list(y_pos), x_vals, color='#3b82f6')
        ax.set_yticks(list(y_pos))
        ax.set_yticklabels(y_labels)
    ax.set_title('Top Semantic Patterns by Frequency')
    ax.set_xlabel('Total Frequency')
    ax.set_ylabel('Semantic Pattern')
    # 数值标注
    for i, v in enumerate(use[col_freq].values):
        ax.text(v, i, f' {v}', va='center', ha='left', fontsize=10)
    fig.tight_layout()

    ensure_out_dir(out_dir)
    fig.savefig(os.path.join(out_dir, 'fig1_top_semantic_patterns.png'))
    fig.savefig(os.path.join(out_dir, 'fig1_top_semantic_patterns.pdf'))
    plt.close(fig)


def fig_breakdown_syntactic_paths(df: pd.DataFrame, out_dir: str, topM: int = 5, topK_per_pattern: int = 4):
    col_pat = '语义模式 (Semantic Pattern)'
    col_freq = '总频次 (Total Freq)'
    col_syn = '句法实现路径 (Syntactic Realizations)'
    rel_map = load_custom_rel_map(get_base_dir())

    # 选取TopM语义模式
    topM_df = df.sort_values(col_freq, ascending=False).head(topM)

    # 构建堆叠数据：对每个语义模式，取TopK句法路径，其余归入"Other"
    records = []
    for _, row in topM_df.iterrows():
        pat = translate_semantic_pattern_en(row[col_pat], rel_map)
        parsed = parse_syntactic_realizations(row[col_syn])
        if not parsed:
            continue
        # 将显示路径转换为依存关系链（ASCII），避免中文乱码
        parsed_ascii = [(extract_deprel_chain_from_display(p), c) for p, c in parsed]
        parsed_sorted = sorted(parsed_ascii, key=lambda x: x[1], reverse=True)
        topk = parsed_sorted[:topK_per_pattern]
        other_sum = sum(c for _, c in parsed_sorted[topK_per_pattern:])

        for disp, cnt in topk:
            records.append({'Semantic Pattern': pat, 'Syntactic Path': disp, 'Count': cnt})
        if other_sum > 0:
            records.append({'Semantic Pattern': pat, 'Syntactic Path': 'Other', 'Count': other_sum})

    if not records:
        return

    plot_df = pd.DataFrame(records)
    plot_df['Syntactic Path Short'] = plot_df['Syntactic Path'].apply(lambda s: s if len(s) <= 40 else s[:37] + '...')

    setup_matplotlib_style()
    # 构造堆叠柱状图
    pivot = plot_df.pivot_table(index='Semantic Pattern', columns='Syntactic Path Short', values='Count', aggfunc='sum', fill_value=0)
    # 使用英文模式顺序进行重排，避免中文与英文不匹配
    order_en = [translate_semantic_pattern_en(p, rel_map) for p in topM_df[col_pat].tolist()]
    order_en = [p for p in order_en if p in pivot.index]
    if order_en:
        pivot = pivot.reindex(order_en)

    # 对行索引ASCII化并保存映射
    new_index = sanitize_label_list(list(pivot.index), prefix='Pattern', out_dir=out_dir, mapping_filename='fig2_label_mapping.csv')
    pivot.index = new_index

    fig, ax = plt.subplots(figsize=(10, max(4, 0.6 * len(pivot) + 1)))
    bottom = None
    # 颜色：优先 seaborn 调色板，否则用 matplotlib 的 tab20
    if SEABORN_AVAILABLE:
        colors = okabe_ito_colors(len(pivot.columns))
    else:
        colors = okabe_ito_colors(len(pivot.columns))
    for i, col in enumerate(pivot.columns):
        ax.barh(pivot.index, pivot[col], left=bottom, label=col, color=colors[i])
        bottom = (pivot[col] if bottom is None else bottom + pivot[col])

    ax.set_title('Syntactic Path Breakdown for Top Semantic Patterns')
    ax.set_xlabel('Frequency')
    ax.set_ylabel('Semantic Pattern')
    ax.legend(title='Syntactic Path', bbox_to_anchor=(1.02, 1), loc='upper left', frameon=True)
    fig.tight_layout()

    ensure_out_dir(out_dir)
    fig.savefig(os.path.join(out_dir, 'fig2_syntactic_breakdown.png'))
    fig.savefig(os.path.join(out_dir, 'fig2_syntactic_breakdown.pdf'))
    plt.close(fig)


def fig_sankey_semantic_chain(df: pd.DataFrame, out_dir: str, max_nodes_per_layer: int = 30):
    """基于 "SubjectType → Relation → ObjectType" 生成三段式桑基图。
    注意：若关系（Relation）为中文，你可在下方relation_map中做人工英文映射。
    """
    if not PLOTLY_AVAILABLE:
        print('[WARN] Plotly not available. Skip Sankey figure. Install plotly and kaleido to enable.')
        return

    col_pat = '语义模式 (Semantic Pattern)'
    col_freq = '总频次 (Total Freq)'

    # 使用可自定义的关系英文映射（如存在 dosc/relation_map.json 会覆盖默认）
    relation_map = load_custom_rel_map(get_base_dir())

    def split_semantic_pattern_local(pat: str):
        parts = [p.strip() for p in re.split(r"→|->|➡|⇒", str(pat))]
        if len(parts) == 3:
            subj, rel, obj = parts
            # 类型/关系英文化，并强制ASCII
            subj = ascii_only(TYPE_MAP.get(subj, subj)) or 'Type'
            rel = ascii_only(relation_map.get(rel, rel)) or 'Relation'
            obj = ascii_only(TYPE_MAP.get(obj, obj)) or 'Type'
            return subj, rel, obj
        return None, None, None

    rows = []
    for _, row in df.iterrows():
        subj, rel, obj = split_semantic_pattern_local(row[col_pat])
        if subj and rel and obj:
            rows.append({'SubjectType': subj, 'Relation': rel, 'ObjectType': obj, 'Count': int(row[col_freq])})
    if not rows:
        return

    sankey_df = pd.DataFrame(rows)

    # 控制节点数，避免过密
    def top_values(s: pd.Series, k: int):
        counts = s.value_counts()
        return set(counts.index[:k])

    top_subj = top_values(sankey_df['SubjectType'], max_nodes_per_layer)
    top_rel = top_values(sankey_df['Relation'], max_nodes_per_layer)
    top_obj = top_values(sankey_df['ObjectType'], max_nodes_per_layer)

    sankey_df = sankey_df[ (
        sankey_df['SubjectType'].isin(top_subj) &
        sankey_df['Relation'].isin(top_rel) &
        sankey_df['ObjectType'].isin(top_obj)
    ) ]

    # 构建节点索引
    subjects = sorted(sankey_df['SubjectType'].unique())
    relations = sorted(sankey_df['Relation'].unique())
    objects = sorted(sankey_df['ObjectType'].unique())

    raw_nodes = ([f'S: {s}' for s in subjects] +
                 [f'R: {r}' for r in relations] +
                 [f'O: {o}' for o in objects])
    # 节点ASCII化并建立原始->ASCII映射
    sanitized_nodes = sanitize_label_list(raw_nodes, prefix='Node', out_dir=out_dir, mapping_filename='fig3_label_mapping.csv')
    node_label_map = {raw: san for raw, san in zip(raw_nodes, sanitized_nodes)}
    node_index = {name: i for i, name in enumerate(sanitized_nodes)}

    links = {
        'source': [], 'target': [], 'value': [], 'label': []
    }
    # Subject -> Relation
    agg_sr = sankey_df.groupby(['SubjectType', 'Relation'], as_index=False)['Count'].sum()
    for _, r in agg_sr.iterrows():
        s_key = node_label_map[f'S: {r.SubjectType}']
        r_key = node_label_map[f'R: {r.Relation}']
        links['source'].append(node_index[s_key])
        links['target'].append(node_index[r_key])
        links['value'].append(int(r.Count))
        links['label'].append(f"{r.SubjectType} -> {r.Relation}: {int(r.Count)}")
    # Relation -> Object
    agg_ro = sankey_df.groupby(['Relation', 'ObjectType'], as_index=False)['Count'].sum()
    for _, r in agg_ro.iterrows():
        r_key = node_label_map[f'R: {r.Relation}']
        o_key = node_label_map[f'O: {r.ObjectType}']
        links['source'].append(node_index[r_key])
        links['target'].append(node_index[o_key])
        links['value'].append(int(r.Count))
        links['label'].append(f"{r.Relation} -> {r.ObjectType}: {int(r.Count)}")

    fig = go.Figure(data=[go.Sankey(
        arrangement='snap',
        node=dict(
            pad=10,
            thickness=18,
            line=dict(color='black', width=0.5),
            label=sanitized_nodes
        ),
        link=dict(
            source=links['source'],
            target=links['target'],
            value=links['value'],
            label=links['label']
        )
    )])

    fig.update_layout(
        title_text='Semantic Chain: Subject Type -> Relation -> Object Type',
        title_x=0.5,
        font=dict(family='Times New Roman, Arial, DejaVu Sans', size=12)
    )

    ensure_out_dir(out_dir)
    # 保存静态图像需要 kaleido
    try:
        fig.write_image(os.path.join(out_dir, 'fig3_semantic_sankey.png'), scale=3)
        fig.write_image(os.path.join(out_dir, 'fig3_semantic_sankey.pdf'))
    except Exception as e:
        # 退化为HTML交互图
        html_path = os.path.join(out_dir, 'fig3_semantic_sankey.html')
        fig.write_html(html_path)
        print(f"[WARN] Failed to export static image via kaleido: {e}\nSaved interactive HTML instead: {html_path}")


def main():
    parser = argparse.ArgumentParser(description='Make publication-quality figures from semantic-syntactic CSV report.')
    parser.add_argument('--report', type=str, default=None, help='Path to CSV report. If omitted, use the latest in the output folder.')
    parser.add_argument('--topN', type=int, default=15, help='Top N semantic patterns for Fig.1')
    parser.add_argument('--topM', type=int, default=5, help='Top M semantic patterns for Fig.2')
    parser.add_argument('--topK', type=int, default=4, help='Top K syntactic paths per pattern for Fig.2')
    parser.add_argument('--maxNodes', type=int, default=30, help='Max nodes per layer for Sankey (Fig.3)')
    args = parser.parse_args()

    base_dir = get_base_dir()
    out_report_dir = os.path.join(base_dir, '统计提取结果')
    figs_dir = os.path.join(out_report_dir, 'figures')

    report_path = args.report or find_latest_report(out_report_dir)
    print(f"[INFO] Using report: {report_path}")
    df = pd.read_csv(report_path)

    # 生成图
    fig_top_semantic_patterns(df, figs_dir, topN=args.topN)
    fig_breakdown_syntactic_paths(df, figs_dir, topM=args.topM, topK_per_pattern=args.topK)
    fig_sankey_semantic_chain(df, figs_dir, max_nodes_per_layer=args.maxNodes)

    print(f"[DONE] Figures saved to: {figs_dir}")


if __name__ == '__main__':
    main()
