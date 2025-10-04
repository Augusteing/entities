import json
from pathlib import Path
import argparse
import matplotlib.pyplot as plt
from typing import Optional, Tuple, Dict
import csv

# 颜色与字体
COLOR_ENTITY = '#925EB0'   # 实体正确率柱
COLOR_REL    = '#7AB656'   # 关系正确率柱
PREFERRED_FONTS = ['Microsoft YaHei', 'SimHei', 'STHeiti', 'Songti SC', 'Arial Unicode MS']

MODEL_NAME_MAP = {
    'deepseek': 'deepseek',
    'gemini': 'gemini',
    'kimi': 'kimi'
}

def set_chinese_font():
    from matplotlib import font_manager
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in PREFERRED_FONTS:
        if name in available:
            plt.rcParams['font.sans-serif'] = [name]
            plt.rcParams['axes.unicode_minus'] = False
            return name
    return None

def _is_correct(meta) -> Optional[bool]:
    """复制并简化自已有脚本逻辑:
    返回 True / False; 如果 meta 缺失(None) 返回 None 以便统计覆盖率。
    可识别: '正确' 'correct' 'true' 'yes' 以及其大小写。
    错误集: '错误' 'error' 'false' 'no'. 其他与无法识别 -> False (但若 meta 本身缺, 返回 None)。
    """
    if meta is None:
        return None
    if isinstance(meta, bool):
        return bool(meta)
    if isinstance(meta, str):
        val = meta.strip().lower()
        if val in {'正确', 'correct', 'true', 'yes'}:
            return True
        if val in {'错误', 'error', 'false', 'no'}:
            return False
    return False

def scan_file(path: Path) -> Tuple[Tuple[int,int,int], Tuple[int,int,int]]:
    """返回 ((实体总数, 有evaluation数, 正确数), (关系总数, 有evaluation数, 正确数))"""
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return (0,0,0),(0,0,0)
    if not isinstance(data, dict):
        return (0,0,0),(0,0,0)
    entities = data.get('entities') or []
    relations = data.get('relations') or []

    ent_total = len(entities); ent_with_eval = 0; ent_correct = 0
    for e in entities:
        flag = _is_correct(e.get('evaluation'))
        if flag is None:
            continue
        ent_with_eval += 1
        if flag:
            ent_correct += 1

    rel_total = len(relations); rel_with_eval = 0; rel_correct = 0
    for r in relations:
        flag = _is_correct(r.get('evaluation'))
        if flag is None:
            continue
        rel_with_eval += 1
        if flag:
            rel_correct += 1
    return (ent_total, ent_with_eval, ent_correct), (rel_total, rel_with_eval, rel_correct)

def aggregate(dir_path: Path) -> Dict[str, Optional[float]]:
    ent_total = ent_with_eval = ent_correct = 0
    rel_total = rel_with_eval = rel_correct = 0
    json_files = sorted(dir_path.glob('*.json'))
    for jf in json_files:
        (et, ewe, ec), (rt, rwe, rc) = scan_file(jf)
        ent_total += et; ent_with_eval += ewe; ent_correct += ec
        rel_total += rt; rel_with_eval += rwe; rel_correct += rc
    return {
        'entity_total': ent_total,
        'entity_with_eval': ent_with_eval,
        'entity_correct': ent_correct,
        'relation_total': rel_total,
        'relation_with_eval': rel_with_eval,
        'relation_correct': rel_correct,
        'entity_accuracy': (ent_correct / ent_with_eval) if ent_with_eval else None,
        'relation_accuracy': (rel_correct / rel_with_eval) if rel_with_eval else None,
        'entity_eval_coverage': (ent_with_eval / ent_total) if ent_total else None,
        'relation_eval_coverage': (rel_with_eval / rel_total) if rel_total else None,
        'files_scanned': len(json_files),
    }

def plot_accuracy(model_key: str, stats: dict, out_dir: Path, title_suffix: str = '') -> Path:
    set_chinese_font()
    acc_e = stats['entity_accuracy']
    acc_r = stats['relation_accuracy']
    values = []; labels = []; colors = []
    if acc_e is not None:
        labels.append('实体正确率'); values.append(acc_e * 100); colors.append(COLOR_ENTITY)
    if acc_r is not None:
        labels.append('关系正确率'); values.append(acc_r * 100); colors.append(COLOR_REL)
    if not values:
        print(f'[WARN] {model_key} 没有可绘制的正确率 (无 evaluation)')
        return out_dir / f'{model_key}_空_正确率.png'

    plt.figure(figsize=(5,4), dpi=150)
    bars = plt.bar(labels, values, color=colors, edgecolor='#333333')
    for bar, val in zip(bars, values):
        plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), f"{val:.2f}%", ha='center', va='bottom', fontsize=10)
    base_title = f"{MODEL_NAME_MAP.get(model_key, model_key)} 模型实体/关系正确率统计"
    if title_suffix:
        base_title += f'（{title_suffix}）'
    plt.title(base_title)
    plt.ylabel('正确率 (%)')
    plt.ylim(0,100)
    plt.tight_layout()
    out_path = out_dir / f'{model_key}_实体关系正确率.png'
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()
    return out_path

def write_single_csv(model_key: str, stats: dict, out_dir: Path):
    out_csv = out_dir / f'{model_key}_实体关系正确率统计.csv'
    # 中文表头
    header = [
        '模型','文件数',
        '实体总数','实体有评估数','实体正确数','实体正确率','实体评估覆盖率',
        '关系总数','关系有评估数','关系正确数','关系正确率','关系评估覆盖率'
    ]
    with out_csv.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f); w.writerow(header)
        w.writerow([
            model_key, stats['files_scanned'],
            stats['entity_total'], stats['entity_with_eval'], stats['entity_correct'], stats['entity_accuracy'], stats['entity_eval_coverage'],
            stats['relation_total'], stats['relation_with_eval'], stats['relation_correct'], stats['relation_accuracy'], stats['relation_eval_coverage']
        ])
    return out_csv

def write_summary_csv(all_stats: Dict[str, dict], out_csv: Path):
    header = [
        '模型','文件数',
        '实体总数','实体有评估数','实体正确数','实体正确率','实体评估覆盖率',
        '关系总数','关系有评估数','关系正确数','关系正确率','关系评估覆盖率'
    ]
    with out_csv.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f); w.writerow(header)
        for mk, stats in all_stats.items():
            w.writerow([
                mk, stats['files_scanned'],
                stats['entity_total'], stats['entity_with_eval'], stats['entity_correct'], stats['entity_accuracy'], stats['entity_eval_coverage'],
                stats['relation_total'], stats['relation_with_eval'], stats['relation_correct'], stats['relation_accuracy'], stats['relation_eval_coverage']
            ])

def format_percent(p: Optional[float]) -> str:
    return 'NA' if p is None else f"{p*100:.2f}%"

def main():
    parser = argparse.ArgumentParser(description='统计多个模型打分 JSON 中实体与关系正确率并绘图')
    parser.add_argument('--models', nargs='*', default=['deepseek','gemini','kimi'], help='要统计的模型列表 (默认: deepseek gemini kimi)')
    parser.add_argument('--no-figure', action='store_true', help='只生成 CSV，不绘图')
    parser.add_argument('--title-suffix', type=str, default='', help='标题后缀')
    parser.add_argument('--summary-only', action='store_true', help='只生成汇总 CSV，不生成单模型 CSV')
    parser.add_argument('--no-summary', action='store_true', help='不生成汇总 CSV')
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    # 修正根目录推断：
    # 原来使用 parents[2] 得到的是 “…/指标统计计算”，再拼接 '指标统计计算' 导致重复段。
    # 当前脚本路径结构：EXP-1/指标统计计算/指标三：模型打分/code/绘图脚本/脚本.py
    # 需要的项目根 EXP-1 = parents[3]
    root_dir = script_dir.parents[3]
    if not (root_dir / '指标统计计算').exists():  # 防御：若层级变化则回退
        # 回退到旧逻辑（尽量不中断执行）
        root_dir = script_dir.parents[2]
        print(f'[INFO] 未在 parents[3] 发现 标识目录，使用回退 root_dir={root_dir}')

    # 输入根：指标统计计算/指标三：模型打分/打分结果/{model}
    score_base = root_dir / '指标统计计算' / '指标三：模型打分' / '打分结果'
    out_base = root_dir / '指标统计计算' / '指标三：模型打分' / '统计结果'
    out_tables = out_base / '表格'
    out_figs = out_base / '图表'
    out_tables.mkdir(parents=True, exist_ok=True)
    out_figs.mkdir(parents=True, exist_ok=True)

    all_stats: Dict[str, dict] = {}
    for mk in args.models:
        input_dir = score_base / mk
        if not input_dir.exists():
            print(f'[WARN] 模型 {mk} 目录不存在: {input_dir}，跳过。')
            continue
        stats = aggregate(input_dir)
        all_stats[mk] = stats
        print(f'== {mk} ==')
        print('  扫描文件数           :', stats['files_scanned'])
        print('  实体: 总/有评估/正确 :', stats['entity_total'], stats['entity_with_eval'], stats['entity_correct'])
        print('  实体: 正确率          :', format_percent(stats['entity_accuracy']))
        print('  实体: 评估覆盖率      :', format_percent(stats['entity_eval_coverage']))
        print('  关系: 总/有评估/正确 :', stats['relation_total'], stats['relation_with_eval'], stats['relation_correct'])
        print('  关系: 正确率          :', format_percent(stats['relation_accuracy']))
        print('  关系: 评估覆盖率      :', format_percent(stats['relation_eval_coverage']))

        if not args.summary_only:
            write_single_csv(mk, stats, out_tables)
        if not args.no_figure:
            plot_accuracy(mk, stats, out_figs, title_suffix=args.title_suffix)

    if all_stats and not args.no_summary:
        summary_csv = out_tables / '模型_实体关系正确率汇总.csv'
        write_summary_csv(all_stats, summary_csv)
        print('汇总 CSV 已写入:', summary_csv)

if __name__ == '__main__':
    main()
