import json
from pathlib import Path
import argparse
import matplotlib.pyplot as plt
from typing import Optional, Tuple

# 颜色与字体风格沿用 原脚本 单模型_实体关系统计图.py
COLOR_ENTITY = '#925EB0'   # 实体（原: 实体数量）
COLOR_REL    = '#7AB656'   # 关系（原: 关系数量）

PREFERRED_FONTS = ['Microsoft YaHei', 'SimHei', 'STHeiti', 'Songti SC', 'Arial Unicode MS']

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

    ent_total = len(entities)
    ent_with_eval = 0
    ent_correct = 0
    for e in entities:
        flag = _is_correct(e.get('evaluation'))
        if flag is None:
            continue
        ent_with_eval += 1
        if flag:
            ent_correct += 1

    rel_total = len(relations)
    rel_with_eval = 0
    rel_correct = 0
    for r in relations:
        flag = _is_correct(r.get('evaluation'))
        if flag is None:
            continue
        rel_with_eval += 1
        if flag:
            rel_correct += 1

    return (ent_total, ent_with_eval, ent_correct), (rel_total, rel_with_eval, rel_correct)

def aggregate(dir_path: Path):
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

def plot_accuracy(stats: dict, out_dir: Path, title_suffix: str = '') -> Path:
    """绘制实体与关系正确率柱状图。
    实体柱使用 COLOR_ENTITY, 关系柱使用 COLOR_REL。"""
    set_chinese_font()
    acc_e = stats['entity_accuracy']
    acc_r = stats['relation_accuracy']
    values = []
    labels = []
    colors = []
    if acc_e is not None:
        labels.append('实体正确率')
        values.append(acc_e * 100)
        colors.append(COLOR_ENTITY)
    if acc_r is not None:
        labels.append('关系正确率')
        values.append(acc_r * 100)
        colors.append(COLOR_REL)
    if not values:
        print('[WARN] 没有可绘制的正确率(无 evaluation 标注)。')
        return out_dir / '空_正确率.png'

    plt.figure(figsize=(5,4), dpi=150)
    bars = plt.bar(labels, values, color=colors, edgecolor='#333333')
    for bar, val in zip(bars, values):
        plt.text(bar.get_x()+bar.get_width()/2, bar.get_height(), f"{val:.1f}%", ha='center', va='bottom', fontsize=10)
    base_title = 'Gemini 实体/关系正确率'
    if title_suffix:
        base_title += f'（{title_suffix}）'
    plt.title(base_title)
    plt.ylabel('正确率 (%)')
    plt.ylim(0, 100)
    plt.tight_layout()
    out_path = out_dir / 'gemini_实体关系正确率.png'
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()
    return out_path

def write_csv(stats: dict, out_csv: Path):
    import csv
    header = [
        'files_scanned',
        'entity_total','entity_with_eval','entity_correct','entity_accuracy','entity_eval_coverage',
        'relation_total','relation_with_eval','relation_correct','relation_accuracy','relation_eval_coverage'
    ]
    with out_csv.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(header)
        row = [
            stats['files_scanned'],
            stats['entity_total'], stats['entity_with_eval'], stats['entity_correct'], stats['entity_accuracy'], stats['entity_eval_coverage'],
            stats['relation_total'], stats['relation_with_eval'], stats['relation_correct'], stats['relation_accuracy'], stats['relation_eval_coverage']
        ]
            
        w.writerow(row)

def format_percent(p: Optional[float]) -> str:
    return 'NA' if p is None else f"{p*100:.2f}%"

def main():
    parser = argparse.ArgumentParser(description='统计 Gemini 评估 JSON 中实体与关系正确率并绘图')
    parser.add_argument('--json-dir', type=str, default=None, help='JSON 目录(默认: 抽取/评估/数据结果/发送结果_by_gemini)')
    parser.add_argument('--out-dir', type=str, default=None, help='输出图表/CSV 目录(默认: 同级 创建 实验过程图/正确率)')
    parser.add_argument('--no-figure', action='store_true', help='只生成 CSV，不绘图')
    parser.add_argument('--csv-name', type=str, default='gemini_实体关系正确率统计.csv', help='CSV 文件名')
    parser.add_argument('--title-suffix', type=str, default='', help='图表标题后缀')
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    # script_dir = .../抽取/评估/code  -> 抽取根 = parents[2]
    root_dir = script_dir.parents[2]
    default_json_dir = root_dir / '评估' / '数据结果' / '发送结果_by_gemini'

    json_dir = Path(args.json_dir) if args.json_dir else default_json_dir
    if not json_dir.exists():
        raise SystemExit(f'[ERROR] JSON 目录不存在: {json_dir}')

    if args.out_dir:
        out_dir = Path(args.out_dir)
    else:
        out_dir = root_dir / '评估' / '实验过程图' / '正确率'
    out_dir.mkdir(parents=True, exist_ok=True)

    stats = aggregate(json_dir)

    print('== 统计结果 ==')
    print('扫描文件数           :', stats['files_scanned'])
    print('实体: 总数/有评估/正确:', stats['entity_total'], stats['entity_with_eval'], stats['entity_correct'])
    print('实体: 正确率          :', format_percent(stats['entity_accuracy']))
    print('实体: 评估覆盖率      :', format_percent(stats['entity_eval_coverage']))
    print('关系: 总数/有评估/正确:', stats['relation_total'], stats['relation_with_eval'], stats['relation_correct'])
    print('关系: 正确率          :', format_percent(stats['relation_accuracy']))
    print('关系: 评估覆盖率      :', format_percent(stats['relation_eval_coverage']))

    # CSV
    out_csv = out_dir / args.csv_name
    write_csv(stats, out_csv)
    print('CSV 已写入:', out_csv)

    if not args.no_figure:
        fig_path = plot_accuracy(stats, out_dir, title_suffix=args.title_suffix)
        print('图表已保存:', fig_path)
    else:
        print('已跳过绘图 (--no-figure)')

    # 简单退出码策略: 若任一准确率为 None 但对应 total>0, 可提示
    warnings = []
    if stats['entity_total'] and stats['entity_accuracy'] is None:
        warnings.append('实体缺 evaluation 标注 (无法计算正确率)')
    if stats['relation_total'] and stats['relation_accuracy'] is None:
        warnings.append('关系缺 evaluation 标注 (无法计算正确率)')
    if warnings:
        print('\n[WARN] ' + ' | '.join(warnings))

if __name__ == '__main__':
    main()
