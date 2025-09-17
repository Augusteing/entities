import json
import csv
import argparse
from pathlib import Path


def load_items(path: Path):
    """
    读取一个评估JSON文件，返回 entities 与 relations 的列表（原始对象），
    若结构为 [ { entities: [...], relations: [...] } ] 或 { entities, relations } 均支持。
    解析失败则返回两个空列表。
    """
    try:
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list) and data:
            item = data[0]
        elif isinstance(data, dict):
            item = data
        else:
            return [], []
        entities = item.get('entities', []) or []
        relations = item.get('relations', []) or []
        return entities, relations
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return [], []


def count_eval(items):
    """
    统计一组对象的 evaluation 分布：正确/错误/不确定 及 有标记总数。
    仅统计含 evaluation 字段的对象。
    返回 dict: {correct, error, uncertain, total_marked}
    """
    correct = error = uncertain = 0
    for obj in items:
        if not isinstance(obj, dict):
            continue
        val = obj.get('evaluation')
        if val is None:
            continue
        if val == '正确':
            correct += 1
        elif val == '错误':
            error += 1
        elif val == '不确定':
            uncertain += 1
        else:
            # 未知取值亦不计入
            continue
    total_marked = correct + error + uncertain
    return {
        'correct': correct,
        'error': error,
        'uncertain': uncertain,
        'total_marked': total_marked,
    }


def safe_rate(numer, denom):
    return (numer / denom) if denom else 0.0


def run(input_dir: Path, export_csv: bool = True):
    files = sorted(input_dir.glob('*.json'))
    per_file_rows = []

    # 总体（合计）
    grand_correct = grand_error = grand_uncertain = grand_total = 0
    # 分项总体（实体/关系）
    grand_ents_correct = grand_ents_error = grand_ents_uncertain = grand_ents_total = 0
    grand_rels_correct = grand_rels_error = grand_rels_uncertain = grand_rels_total = 0

    for fp in files:
        ents, rels = load_items(fp)
        stats_ents = count_eval(ents)
        stats_rels = count_eval(rels)
        file_correct = stats_ents['correct'] + stats_rels['correct']
        file_error = stats_ents['error'] + stats_rels['error']
        file_uncertain = stats_ents['uncertain'] + stats_rels['uncertain']
        file_total = stats_ents['total_marked'] + stats_rels['total_marked']
        file_rate = safe_rate(file_correct, file_total)
        ents_rate = safe_rate(stats_ents['correct'], stats_ents['total_marked'])
        rels_rate = safe_rate(stats_rels['correct'], stats_rels['total_marked'])

        grand_correct += file_correct
        grand_error += file_error
        grand_uncertain += file_uncertain
        grand_total += file_total

        # 分项累计
        grand_ents_correct += stats_ents['correct']
        grand_ents_error += stats_ents['error']
        grand_ents_uncertain += stats_ents['uncertain']
        grand_ents_total += stats_ents['total_marked']

        grand_rels_correct += stats_rels['correct']
        grand_rels_error += stats_rels['error']
        grand_rels_uncertain += stats_rels['uncertain']
        grand_rels_total += stats_rels['total_marked']

        per_file_rows.append({
            'file': fp.name,
            'entities_marked': stats_ents['total_marked'],
            'entities_correct': stats_ents['correct'],
            'entities_pass_rate': f"{ents_rate*100:.2f}%",
            'relations_marked': stats_rels['total_marked'],
            'relations_correct': stats_rels['correct'],
            'relations_pass_rate': f"{rels_rate*100:.2f}%",
            'total_marked': file_total,
            'total_correct': file_correct,
            'pass_rate': f"{file_rate*100:.2f}%",
        })

    overall_rate = safe_rate(grand_correct, grand_total)
    ents_overall_rate = safe_rate(grand_ents_correct, grand_ents_total)
    rels_overall_rate = safe_rate(grand_rels_correct, grand_rels_total)

    # 打印摘要
    summary = {
        'files_count': len(files),
        # 总体
        'total_marked': grand_total,
        'total_correct': grand_correct,
        'total_error': grand_error,
        'total_uncertain': grand_uncertain,
        'overall_pass_rate': f"{overall_rate*100:.2f}%",
        # 实体分项
        'entities_total_marked': grand_ents_total,
        'entities_total_correct': grand_ents_correct,
        'entities_total_error': grand_ents_error,
        'entities_total_uncertain': grand_ents_uncertain,
        'entities_pass_rate': f"{ents_overall_rate*100:.2f}%",
        # 关系分项
        'relations_total_marked': grand_rels_total,
        'relations_total_correct': grand_rels_correct,
        'relations_total_error': grand_rels_error,
        'relations_total_uncertain': grand_rels_uncertain,
        'relations_pass_rate': f"{rels_overall_rate*100:.2f}%",
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    # 可选导出CSV（每文件）
    if export_csv and files:
        out_csv = input_dir / 'pass_rate_per_file.csv'
        with out_csv.open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    'file',
                    'entities_marked', 'entities_correct', 'entities_pass_rate',
                    'relations_marked', 'relations_correct', 'relations_pass_rate',
                    'total_marked', 'total_correct', 'pass_rate'
                ]
            )
            writer.writeheader()
            writer.writerows(per_file_rows)
        # 顺带写总体摘要
        out_json = input_dir / 'pass_rate_summary.json'
        with out_json.open('w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description='统计评估JSON合格率（evaluation=="正确" 占比）')
    parser.add_argument('--input-dir', required=True, help='包含 *.json 的目录')
    parser.add_argument('--no-export', action='store_true', help='不导出CSV与摘要JSON')
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists() or not input_dir.is_dir():
        raise SystemExit(f'输入目录不存在或不是目录: {input_dir}')

    run(input_dir, export_csv=not args.no_export)


if __name__ == '__main__':
    main()
