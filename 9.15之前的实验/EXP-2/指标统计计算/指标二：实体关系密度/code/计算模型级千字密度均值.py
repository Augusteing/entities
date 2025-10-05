import csv
from pathlib import Path
from collections import defaultdict

ROOT = Path(r"e:\知识图谱构建\9.15之前的实验\EXP-1")

# 新的输入：来自 指标统计计算/指标二：实体关系密度/统计结果/按论文统计
SCRIPT_DIR = Path(__file__).resolve().parent
INDICATOR_DIR = SCRIPT_DIR.parent
INPUT_CSV = INDICATOR_DIR / '统计结果' / '按论文统计' / '按论文模型_实体关系千字密度_统一口径.csv'

# 输出：统计结果/模型统计/ 目录下
OUT_DIR = INDICATOR_DIR / '统计结果' / '模型统计'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = OUT_DIR / '模型_实体关系千字密度均值.csv'


def read_rows():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f'未找到输入文件: {INPUT_CSV}')
    with INPUT_CSV.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def main():
    data_per_model = defaultdict(lambda: {
        'entity_density_list': [],
        'relation_density_list': [],
        'total_entities': 0,
        'total_relations': 0,
        'total_clean_len': 0,
        'paper_count': 0,
    })

    for row in read_rows():
        model = row['模型']
        try:
            clean_len = int(row['去空白字符数'])
            ent_cnt = int(row['实体数量'])
            rel_cnt = int(row['关系数量'])
            ent_density = float(row['实体千字密度(按去空白)'])
            rel_density = float(row['关系千字密度(按去空白)'])
        except (KeyError, ValueError):
            continue
        m = data_per_model[model]
        m['entity_density_list'].append(ent_density)
        m['relation_density_list'].append(rel_density)
        m['total_entities'] += ent_cnt
        m['total_relations'] += rel_cnt
        m['total_clean_len'] += clean_len
        m['paper_count'] += 1

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow([
            '模型',
            '实体千字密度_未加权均值','关系千字密度_未加权均值',
            '实体千字密度_加权','关系千字密度_加权',
            '覆盖论文数','总实体数','总关系数','总去空白字符数'
        ])
        for model in sorted(data_per_model.keys()):
            m = data_per_model[model]
            if m['entity_density_list']:
                unweighted_ent_mean = sum(m['entity_density_list']) / len(m['entity_density_list'])
            else:
                unweighted_ent_mean = 0.0
            if m['relation_density_list']:
                unweighted_rel_mean = sum(m['relation_density_list']) / len(m['relation_density_list'])
            else:
                unweighted_rel_mean = 0.0
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

    print('模型级均值输出 ->', OUT_CSV)


if __name__ == '__main__':
    main()
