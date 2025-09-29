import json
import re
import csv
import argparse
from pathlib import Path

# ---------- 路径与可配置 ----------
# 默认自动推断: 当前文件位于  抽取/code/统计脚本/  下, 向上两级即为 抽取 目录
DEFAULT_ROOT = Path(__file__).resolve().parents[2]

def build_paths(root: Path):
    papers_dir = root / '论文文献' / '需要评估的论文'
    model_dirs = {
        'deepseek': root / '数据结果' / '提取结果_by_deepseek' / 'in_scope',
        'gemini':   root / '数据结果' / '提取结果_by_gemini' / 'in_scope',
        'kimi':     root / '数据结果' / '提取结果_by_kimi' / 'in_scope',
    }
    out_csv = root / '数据结果' / '按论文模型_实体关系千字密度_统一口径.csv'
    return papers_dir, model_dirs, out_csv

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


def read_markdown_lengths(papers_dir: Path):
    mapping = {}
    for md in papers_dir.glob('*.md'):
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


def parse_args():
    p = argparse.ArgumentParser(description='生成 按论文×模型 的实体/关系千字密度统一口径表')
    p.add_argument('--root', type=Path, default=DEFAULT_ROOT,
                   help='根目录(应指向 抽取 目录)，默认自动推断为当前脚本上两级目录')
    p.add_argument('--expect', type=int, default=50, help='期望论文篇数(用于提示)')
    p.add_argument('--unique-weight', action='store_true',
                   help='加权密度时仅按唯一论文长度汇总(默认按 论文×模型 计数)')
    p.add_argument('--models', type=str, help='仅统计指定模型，逗号分隔，例如: gemini 或 deepseek,kimi')
    return p.parse_args()


def main():
    args = parse_args()
    papers_dir, model_dirs, out_csv = build_paths(args.root)

    # 处理模型过滤
    if args.models:
        requested = [m.strip() for m in args.models.split(',') if m.strip()]
        invalid = [m for m in requested if m not in model_dirs]
        if invalid:
            print(f"[警告] 下列模型名称无效，将忽略: {invalid}；可用: {list(model_dirs.keys())}")
        filtered = {k: v for k, v in model_dirs.items() if k in requested}
        if not filtered:
            print('[错误] 过滤后没有有效模型，程序终止。')
            return
        model_dirs = filtered
    if not papers_dir.exists():
        print(f"[错误] 论文目录不存在: {papers_dir}")
        return
    paper_lengths = read_markdown_lengths(papers_dir)
    stems = sorted(paper_lengths.keys())
    if len(stems) != args.expect:
        print(f"[提示] 发现评估论文 {len(stems)} 篇 (期望 {args.expect} )，继续处理。")

    rows = []
    total_entities = 0
    total_relations = 0
    total_clean_len = 0          # 按 (论文×模型) 统计的总长度
    unique_clean_len = 0         # 按唯一论文统计的长度（若启用 --unique-weight 使用）

    unique_clean_len = sum(v[1] for v in paper_lengths.values())

    # 遍历每篇 * 每模型，若 JSON 缺失则以 0 计
    for stem in stems:
        raw_len, cleaned_len = paper_lengths[stem]
        base_len = max(cleaned_len, 1)
        for model, mdir in model_dirs.items():
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

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow([
            '论文stem','模型','原始字符数','去空白字符数','实体数量','关系数量',
            '实体千字密度(按去空白)','关系千字密度(按去空白)','关系/实体比'
        ])
        w.writerows(rows)
    if args.unique_weight:
        base_len_for_weight = unique_clean_len
        mode_desc = '按唯一论文长度'
    else:
        base_len_for_weight = total_clean_len
        mode_desc = '按论文×模型展开长度'
    weighted_entity_density = (total_entities * 1000 / base_len_for_weight) if base_len_for_weight else 0
    weighted_relation_density = (total_relations * 1000 / base_len_for_weight) if base_len_for_weight else 0
    print('已生成统一口径 CSV ->', out_csv)
    print(f'总体加权实体千字密度({mode_desc}):', f"{weighted_entity_density:.4f}")
    print(f'总体加权关系千字密度({mode_desc}):', f"{weighted_relation_density:.4f}")
    print('\n参数确认:')
    print('  root                =', args.root)
    print('  expect              =', args.expect)
    print('  unique-weight       =', args.unique_weight)
    print('  models              =', args.models or 'ALL')


if __name__ == '__main__':
    main()
