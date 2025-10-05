import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Union
import csv
import shutil

"""
清理已有元数据脚本
---------------------------------
目的: 在执行元数据填充(augment)前，先删除 LLM 抽取结果中不应出现的元数据型实体与关系，确保后续注入统一、无重复。

清理范围:
  实体类型(兼容多种写法):
    - 论文, 题名, Title, 文章, 文献
    - 作者, Author
    - 发表单位, 机构, 单位, 组织, 机构单位
    - 发表时间, 出版时间, 出版日期, 年份
  关系类型:
    - 撰写, 作者-论文, wrote, 写作
    - 隶属, 属于, 从属, 隶属于, affiliation
    - 发表于, 发表, 出版于, published_in, published_at

支持两种 JSON 结构:
  1) dict 顶层: { entities:[...], relations:[...] }
  2) list 顶层且第一个元素为 dict (早期批量格式)

输出:
  - 一个 CSV (默认: 清理元数据_变更明细.csv) 记录被删除的实体与关系。
  - 控制台统计汇总。

列说明:
  model, file, kind(entity|relation), type, text(实体文本或关系.head), tail(仅关系), note

可选功能:
  --dry-run 仅统计将删除的项, 不写回
  --backup  每个被修改的 JSON 生成同名 .bak (UTF-8) 备份
  --models  指定模型 (默认 deepseek,gemini,kimi)
  --data-base 指定 数据结果 根目录 (自动推断: 当前脚本 ../../ 数据结果)
  --output-csv 指定输出 CSV 完整路径
  --limit 每模型最多处理文件数 (调试用)

使用示例:
  python 清理已有元数据.py --dry-run
  python 清理已有元数据.py --models gemini --backup
  python 清理已有元数据.py --output-csv E:/temp/clean_report.csv
"""

# ---------------- 配置集合 -----------------
ENTITY_TYPE_ALIASES = {
    '论文','题名','title','文章','文献',
    '作者','author',
    '发表单位','机构','单位','组织','机构单位',
    '发表时间','出版时间','出版日期','年份'
}

# 归一化后做匹配 (全部转小写)
ENTITY_TYPES_NORMALIZED = {t.lower() for t in ENTITY_TYPE_ALIASES}

REL_TYPE_ALIASES = {
    '撰写','作者-论文','wrote','写作',
    '隶属','属于','从属','隶属于','affiliation',
    '发表于','发表','出版于','published_in','published_at'
}
REL_TYPES_NORMALIZED = {t.lower() for t in REL_TYPE_ALIASES}

DEFAULT_MODELS = ['deepseek','gemini','kimi']

# ----------------- 工具函数 -----------------

def normalize(s: str) -> str:
    return (s or '').strip().lower()


def load_json_file(path: Path):
    try:
        txt = path.read_text(encoding='utf-8')
        return json.loads(txt)
    except Exception as e:
        print(f"[WARN] 读取失败 {path.name}: {e}")
        return None


def detect_container(obj) -> Union[Dict, List, None]:
    """返回 (item, container) 其中 item 是含 entities/relations 的 dict。"""
    if isinstance(obj, dict):
        return obj, obj
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        return obj[0], obj
    return None


def filter_entities(entities: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    removed = []
    kept = []
    for e in entities:
        ety = normalize(e.get('type',''))
        if ety in ENTITY_TYPES_NORMALIZED:
            removed.append(e)
        else:
            kept.append(e)
    return kept, removed


def filter_relations(relations: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    removed = []
    kept = []
    for r in relations:
        rty = normalize(r.get('type',''))
        if rty in REL_TYPES_NORMALIZED:
            removed.append(r)
        else:
            kept.append(r)
    return kept, removed


def process_file(json_path: Path, model: str, dry_run: bool, backup: bool):
    obj = load_json_file(json_path)
    if obj is None:
        return [], []  # (removed_entities, removed_relations)
    detected = detect_container(obj)
    if not detected:
        print(f"[WARN] 不支持结构 {json_path.name}")
        return [], []
    item, container = detected
    entities = item.get('entities') or []
    relations = item.get('relations') or []
    if not isinstance(entities, list) or not isinstance(relations, list):
        return [], []

    kept_e, removed_e = filter_entities(entities)
    kept_r, removed_r = filter_relations(relations)

    if (removed_e or removed_r) and not dry_run:
        if backup:
            try:
                shutil.copyfile(json_path, json_path.with_suffix(json_path.suffix + '.bak'))
            except Exception as e:
                print(f"[WARN] 备份失败 {json_path.name}: {e}")
        item['entities'] = kept_e
        item['relations'] = kept_r
        try:
            json_path.write_text(json.dumps(container, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception as e:
            print(f"[ERROR] 写回失败 {json_path.name}: {e}")
    return removed_e, removed_r


# ----------------- 主逻辑 -----------------

def main():
    parser = argparse.ArgumentParser(description='清理抽取结果中已有的元数据实体与关系')
    parser.add_argument('--models', default=','.join(DEFAULT_MODELS), help='模型列表，逗号分隔; 默认 deepseek,gemini,kimi')
    parser.add_argument('--data-base', type=str, default=None, help='数据结果根目录 (含 提取结果_by_xxx/in_scope)')
    parser.add_argument('--dry-run', action='store_true', help='仅统计，不写回')
    parser.add_argument('--backup', action='store_true', help='写回前为每个修改文件创建 .json.bak 备份')
    parser.add_argument('--output-csv', type=str, default=None, help='保存变更明细 CSV 路径')
    parser.add_argument('--limit', type=int, default=0, help='每模型最多处理文件数 (0=不限)')

    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    # 自动向上查找：优先选择其下存在 提取结果_by_gemini 的 数据结果 目录
    candidate_roots = []
    for p in [script_dir] + list(script_dir.parents):
        data_dir = p / '数据结果'
        if data_dir.is_dir():
            score = 0
            # 典型抽取结果子目录判定
            if (data_dir / '提取结果_by_gemini' / 'in_scope').is_dir():
                score += 10
            if (data_dir / '提取结果_by_deepseek').is_dir():
                score += 5
            if (data_dir / '提取结果_by_kimi').is_dir():
                score += 5
            candidate_roots.append((score, p))
    candidate_roots.sort(key=lambda x: x[0], reverse=True)
    extract_root = candidate_roots[0][1] if candidate_roots else None
    if extract_root is None:
        print('[ERROR] 未能找到包含 数据结果 的根目录，请使用 --data-base 指定。')
        return
    default_data_base = extract_root / '数据结果'
    print(f'[INFO] 选择数据结果根目录: {default_data_base}')
    data_base = Path(args.data_base) if args.data_base else default_data_base

    models = [m.strip() for m in args.models.split(',') if m.strip()]
    if not models:
        print('[ERROR] 未提供模型列表')
        return

    if not data_base.exists():
        print(f'[ERROR] 数据结果根目录不存在: {data_base}')
        return

    # 输出 CSV
    if args.output_csv:
        out_csv = Path(args.output_csv)
    else:
        out_csv = extract_root / '数据结果' / '清理元数据_变更明细.csv'
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    rows = []  # 收集所有删除记录
    summary = []  # 汇总统计

    for model in models:
        in_scope_dir = data_base / f'提取结果_by_{model}' / 'in_scope'
        if not in_scope_dir.exists():
            print(f'[WARN] 模型目录不存在: {in_scope_dir}')
            continue
        files = sorted(in_scope_dir.glob('*.json'))
        if args.limit > 0:
            files = files[: args.limit]
        removed_e_total = removed_r_total = 0
        for jf in files:
            removed_e, removed_r = process_file(jf, model, args.dry_run, args.backup)
            if removed_e:
                for e in removed_e:
                    rows.append({
                        'model': model,
                        'file': jf.name,
                        'kind': 'entity',
                        'type': e.get('type',''),
                        'text': e.get('text',''),
                        'tail': '',
                        'note': ''
                    })
                removed_e_total += len(removed_e)
            if removed_r:
                for r in removed_r:
                    rows.append({
                        'model': model,
                        'file': jf.name,
                        'kind': 'relation',
                        'type': r.get('type',''),
                        'text': r.get('head',''),
                        'tail': r.get('tail',''),
                        'note': ''
                    })
                removed_r_total += len(removed_r)
        summary.append((model, len(files), removed_e_total, removed_r_total))
        print(f"[模型 {model}] 文件数={len(files)} 删除实体={removed_e_total} 删除关系={removed_r_total}")

    # 写 CSV
    with out_csv.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['model','file','kind','type','text','tail','note'])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print(f'[INFO] 明细已写入: {out_csv} (删除记录 {len(rows)} 条)')

    # 打印汇总表
    if summary:
        print('\n=== 汇总 ===')
        print('模型\t文件数\t删实体\t删关系')
        for m, fc, de, dr in summary:
            print(f'{m}\t{fc}\t{de}\t{dr}')
    else:
        print('[INFO] 无任何模型被处理或无删除。')

    if args.dry_run:
        print('\n[提示] 运行了 --dry-run，没有实际写回。')

if __name__ == '__main__':
    main()
