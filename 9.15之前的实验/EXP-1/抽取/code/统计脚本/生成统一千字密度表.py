import json
import re
import csv
from pathlib import Path

ROOT = Path(r"e:\知识图谱构建\9.15之前的实验\EXP-1")
PAPERS_DIR = ROOT / '论文文献' / '需要评估的论文'
MODEL_DIRS = {
    'deepseek': ROOT / '数据结果' / '提取结果_by_deepseek' / 'in_scope',
    'gemini':   ROOT / '数据结果' / '提取结果_by_gemini' / 'in_scope',
    'kimi':     ROOT / '数据结果' / '提取结果_by_kimi' / 'in_scope',
}

# 为避免文件被编辑器占用导致权限错误，先写入临时新文件，再视需要替换原文件
OUT_CSV = ROOT / '数据结果' / '按论文模型_实体关系千字密度_统一口径.csv'

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
    paper_lengths = read_markdown_lengths()
    stems = sorted(paper_lengths.keys())
    if len(stems) != 50:
        print(f"[提示] 发现评估论文 {len(stems)} 篇 (期望50)，继续处理。")

    rows = []
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
            rows.append([
                stem, model, raw_len, cleaned_len, ent_cnt, rel_cnt,
                f"{ent_density:.4f}", f"{rel_density:.4f}", f"{ratio:.4f}"
            ])
            # 加权总体统计（跨模型/跨论文）
            total_entities += ent_cnt
            total_relations += rel_cnt
            total_clean_len += cleaned_len

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow([
            '论文stem','模型','原始字符数','去空白字符数','实体数量','关系数量',
            '实体千字密度(按去空白)','关系千字密度(按去空白)','关系/实体比'
        ])
        w.writerows(rows)

    weighted_entity_density = (total_entities * 1000 / total_clean_len) if total_clean_len else 0
    weighted_relation_density = (total_relations * 1000 / total_clean_len) if total_clean_len else 0
    print('已生成统一口径 CSV ->', OUT_CSV)
    print('总体加权实体千字密度:', f"{weighted_entity_density:.4f}")
    print('总体加权关系千字密度:', f"{weighted_relation_density:.4f}")


if __name__ == '__main__':
    main()
