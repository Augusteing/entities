import csv
import argparse
from pathlib import Path
from collections import defaultdict

# 自动推断根：脚本位于 抽取/code/统计脚本/，上两级即 抽取 目录
DEFAULT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = '数据结果/按论文模型_实体关系千字密度_统一口径.csv'
DEFAULT_OUTPUT = '数据结果/模型_实体关系千字密度均值.csv'

REQUIRED_COLUMNS = [
    '模型','去空白字符数','实体数量','关系数量',
    '实体千字密度(按去空白)','关系千字密度(按去空白)'
]

def parse_args():
    p = argparse.ArgumentParser(description='汇总模型级实体/关系千字密度（未加权均值与加权密度）')
    p.add_argument('--root', type=Path, default=DEFAULT_ROOT, help='根目录(指向 抽取 )，默认自动推断')
    p.add_argument('--input', type=Path, help='输入 CSV 相对或绝对路径；默认 root/数据结果/按论文模型_实体关系千字密度_统一口径.csv')
    p.add_argument('--output', type=Path, help='输出 CSV；默认 root/数据结果/模型_实体关系千字密度均值.csv')
    p.add_argument('--models', type=str, help='仅统计指定模型(逗号分隔)，示例: gemini 或 deepseek,kimi')
    p.add_argument('--min-papers', type=int, default=1, help='模型最少覆盖论文篇数(低于则仍输出但可用于后续过滤)')
    return p.parse_args()

def resolve_paths(args):
    root = args.root
    input_csv = args.input if args.input else (root / DEFAULT_INPUT)
    output_csv = args.output if args.output else (root / DEFAULT_OUTPUT)
    return root, input_csv, output_csv

def load_rows(input_csv: Path):
    if not input_csv.exists():
        raise FileNotFoundError(f'未找到输入文件: {input_csv}')
    with input_csv.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        missing = [c for c in REQUIRED_COLUMNS if c not in header]
        if missing:
            raise ValueError(f'输入文件缺少必要列: {missing}; 现有列: {header}')
        for row in reader:
            yield row

def main():
    args = parse_args()
    root, input_csv, output_csv = resolve_paths(args)

    # 模型过滤集合
    model_filter = None
    if args.models:
        model_filter = {m.strip() for m in args.models.split(',') if m.strip()}
        if not model_filter:
            print('[警告] --models 解析后为空，忽略该过滤。')
            model_filter = None

    data_per_model = defaultdict(lambda: {
        'entity_density_list': [],
        'relation_density_list': [],
        'total_entities': 0,
        'total_relations': 0,
        'total_clean_len': 0,
        'paper_count': 0,
    })

    total_rows = 0
    for row in load_rows(input_csv):
        total_rows += 1
        model = row.get('模型')
        if model_filter and model not in model_filter:
            continue
        try:
            clean_len = int(row['去空白字符数'])
            ent_cnt = int(row['实体数量'])
            rel_cnt = int(row['关系数量'])
            ent_density = float(row['实体千字密度(按去空白)'])
            rel_density = float(row['关系千字密度(按去空白)'])
        except (KeyError, ValueError):
            # 跳过异常行
            continue
        m = data_per_model[model]
        m['entity_density_list'].append(ent_density)
        m['relation_density_list'].append(rel_density)
        m['total_entities'] += ent_cnt
        m['total_relations'] += rel_cnt
        m['total_clean_len'] += clean_len
        m['paper_count'] += 1

    if not data_per_model:
        print('[提示] 没有匹配到任何模型数据，可能是过滤过严。')
        return

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow([
            '模型',
            '实体千字密度_未加权均值','关系千字密度_未加权均值',
            '实体千字密度_加权','关系千字密度_加权',
            '覆盖论文数','总实体数','总关系数','总去空白字符数'
        ])
        for model in sorted(data_per_model.keys()):
            m = data_per_model[model]
            ent_list = m['entity_density_list']
            rel_list = m['relation_density_list']
            unweighted_ent_mean = sum(ent_list)/len(ent_list) if ent_list else 0.0
            unweighted_rel_mean = sum(rel_list)/len(rel_list) if rel_list else 0.0
            if m['total_clean_len'] > 0:
                weighted_ent = m['total_entities'] * 1000 / m['total_clean_len']
                weighted_rel = m['total_relations'] * 1000 / m['total_clean_len']
            else:
                weighted_ent = weighted_rel = 0.0
            w.writerow([
                model,
                f"{unweighted_ent_mean:.4f}", f"{unweighted_rel_mean:.4f}",
                f"{weighted_ent:.4f}", f"{weighted_rel:.4f}",
                m['paper_count'], m['total_entities'], m['total_relations'], m['total_clean_len']
            ])

    print('模型级均值输出 ->', output_csv)
    print('参数:')
    print('  root       =', root)
    print('  input      =', input_csv)
    print('  output     =', output_csv)
    print('  models     =', args.models or 'ALL')
    print('  total_rows =', total_rows)
    print('  models_out =', len(data_per_model))

if __name__ == '__main__':
    main()
