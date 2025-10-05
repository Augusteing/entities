import json
import re
import csv
from pathlib import Path
import argparse

ROOT = Path(r"e:\知识图谱构建\9.15之前的实验\EXP-1")

# 自适应查找评估论文目录：
# 0) 抽取/论文文献/需要评估的论文  (根据实际截图)
# 1) 论文文献/需要评估的论文
# 2) 评估/需要评估的论文
# 3) 抽取/论文文献
# 4) 论文文献
_candidate_paper_dirs = [
    ROOT / '抽取' / '论文文献' / '需要评估的论文',
    ROOT / '论文文献' / '需要评估的论文',
    ROOT / '评估' / '需要评估的论文',
    ROOT / '抽取' / '论文文献',
    ROOT / '论文文献',
]
PAPERS_DIR = None
for _d in _candidate_paper_dirs:
    if _d.exists() and any(_d.glob('*.md')):
        PAPERS_DIR = _d
        break
if PAPERS_DIR is None:
    # 若仍未找到，设为第一个候选（后续读取时返回 0 篇并提示）
    PAPERS_DIR = _candidate_paper_dirs[0]
print(f"[信息] 使用论文目录: {PAPERS_DIR}")

def list_md_count(path: Path) -> int:
    try:
        return sum(1 for _ in path.glob('*.md'))
    except Exception:
        return 0

def debug_candidates():
    print('[调试] 论文目录候选及其 .md 数量:')
    for idx, d in enumerate(_candidate_paper_dirs):
        print(f"  - [{idx}] {d} -> {list_md_count(d)}")

# 新的数据来源：抽取/数据结果/提取结果_by_<model>/in_scope
EXTRACTION_BASE = ROOT / '抽取' / '数据结果'
MODEL_DIRS = {
    'deepseek': EXTRACTION_BASE / '提取结果_by_deepseek' / 'in_scope',
    'gemini':   EXTRACTION_BASE / '提取结果_by_gemini' / 'in_scope',
    'kimi':     EXTRACTION_BASE / '提取结果_by_kimi' / 'in_scope',
}

# 输出位置调整：指标统计计算/指标二：实体关系密度/统计结果/表格/
SCRIPT_DIR = Path(__file__).resolve().parent  # .../指标统计计算/指标二：实体关系密度/code
INDICATOR_DIR = SCRIPT_DIR.parent            # .../指标统计计算/指标二：实体关系密度
OUT_TABLE_DIR = INDICATOR_DIR / '统计结果' / '按论文统计'
OUT_TABLE_DIR.mkdir(parents=True, exist_ok=True)

# 统一总表
OUT_CSV = OUT_TABLE_DIR / '按论文模型_实体关系千字密度_统一口径.csv'

CODE_FENCE_PATTERN = re.compile(r"```[\s\S]*?```", re.MULTILINE)
INLINE_CODE_PATTERN = re.compile(r"`[^`]*`")
IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\([^)]*\)")
LINK_PATTERN = re.compile(r"\[[^\]]*\]\([^)]*\)")
HEADING_PATTERN = re.compile(r"^#+.*$", re.MULTILINE)
QUOTE_PATTERN = re.compile(r"^>.*$", re.MULTILINE)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
EMPHASIS_PATTERN = re.compile(r"[*_~]")
WHITESPACE_PATTERN = re.compile(r"\s+")


def clean_and_count(text: str) -> int:
    """返回: 去 markdown 语法后再去全部空白的字符数 (不可逆清洗)."""
    # 去代码块 & 行内代码
    text = CODE_FENCE_PATTERN.sub('', text)
    text = INLINE_CODE_PATTERN.sub('', text)
    # 图片 / 链接 (放前防止残留方括号)
    text = IMAGE_PATTERN.sub('', text)
    text = LINK_PATTERN.sub('', text)
    # 标题 / 引用
    text = HEADING_PATTERN.sub('', text)
    text = QUOTE_PATTERN.sub('', text)
    # HTML 标记 与强调符
    text = HTML_TAG_PATTERN.sub('', text)
    text = EMPHASIS_PATTERN.sub('', text)
    # 去所有空白
    text = WHITESPACE_PATTERN.sub('', text)
    return len(text)


def read_markdown_lengths():
    mapping = {}
    for md in PAPERS_DIR.glob('*.md'):
        try:
            raw = md.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        raw_len = len(raw)
        cleaned_len = clean_and_count(raw)
        mapping[md.stem] = (raw_len, cleaned_len)
    return mapping


def load_json(path: Path):
    try:
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description='生成统一千字密度表')
    parser.add_argument('--debug', action='store_true', help='输出候选目录调试信息与样例')
    args = parser.parse_args()

    if args.debug:
        debug_candidates()

    paper_lengths = read_markdown_lengths()
    stems = sorted(paper_lengths.keys())
    if len(stems) != 50:
        print(f"[提示] 发现评估论文 {len(stems)} 篇 (期望50)，继续处理。")
        if args.debug and len(stems) == 0:
            print('[调试] 未找到任何 .md 文件，请确认论文是否位于上述候选目录之一。')
            print('[调试] 建议：如果真实路径不同，请提供具体路径，我可直接改为固定路径。')

    # 检查各模型 in_scope 目录
    for m, d in MODEL_DIRS.items():
        if not d.exists():
            print(f"[警告] 模型目录不存在: {d}")
        else:
            json_count = len(list(d.glob('*.json')))
            print(f"[信息] 模型 {m} in_scope JSON 数: {json_count}")

    rows = []
    # 按模型单独收集行（不含模型列冗余）
    per_model_rows = {m: [] for m in MODEL_DIRS.keys()}
    total_entities = 0
    total_relations = 0
    total_clean_len = 0

    # 遍历每篇 * 每模型，若 JSON 缺失则以 0 计
    for stem in stems:
        raw_len, cleaned_len = paper_lengths[stem]
        base_len = max(cleaned_len, 1)
        for model, mdir in MODEL_DIRS.items():
            jpath = mdir / f"{stem}.json"
            ent_cnt = rel_cnt = 0
            if jpath.exists():
                data = load_json(jpath)
                if isinstance(data, dict):
                    entities = data.get('entities', []) or []
                    relations = data.get('relations', []) or []
                    ent_cnt = len(entities)
                    rel_cnt = len(relations)
            ent_density = ent_cnt * 1000 / base_len
            rel_density = rel_cnt * 1000 / base_len
            ratio = (rel_cnt / ent_cnt) if ent_cnt else 0
            row = [
                stem, model, raw_len, cleaned_len, ent_cnt, rel_cnt,
                f"{ent_density:.4f}", f"{rel_density:.4f}", f"{ratio:.4f}"
            ]
            rows.append(row)
            per_model_rows[model].append([
                stem, raw_len, cleaned_len, ent_cnt, rel_cnt,
                f"{ent_density:.4f}", f"{rel_density:.4f}", f"{ratio:.4f}"
            ])
            # 加权总体统计（跨模型/跨论文）
            total_entities += ent_cnt
            total_relations += rel_cnt
            total_clean_len += cleaned_len

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    # 写统一总表
    with OUT_CSV.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow([
            '论文stem','模型','原始字符数','去空白字符数','实体数量','关系数量',
            '实体千字密度(按去空白)','关系千字密度(按去空白)','关系/实体比'
        ])
        w.writerows(rows)

    # 写分模型表
    for model, mrows in per_model_rows.items():
        out_path = OUT_TABLE_DIR / f'{model}_按论文_实体关系千字密度.csv'
        with out_path.open('w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow([
                '论文stem','原始字符数','去空白字符数','实体数量','关系数量',
                '实体千字密度(按去空白)','关系千字密度(按去空白)','关系/实体比'
            ])
            w.writerows(mrows)
        print('已生成分模型表 ->', out_path)

    weighted_entity_density = (total_entities * 1000 / total_clean_len) if total_clean_len else 0
    weighted_relation_density = (total_relations * 1000 / total_clean_len) if total_clean_len else 0
    print('已生成统一口径 CSV ->', OUT_CSV)
    print('总体加权实体千字密度:', f"{weighted_entity_density:.4f}")
    print('总体加权关系千字密度:', f"{weighted_relation_density:.4f}")


if __name__ == '__main__':
    main()
