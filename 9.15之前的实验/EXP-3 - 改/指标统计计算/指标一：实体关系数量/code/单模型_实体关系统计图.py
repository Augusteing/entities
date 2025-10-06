import json
from pathlib import Path
import matplotlib.pyplot as plt
import argparse
import csv
from typing import Iterable, Tuple, Set, Dict, List
import os

"""
通用单模型/全部模型 实体/关系 数量+类型 统计脚本

适配目录结构 (EXP-1 / EXP-2 / EXP-3)：
  <EXPROOT>/
    抽取/数据结果/提取结果_by_<model>/in_scope/*.json
    论文文献/需要评估的论文/*.md   (用于 50 篇限定)
    指标统计计算/指标一：实体关系数量/统计结果/{图像, 表格}

自动行为：
  - 若未显式提供 --root，则从当前脚本向上搜索同时存在 '抽取' 与 '指标统计计算' 目录的父级作为实验根。
  - 自动发现模型：扫描 抽取/数据结果 下符合 提取结果_by_* 且含 in_scope 的目录。
  - 未指定 --model/--all 且未给 --models 时，默认统计全部发现的模型并输出 CSV。

新增参数：
  --root <dir>         手动指定实验根
  --models a,b,c       批量指定模型（覆盖自动发现）
  --out-dir <dir>      自定义输出根目录（内部仍建 图像 / 表格）

兼容参数：
  --model / --all / --csv / --use-paper-stems 等保留。
"""


def auto_detect_root(script_path: Path) -> Path:
    for p in [script_path] + list(script_path.parents):
        if (p / '抽取').is_dir() and (p / '抽取' / '数据结果').is_dir():
            return p
    raise SystemExit('[ERROR] 未能自动找到实验根目录，请使用 --root 指定。')


def discover_models(data_base: Path) -> Dict[str, Path]:
    mapping: Dict[str, Path] = {}
    if not data_base.exists():
        return mapping
    for d in data_base.glob('提取结果_by_*'):
        if not d.is_dir():
            continue
        model = d.name.replace('提取结果_by_', '', 1)
        in_scope = d / 'in_scope'
        if in_scope.is_dir():
            mapping[model] = in_scope
    return mapping


def ensure_output_dirs(root: Path, custom_out: Path | None) -> Tuple[Path, Path]:
    if custom_out is None:
        base_stat_dir = root / '指标统计计算' / '指标一：实体关系数量' / '统计结果'
    else:
        base_stat_dir = custom_out
    out_img = base_stat_dir / '图像'
    out_tbl = base_stat_dir / '表格'
    out_img.mkdir(parents=True, exist_ok=True)
    out_tbl.mkdir(parents=True, exist_ok=True)
    return out_img, out_tbl

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

def plot_bar(model: str, stats, out_img_dir: Path, title_suffix: str):
    (ent_count, ent_type_count, rel_count, rel_type_count) = stats
    labels = ['实体数量', '实体类型数量', '关系数量', '关系类型数量']
    values = [ent_count, ent_type_count, rel_count, rel_type_count]
    colors = [COLOR_ENTITY_COUNT, COLOR_ENTITY_TYPES, COLOR_REL_COUNT, COLOR_REL_TYPES]

    plt.figure(figsize=(6,4), dpi=150)
    bars = plt.bar(labels, values, color=colors, edgecolor='#333333')
    for bar, val in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height(), str(val), ha='center', va='bottom', fontsize=9)
    plt.title(f'{model} 模型实体/关系抽取统计（{title_suffix}）', fontsize=12)
    plt.ylabel('数量')
    plt.tight_layout()
    out_path = out_img_dir / f'{model}_实体关系数量统计.png'
    plt.savefig(out_path, bbox_inches='tight')
    plt.close()
    print(f"{model} 图已保存: {out_path}")
    print(f"统计 => 实体数量:{ent_count} 实体类型:{ent_type_count} 关系数量:{rel_count} 关系类型:{rel_type_count}")

def main():
    parser = argparse.ArgumentParser(description='单模型或全部模型 实体/关系 数量与类型数量统计 (适配 EXP-1/2/3 通用结构)')
    parser.add_argument('--root', type=str, help='实验根目录 (含 抽取/指标统计计算)，默认自动检测')
    parser.add_argument('--models', type=str, help='逗号分隔模型名，覆盖自动发现')
    parser.add_argument('--model', type=str, help='单个模型名称 (与 --all 互斥)')
    parser.add_argument('--all', action='store_true', help='统计全部模型')
    parser.add_argument('--csv', action='store_true', help='输出一个汇总CSV')
    parser.add_argument('--out-dir', type=str, help='自定义输出根目录 (默认: 实验根/指标统计计算/指标一：实体关系数量/统计结果)')
    parser.add_argument('--use-paper-stems', action='store_true', help='仅统计评估目录(论文文献/需要评估的论文)列出的 50 篇')
    parser.add_argument('--only-correct', action='store_true', help='仅统计 evaluation 标记为 正确/correct 的关系')
    parser.add_argument('--only-correct-entities', action='store_true', help='仅统计 evaluation 标记为 正确/correct 的实体')
    parser.add_argument('--dedup-relations', action='store_true', help='关系按 (head, type, tail) 去重')
    parser.add_argument('--strict-correct', action='store_true', help='与 --only-correct 搭配：缺 evaluation 视为不正确 (默认保留)')
    parser.add_argument('--debug-relations', action='store_true', help='打印关系过滤调试信息')
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    root = Path(args.root) if args.root else auto_detect_root(script_path)
    data_base = root / '抽取' / '数据结果'
    eval_dir = root / '论文文献' / '需要评估的论文'

    model_map = discover_models(data_base)
    if not model_map:
        raise SystemExit(f'[ERROR] 未在 {data_base} 下发现任何 提取结果_by_* / in_scope 目录。')

    # 解析模型选择逻辑
    explicit_models: List[str] | None = None
    if args.models:
        explicit_models = [m.strip() for m in args.models.split(',') if m.strip()]
    targets: List[str]
    if explicit_models:
        targets = [m for m in explicit_models if m in model_map]
        missing = set(explicit_models) - set(targets)
        if missing:
            print(f'[WARN] 以下模型未发现且被忽略: {",".join(sorted(missing))}')
    elif args.model:
        if args.model not in model_map:
            raise SystemExit(f'[ERROR] 指定模型 {args.model} 不存在于自动发现集合 {list(model_map.keys())}')
        targets = [args.model]
    else:
        # 默认或 --all 统计全部
        targets = sorted(model_map.keys())
        if not args.model and not args.all and not args.models:
            print('[INFO] 未指定模型参数，默认统计全部模型并输出 CSV。')
            args.csv = True

    # 输出目录
    out_img_dir, out_table_dir = ensure_output_dirs(root, Path(args.out_dir) if args.out_dir else None)

    # 让 _iter_target_json_files 可访问到动态变量
    global MODEL_DIR_MAP, EVAL_PAPERS_DIR
    MODEL_DIR_MAP = {m: model_map[m] for m in targets}  # type: ignore
    EVAL_PAPERS_DIR = eval_dir  # type: ignore

    set_chinese_font()
    title_suffix = '限定50篇' if args.use_paper_stems else '全部文件'
    results = []
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
        plot_bar(m, stats, out_img_dir, title_suffix)
        results.append((m, *stats))

    if args.csv:
        csv_path = out_table_dir / '模型实体关系统计汇总.csv'
        with csv_path.open('w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['模型','实体数量','实体类型数量','关系数量','关系类型数量'])
            for row in results:
                w.writerow(row)
        print('[INFO] 汇总CSV已生成:', csv_path)
    print('[DONE] 处理完成。')

if __name__ == '__main__':
    main()
