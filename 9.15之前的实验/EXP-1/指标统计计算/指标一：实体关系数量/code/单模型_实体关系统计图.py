import json
from pathlib import Path
import matplotlib.pyplot as plt
import argparse
import csv
from typing import Iterable, Tuple, Set

# 配置路径
ROOT = Path(r"e:\知识图谱构建\9.15之前的实验\EXP-1")
# 数据源：抽取/数据结果 下的三个模型抽取结果
DATA_BASE = ROOT / '抽取' / '数据结果'
MODEL_DIR_MAP = {
    'deepseek': DATA_BASE / '提取结果_by_deepseek' / 'in_scope',
    'gemini': DATA_BASE / '提取结果_by_gemini' / 'in_scope',
    'kimi': DATA_BASE / '提取结果_by_kimi' / 'in_scope',
}

# 评估论文目录（用于精确限制 50 篇）
EVAL_PAPERS_DIR = ROOT / '论文文献' / '需要评估的论文'
# 输出目录：指标统计计算/指标一：实体关系数量/统计结果/{图像, 表格}
_BASE_STAT_DIR = ROOT / '指标统计计算' / '指标一：实体关系数量' / '统计结果'
OUT_IMG_DIR = _BASE_STAT_DIR / '图像'
OUT_TABLE_DIR = _BASE_STAT_DIR / '表格'
OUT_IMG_DIR.mkdir(parents=True, exist_ok=True)
OUT_TABLE_DIR.mkdir(parents=True, exist_ok=True)

# 颜色（按需求四种）
COLOR_ENTITY_COUNT = '#925EB0'   # 紫
COLOR_ENTITY_TYPES = '#7E99F4'   # 蓝
COLOR_REL_COUNT    = '#7AB656'   # 绿
COLOR_REL_TYPES    = '#CC7C71'   # 红/棕

def load_json(path: Path):
    try:
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def set_chinese_font():
    """尝试设置中文字体，减少中文文字方块 / 缺字警告。"""
    preferred = ['Microsoft YaHei', 'SimHei', 'STHeiti', 'Songti SC', 'Arial Unicode MS']
    from matplotlib import font_manager
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in preferred:
        if name in available:
            plt.rcParams['font.sans-serif'] = [name]
            plt.rcParams['axes.unicode_minus'] = False
            return name
    return None


def _is_correct(meta):
    """基础判断: evaluation 字段是否标注为正确。用于 strict 模式。"""
    if meta is None:
        return None  # 返回 None 让上层决定缺失策略
    if isinstance(meta, bool):
        return bool(meta)
    if isinstance(meta, str):
        val = meta.strip().lower()
        if val in {'正确', 'correct', 'true', 'yes'}:
            return True
        if val in {'错误', 'error', 'false', 'no'}:
            return False
    return False


def _relation_signature(r: dict) -> Tuple[str, str, str]:
    """构造关系去重用签名，尽量兼容不同字段命名。"""
    # 常见字段：head/tail 或 subject/object 或 source/target
    head = r.get('head') or r.get('subject') or r.get('source') or ''
    tail = r.get('tail') or r.get('object') or r.get('target') or ''
    rtype = r.get('type') or r.get('relation') or ''
    # 若 head/tail 是字典（含文本），尝试取 'text' 或 'name'
    def norm(x):
        if isinstance(x, dict):
            return x.get('text') or x.get('name') or json.dumps(x, ensure_ascii=False)
        return str(x)
    return (norm(head), rtype, norm(tail))


def _iter_target_json_files(model: str, restrict_stems: bool) -> Iterable[Path]:
    mdir = MODEL_DIR_MAP[model]
    if not mdir.exists():
        return []
    if not restrict_stems:
        return mdir.glob('*.json')
    # 读取评估论文 50 篇的 stem
    stems = {p.stem for p in EVAL_PAPERS_DIR.glob('*.md')}
    return [mdir / f"{s}.json" for s in stems if (mdir / f"{s}.json").exists()]


def aggregate(model: str, restrict_stems: bool, only_correct: bool, dedup_rel: bool, only_correct_entities: bool,
              strict_correct: bool, debug_rel: bool):
    total_entities = 0
    total_relations = 0
    entity_types: Set[str] = set()
    relation_types: Set[str] = set()
    seen_rel: Set[Tuple[str, str, str]] = set()

    # 调试统计
    raw_rel_total = 0
    filtered_rel_due_to_eval = 0
    missing_eval_rel = 0

    for jf in _iter_target_json_files(model, restrict_stems):
        data = load_json(jf)
        if not isinstance(data, dict):
            continue
        entities = data.get('entities', []) or []
        relations = data.get('relations', []) or []

        # 过滤实体
        filtered_entities = []
        for e in entities:
            if only_correct_entities:
                if not _is_correct(e.get('evaluation')):
                    continue
            filtered_entities.append(e)
        total_entities += len(filtered_entities)
        for e in filtered_entities:
            et = e.get('type')
            if et:
                entity_types.add(et)

        # 过滤关系
        for r in relations:
            raw_rel_total += 1
            keep = True
            if only_correct:
                eval_flag = _is_correct(r.get('evaluation'))
                if eval_flag is None:
                    # 缺 evaluation：strict 模式视为不通过；非 strict 模式视为通过
                    if strict_correct:
                        keep = False
                        missing_eval_rel += 1
                    else:
                        # 允许保留
                        pass
                else:
                    if not eval_flag:
                        keep = False
                        filtered_rel_due_to_eval += 1
            if not keep:
                continue
            sig = _relation_signature(r)
            if dedup_rel:
                if sig in seen_rel:
                    continue
                seen_rel.add(sig)
            total_relations += 1
            rt = r.get('type') or r.get('relation')
            if rt:
                relation_types.add(rt)

    if debug_rel and only_correct:
        print(f"[DEBUG][{model}] 原始关系数={raw_rel_total} 保留={total_relations} 过滤(显式错误)={filtered_rel_due_to_eval} 缺evaluation={missing_eval_rel} strict={strict_correct}")
        if strict_correct and raw_rel_total and (missing_eval_rel == raw_rel_total):
            print(f"[WARN][{model}] 所有关系均缺 evaluation 字段，strict 模式导致全部被排除。")

    return total_entities, len(entity_types), total_relations, len(relation_types)

def plot_bar(model: str, stats):
    (ent_count, ent_type_count, rel_count, rel_type_count) = stats
    labels = ['实体数量', '实体类型数量', '关系数量', '关系类型数量']
    values = [ent_count, ent_type_count, rel_count, rel_type_count]
    colors = [COLOR_ENTITY_COUNT, COLOR_ENTITY_TYPES, COLOR_REL_COUNT, COLOR_REL_TYPES]

    plt.figure(figsize=(6,4), dpi=150)
    bars = plt.bar(labels, values, color=colors, edgecolor='#333333')
    for bar, val in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height(), str(val), ha='center', va='bottom', fontsize=9)
    plt.title(f'{model} 模型实体和关系抽取数量统计（50篇）', fontsize=12)
    plt.ylabel('数量')
    plt.tight_layout()
    out_path = OUT_IMG_DIR / f'{model}实体和关系抽取数量请执行.png'
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()
    print(f"{model} 图已保存: {out_path}")
    print(f"统计 => 实体数量:{ent_count} 实体类型:{ent_type_count} 关系数量:{rel_count} 关系类型:{rel_type_count}")

def main():
    parser = argparse.ArgumentParser(description='单模型或全部模型 50篇 实体/关系 数量与类型数量统计图 (可选过滤)')
    # 允许不传参数：不再强制 required=True
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('--model', choices=list(MODEL_DIR_MAP.keys()), help='单个模型名称')
    group.add_argument('--all', action='store_true', help='一次性生成全部模型')
    parser.add_argument('--csv', action='store_true', help='输出一个汇总CSV')
    parser.add_argument('--use-paper-stems', action='store_true', help='严格仅统计评估目录(论文文献/需要评估的论文)列出的 50 篇')
    parser.add_argument('--only-correct', action='store_true', help='仅统计 evaluation 标记为 正确/correct 的关系')
    parser.add_argument('--only-correct-entities', action='store_true', help='仅统计 evaluation 标记为 正确/correct 的实体')
    parser.add_argument('--dedup-relations', action='store_true', help='关系按 (head, type, tail) 去重')
    parser.add_argument('--strict-correct', action='store_true', help='与 --only-correct 搭配：缺 evaluation 视为不正确。默认缺 evaluation 保留')
    parser.add_argument('--debug-relations', action='store_true', help='打印关系过滤调试信息')
    args = parser.parse_args()

    # 若未指定 --model 或 --all，默认执行全部并自动导出 CSV
    if not args.model and not args.all:
        print('[INFO] 未指定 --model/--all，默认执行全部模型 (--all) 并输出汇总 CSV。')
        args.all = True
        args.csv = True

    set_chinese_font()

    results = []
    targets = [args.model] if args.model else list(MODEL_DIR_MAP.keys())
    for m in targets:
        stats = aggregate(
            m,
            restrict_stems=args.use_paper_stems,
            only_correct=args.only_correct,
            dedup_rel=args.dedup_relations,
            only_correct_entities=args.only_correct_entities,
            strict_correct=args.strict_correct,
            debug_rel=args.debug_relations,
        )
        plot_bar(m, stats)
        results.append((m, *stats))

    if args.csv:
        csv_path = OUT_TABLE_DIR / '模型实体关系统计汇总.csv'
        with csv_path.open('w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['模型','实体数量','实体类型数量','关系数量','关系类型数量'])
            for row in results:
                w.writerow(row)
        print('汇总CSV已生成:', csv_path)

if __name__ == '__main__':
    main()
