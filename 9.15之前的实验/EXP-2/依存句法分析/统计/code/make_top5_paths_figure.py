"""
Generate a clean semantic Sankey diagram (Subject Type -> Relation -> Object Type).
- Reads the latest semantic_syntactic_patterns_counts_*.csv under '统计提取结果'
- Parses semantic_pattern into three parts and aggregates counts
- Uses Times New Roman and the specified palette; fixed left-center-right layout
- Outputs PNG/PDF/SVG (fallback HTML): fig_semantic_sankey_clean.*
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple, Dict, List

import numpy as np
import pandas as pd
import plotly.graph_objects as go


# ---------------- Configs ----------------
COLORS: Dict[str, str] = {
    'gray':   '#A5AEB7',
    'purple': '#925EB0',
    'blue':   '#7E99F4',
    'red':    '#CC7C71',
    'green':  '#7AB656',
}

RELATION_PALETTE = [COLORS['purple'], COLORS['blue'], COLORS['red'], COLORS['green'], COLORS['gray']]


def find_base_dir() -> Path:
    try:
        return Path(__file__).resolve().parent.parent
    except NameError:
        return Path.cwd()


def get_latest_counts_csv(result_dir: Path) -> Path:
    files = list(result_dir.glob('semantic_syntactic_patterns_counts_*.csv'))
    if not files:
        raise FileNotFoundError("No counts CSV found under 统计提取结果")
    return max(files, key=os.path.getmtime)


# -------- Label normalization (EN mapping) --------
TYPE_MAP: Dict[str, str] = {
    '研究方法': 'Method', '研究问题': 'Problem', '系统/部件': 'System/Component', '模型': 'Model',
    '研究结果': 'Finding', '性能指标': 'Performance Metric', '应用场景': 'Application', '数据集': 'Dataset',
    '特征/健康指标': 'Sensor/Parameter', 'problem': 'Problem', 'method': 'Method', 'model': 'Model', 'tool': 'Tool'
}

REL_MAP: Dict[str, str] = {
    '解决': 'solves', '导致': 'causes', '属于': 'belongs-to', '影响': 'influences', '包含': 'includes',
    '应用于': 'applies-to', '基于': 'based-on', '提出': 'proposes', '用于': 'used-for', '改善': 'improves',
    '预测': 'predicts', '诊断': 'diagnoses', '建模': 'models', '优化': 'optimizes', '评估': 'evaluates', '验证': 'validates'
}


def ascii_only(s: str) -> str:
    if not isinstance(s, str):
        return ''
    return ' '.join(''.join(ch if ord(ch) < 128 else ' ' for ch in s).split())


def norm_type(token: str) -> str:
    if not isinstance(token, str) or not token.strip():
        return 'Entity'
    t = token.trim() if hasattr(token, 'trim') else token.strip()
    if t in TYPE_MAP:
        return TYPE_MAP[t]
    tl = t.lower()
    if tl in TYPE_MAP:
        return TYPE_MAP[tl]
    # heuristics
    if any(k in t for k in ['方法', '算法']) or any(k in tl for k in ['method', 'approach', 'algorithm', 'technique']):
        return 'Method'
    if any(k in t for k in ['问题', '挑战']) or any(k in tl for k in ['problem', 'task', 'challenge']):
        return 'Problem'
    if any(k in t for k in ['系统', '部件', '装置']) or any(k in tl for k in ['system', 'component', 'device', 'module', 'platform']):
        return 'System/Component'
    if '模型' in t or 'model' in tl or 'framework' in tl:
        return 'Model'
    return ascii_only(t) or 'Entity'


def norm_rel(token: str) -> str:
    if not isinstance(token, str) or not token.strip():
        return 'relates-to'
    r = token.trim() if hasattr(token, 'trim') else token.strip()
    if r in REL_MAP:
        return REL_MAP[r]
    rl = r.lower()
    if rl in REL_MAP:
        return REL_MAP[rl]
    # heuristics
    if any(k in r for k in ['解决', '处理']) or any(k in rl for k in ['solve', 'address', 'tackle']):
        return 'solves'
    if any(k in r for k in ['用于']) or 'used for' in rl:
        return 'used-for'
    if any(k in r for k in ['包含']) or 'include' in rl:
        return 'includes'
    if any(k in r for k in ['应用于']) or 'applies to' in rl:
        return 'applies-to'
    if any(k in r for k in ['改善']) or 'improve' in rl:
        return 'improves'
    if '预测' in r or 'predict' in rl:
        return 'predicts'
    return ascii_only(r) or 'relates-to'


def parse_pattern(pattern: str) -> Tuple[str, str, str]:
    parts = [p.strip() for p in str(pattern).replace('→', '->').split('->')]
    if len(parts) != 3:
        return ('Entity', 'relates-to', 'Entity')
    s, r, o = parts
    return norm_type(s), norm_rel(r), norm_type(o)


def build_aggregated_sro(df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Tuple[str, str, str, int]] = []
    for _, row in df.iterrows():
        s, r, o = parse_pattern(row['semantic_pattern'])
        c = int(row['count']) if not pd.isna(row['count']) else 0
        rows.append((s, r, o, c))
    out = pd.DataFrame(rows, columns=['S', 'R', 'O', 'count'])
    return out.groupby(['S', 'R', 'O'], as_index=False)['count'].sum()


def sankey_positions(subj_nodes: List[str], rel_nodes: List[str], obj_nodes: List[str]) -> Tuple[List[float], List[float]]:
    def lane_y(n: int) -> List[float]:
        if n <= 1:
            return [0.5]
        return list(np.linspace(0.12, 0.88, n))

    xs = [0.02]*len(subj_nodes) + [0.50]*len(rel_nodes) + [0.98]*len(obj_nodes)
    ys = lane_y(len(subj_nodes)) + lane_y(len(rel_nodes)) + lane_y(len(obj_nodes))
    return xs, ys


def make_sankey(df_counts: pd.DataFrame, out_dir: Path, top_relations: int = 5, top_subjects: int = 8, top_objects: int = 8) -> None:
    # aggregate
    sro = build_aggregated_sro(df_counts)

    # top selections
    top_rel = sro.groupby('R', as_index=False)['count'].sum().sort_values('count', ascending=False)['R'].head(top_relations).tolist()
    top_subj = sro.groupby('S', as_index=False)['count'].sum().sort_values('count', ascending=False)['S'].head(top_subjects).tolist()
    top_obj = sro.groupby('O', as_index=False)['count'].sum().sort_values('count', ascending=False)['O'].head(top_objects).tolist()

    sro['S2'] = sro['S'].apply(lambda s: s if s in top_subj else 'Other')
    sro['R2'] = sro['R'].apply(lambda r: r if r in top_rel else 'Other')
    sro['O2'] = sro['O'].apply(lambda o: o if o in top_obj else 'Other')
    sro2 = sro.groupby(['S2','R2','O2'], as_index=False)['count'].sum()

    subj_nodes = sorted(sro2['S2'].unique().tolist(), key=lambda x: (x!='Other', x))
    rel_nodes = [r for r in top_rel] + ([] if 'Other' in top_rel else ['Other'])
    obj_nodes = sorted(sro2['O2'].unique().tolist(), key=lambda x: (x!='Other', x))

    labels = subj_nodes + rel_nodes + obj_nodes
    idx = {lab: i for i, lab in enumerate(labels)}
    x, y = sankey_positions(subj_nodes, rel_nodes, obj_nodes)

    # colors
    rel_color: Dict[str, str] = {}
    for i, r in enumerate(rel_nodes):
        rel_color[r] = RELATION_PALETTE[min(i, len(RELATION_PALETTE)-1)]
    node_colors = ['#E6E6E6']*len(subj_nodes) + [rel_color[r] for r in rel_nodes] + ['#E6E6E6']*len(obj_nodes)

    def rgba(hex_color: str, a: float=0.45) -> str:
        h = hex_color.lstrip('#')
        return f"rgba({int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)},{a})"

    # links
    sr = sro2.groupby(['S2','R2'], as_index=False)['count'].sum()
    ro = sro2.groupby(['R2','O2'], as_index=False)['count'].sum()
    source = [idx[s] for s in sr['S2']] + [idx[r] for r in ro['R2']]
    target = [idx[r] for r in sr['R2']] + [idx[o] for o in ro['O2']]
    value  = sr['count'].tolist() + ro['count'].tolist()
    color  = [rgba(rel_color[r]) for r in sr['R2']] + [rgba(rel_color[r]) for r in ro['R2']]

    fig = go.Figure(data=[go.Sankey(
        arrangement='fixed',
        node=dict(
            pad=18, thickness=16,
            label=[ascii_only(l) for l in labels],
            color=node_colors,
            line=dict(color='black', width=0.4),
            x=x, y=y,
        ),
        link=dict(source=source, target=target, value=value, color=color)
    )])

    fig.update_layout(
        title=dict(text='Semantic Flow: Subject Type → Relation → Object Type', x=0.5, font=dict(family='Times New Roman', size=18)),
        font=dict(family='Times New Roman', size=12),
        margin=dict(l=40, r=40, t=90, b=40),
        paper_bgcolor='white', width=1200, height=max(520, 28*len(labels))
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    base = out_dir / 'fig_semantic_sankey_clean'
    try:
        fig.write_image(str(base.with_suffix('.png')), scale=2)
        fig.write_image(str(base.with_suffix('.pdf')))
        fig.write_image(str(base.with_suffix('.svg')))
        print(f"[Saved] {base.with_suffix('.png')}")
        print(f"[Saved] {base.with_suffix('.pdf')}")
        print(f"[Saved] {base.with_suffix('.svg')}")
    except Exception:
        html_path = base.with_suffix('.html')
        fig.write_html(str(html_path))
        print(f"[Saved] {html_path} (install kaleido for PNG/PDF/SVG)")


def main() -> None:
    base = find_base_dir()
    out_dir = base / '统计提取结果'
    csv_path = get_latest_counts_csv(out_dir)
    print(f"[Info] Using counts file: {csv_path.name}")
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
    except UnicodeError:
        df = pd.read_csv(csv_path, encoding='utf-8')
    make_sankey(df, out_dir, top_relations=5, top_subjects=8, top_objects=8)


if __name__ == '__main__':
    main()

