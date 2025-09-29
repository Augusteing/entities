import json
from pathlib import Path
import matplotlib.pyplot as plt
import argparse
import csv
from typing import Iterable, Tuple, Set

"""单模型/全部模型实体与关系数量及类型统计绘图脚本

适配当前 EXP-3 目录结构，无需手动修改硬编码路径，可直接运行。例如：
    python 单模型_实体关系统计图.py --model gemini --csv
    python 单模型_实体关系统计图.py --all --use-paper-stems --only-correct --dedup-relations --csv
"""

# 动态定位到 抽取 根目录（脚本位于 抽取/code/绘图脚本/）
ROOT = Path(__file__).resolve().parents[2]  # .../EXP-3/抽取
DATA_BASE = ROOT / '数据结果'
EXTRACT_MODEL_DIR_MAP = {
    'deepseek': DATA_BASE / '提取结果_by_deepseek',
    'gemini': DATA_BASE / '提取结果_by_gemini',
    'kimi': DATA_BASE / '提取结果_by_kimi',
}

# 评估后的发送结果目录 (含 evaluation 字段) —— 与正确率统计保持一致
EVAL_MODEL_DIR_MAP = {
    'gemini': ROOT / '评估' / '数据结果' / '发送结果_by_gemini',
    'deepseek': ROOT / '评估' / '数据结果' / '发送结果_by_deepseek',  # 预留
    'kimi': ROOT / '评估' / '数据结果' / '发送结果_by_kimi',          # 预留
}

# 评估（限定子集）论文目录（与当前项目结构一致）
EVAL_PAPERS_DIR = ROOT / '评估' / '需要评估的论文'

# 输出目录（可根据需要调整到可视化结果位置）
OUT_DIR = ROOT / '实验过程图' / '指标一：实体和关系数量'
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 颜色（按需求四种）
COLOR_ENTITY_COUNT = '#925EB0'   # 紫
COLOR_ENTITY_TYPES = '#7E99F4'   # 蓝
COLOR_REL_COUNT    = '#7AB656'   # 绿
COLOR_REL_TYPES    = '#CC7C71'   # 红/棕

def load_json(path: Path):
    """读取 JSON，兼容:
    1. 单对象 { entities: [...], relations: [...] }
    2. 列表包裹 [ {..}, {..}, ... ] => 合并所有 dict 中的 entities/relations
    返回合并后的 dict 或 None。
    """
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        merged = { 'entities': [], 'relations': [] }
        for item in data:
            if isinstance(item, dict):
                ents = item.get('entities') or []
                rels = item.get('relations') or []
                if isinstance(ents, list):
                    merged['entities'].extend(ents)
                if isinstance(rels, list):
                    merged['relations'].extend(rels)
        return merged if (merged['entities'] or merged['relations']) else None
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


def _iter_target_json_files(model: str, restrict_stems: bool, source: str) -> Iterable[Path]:
    if source == 'extraction':
        mdir = EXTRACT_MODEL_DIR_MAP[model]
        pattern = '*.json'
    else:  # evaluation
        mdir = EVAL_MODEL_DIR_MAP.get(model)
        pattern = '*.response.json'
    if not mdir or not mdir.exists():
        print(f"[WARN] 模型目录不存在: {mdir}")
        return []
    if not restrict_stems:
        return list(mdir.glob(pattern))
    # 限定 评估 50 篇
    if not EVAL_PAPERS_DIR.exists():
        print(f"[WARN] 评估目录不存在: {EVAL_PAPERS_DIR}，回退使用全部文件。")
        return list(mdir.glob(pattern))
    stems = {p.stem for p in EVAL_PAPERS_DIR.glob('*.md')}
    # evaluation 文件可能有 .response.json 后缀
    files = []
    for s in stems:
        if source == 'extraction':
            cand = mdir / f"{s}.json"
        else:
            cand = mdir / f"{s}.response.json"
        if cand.exists():
            files.append(cand)
    missing = stems - {f.stem.replace('.response','') for f in files}
    if missing:
        print(f"[INFO] 评估集合中缺失 JSON 数: {len(missing)}")
    return files


def aggregate(model: str, restrict_stems: bool, only_correct: bool, dedup_rel: bool, only_correct_entities: bool,
              strict_correct: bool, debug_rel: bool, source: str):
    total_entities = 0
    total_relations = 0
    entity_types: Set[str] = set()
    relation_types: Set[str] = set()
    seen_rel: Set[Tuple[str, str, str]] = set()




    # 调试统计
    raw_rel_total = 0
    filtered_rel_due_to_eval = 0
    missing_eval_rel = 0

    target_files = list(_iter_target_json_files(model, restrict_stems, source))
    if not target_files:
        print(f"[INFO] 模型 {model} 无可统计 JSON 文件。")
    for jf in target_files:
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

    return total_entities, len(entity_types), total_relations, len(relation_types), len(target_files)

def plot_bar(model: str, stats, title_suffix: str = ''):
    (ent_count, ent_type_count, rel_count, rel_type_count, file_cnt) = stats
    labels = ['实体数量', '实体类型数量', '关系数量', '关系类型数量']
    values = [ent_count, ent_type_count, rel_count, rel_type_count]
    colors = [COLOR_ENTITY_COUNT, COLOR_ENTITY_TYPES, COLOR_REL_COUNT, COLOR_REL_TYPES]

    plt.figure(figsize=(6,4), dpi=150)
    bars = plt.bar(labels, values, color=colors, edgecolor='#333333')
    for bar, val in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height(), str(val), ha='center', va='bottom', fontsize=9)
    base_title = f'{model} 模型实体/关系数量统计'
    # 去掉动态的（提取-.../评估-...）后缀，仅保留固定的 50 篇标识
    base_title += '（50篇论文）'
    plt.title(base_title, fontsize=12)
    plt.ylabel('数量')
    plt.tight_layout()
    out_path = OUT_DIR / f'{model}_实体关系统计.png'
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()
    print(f"{model} 图已保存: {out_path}")
    avg_ent = f"{ent_count/file_cnt:.2f}" if file_cnt else '0'
    avg_rel = f"{rel_count/file_cnt:.2f}" if file_cnt else '0'
    print(f"统计 => 文件:{file_cnt} 实体总:{ent_count} (平均:{avg_ent}) 实体类型:{ent_type_count} 关系总:{rel_count} (平均:{avg_rel}) 关系类型:{rel_type_count}")

def main():
    parser = argparse.ArgumentParser(description='单模型或全部模型 实体/关系 数量与类型数量统计图 (支持提取结果 / 评估发送结果)')
    # 改为默认统计 提取结果_by_gemini 目录中的所有 JSON 文件；参数不再强制
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('--model', choices=list(EXTRACT_MODEL_DIR_MAP.keys()), default='gemini', help='单个模型名称，默认 gemini')
    parser.add_argument('--source', choices=['extraction','evaluation'], default='extraction', help='数据来源: extraction=提取结果目录(默认), evaluation=评估发送结果目录')
    group.add_argument('--all', action='store_true', help='一次性生成全部模型')
    parser.add_argument('--csv', action='store_true', help='输出一个汇总CSV')
    parser.add_argument('--use-paper-stems', action='store_true', help='严格仅统计评估目录(论文文献/需要评估的论文)列出的 50 篇')
    parser.add_argument('--only-correct', action='store_true', help='仅统计 evaluation 标记为 正确/correct 的关系')
    parser.add_argument('--only-correct-entities', action='store_true', help='仅统计 evaluation 标记为 正确/correct 的实体')
    parser.add_argument('--dedup-relations', action='store_true', help='关系按 (head, type, tail) 去重')
    parser.add_argument('--strict-correct', action='store_true', help='与 --only-correct 搭配：缺 evaluation 视为不正确。默认缺 evaluation 保留')
    parser.add_argument('--debug-relations', action='store_true', help='打印关系过滤调试信息')
    args = parser.parse_args()

    set_chinese_font()

    results = []
    targets = [args.model] if (not args.all) else list(EXTRACT_MODEL_DIR_MAP.keys())
    title_suffix = ('评估' if args.source=='evaluation' else '提取') + ('-限定50篇' if args.use_paper_stems else '-全部(或目录)')
    for m in targets:
        stats = aggregate(
            m,
            restrict_stems=args.use_paper_stems,
            only_correct=args.only_correct,
            dedup_rel=args.dedup_relations,
            only_correct_entities=args.only_correct_entities,
            strict_correct=args.strict_correct,
            debug_rel=args.debug_relations,
            source=args.source,
        )
        plot_bar(m, stats, title_suffix=title_suffix)
        results.append((m, *stats))

    csv_path = OUT_DIR / '模型实体关系统计汇总.csv'
    if args.csv:
        with csv_path.open('w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['模型','实体数量','实体类型数量','关系数量','关系类型数量','文件数','实体平均/篇','关系平均/篇'])
            for row in results:
                model, ent_cnt, ent_type_cnt, rel_cnt, rel_type_cnt, file_cnt = row
                ent_avg = f"{(ent_cnt/file_cnt):.2f}" if file_cnt else '0'
                rel_avg = f"{(rel_cnt/file_cnt):.2f}" if file_cnt else '0'
                w.writerow([model, ent_cnt, ent_type_cnt, rel_cnt, rel_type_cnt, file_cnt, ent_avg, rel_avg])
        print('汇总CSV已生成:', csv_path)
    else:
        print('未生成CSV（未使用 --csv），如果需要请添加该参数。')
    print('\n运行参数概览:')
    print('  use-paper-stems       =', args.use_paper_stems)
    print('  only-correct          =', args.only_correct)
    print('  only-correct-entities =', args.only_correct_entities)
    print('  dedup-relations       =', args.dedup_relations)
    print('  strict-correct        =', args.strict_correct)
    print('  debug-relations       =', args.debug_relations)
    print('  source                =', args.source)

if __name__ == '__main__':
    main()
