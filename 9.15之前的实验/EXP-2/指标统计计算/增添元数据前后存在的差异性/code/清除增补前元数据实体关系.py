# -*- coding: utf-8 -*-
"""清除“增补前”数据中已出现的元数据实体 / 关系

目的：
  确保后续统计中，作者 / 论文题名 / 发表单位 / 发表时间 以及其派生关系(撰写/隶属/发表于)
  全部来自统一规则补充，而不是模型原始抽取结果里偶然出现的内容。

作用范围：
  E:/知识图谱构建/9.15之前的实验/EXP-1/抽取/数据结果/增补前/提取结果_by_<model>/in_scope/*.json

删除对象：
  实体 type ∈ {论文, 作者, 发表单位, 发表时间}
  关系 type ∈ {撰写, 隶属, 发表于}

JSON 结构兼容：
  1) 顶层 dict 形式： {"entities": [...], "relations": [...]}
  2) 顶层 list，其中首个元素为 dict： [ {"entities": [...], "relations": [...]} , ...]

提供特性：
  --dry-run        仅统计将要删除的数量，不写回
  --backup         开启时，将原文件复制到指定备份目录(默认: 同级 __backup_meta_clean/<model>/)
  --models         处理模型列表，默认 deepseek,gemini,kimi
  --keep-title     保留 type=论文 的实体（若有需要对题名保留，可加此参数）
  --verbose        打印每个文件的删除统计

输出：
  汇总 CSV: 指标统计计算/增添元数据前后存在的差异性/结果/增补前元数据清除汇总.csv
  （包含：模型、文件数、修改文件数、删除实体数、删除关系数、剩余实体数、剩余关系数）

使用示例：
  python 清除增补前元数据实体关系.py --dry-run
  python 清除增补前元数据实体关系.py --backup
  python 清除增补前元数据实体关系.py --models gemini --keep-title
"""
from __future__ import annotations
import argparse
import csv
import json
import shutil
from pathlib import Path
from typing import Tuple, List, Dict, Any

ROOT = Path(r"e:\知识图谱构建\9.15之前的实验\EXP-1")
PRE_BASE = ROOT / '抽取' / '数据结果' / '增补前'
OUT_REPORT_DIR = ROOT / '指标统计计算' / '增添元数据前后存在的差异性' / '结果'
OUT_REPORT_DIR.mkdir(parents=True, exist_ok=True)

META_ENTITY_TYPES = {"论文", "作者", "发表单位", "发表时间"}
META_REL_TYPES = {"撰写", "隶属", "发表于"}


def load_structure(path: Path) -> Tuple[Any, Dict[str, Any]]:
    """返回 (root_obj, item_dict)
    root_obj: 原始 JSON 顶层对象 (dict 或 list)
    item_dict: 实际包含 entities/relations 的 dict (可能是 root 或 root[0])
    若结构不支持，返回 (None, {})
    """
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None, {}
    if isinstance(data, dict):
        return data, data
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data, data[0]
    return None, {}


def save_structure(path: Path, root_obj: Any):
    path.write_text(json.dumps(root_obj, ensure_ascii=False, indent=2), encoding='utf-8')


def clean_one(path: Path, keep_title: bool) -> Dict[str, Any]:
    root, item = load_structure(path)
    if root is None:
        return {"skip": 1, "removed_entities": 0, "removed_relations": 0, "remain_entities": 0, "remain_relations": 0}

    ents = item.get('entities') or []
    rels = item.get('relations') or []
    if not isinstance(ents, list) or not isinstance(rels, list):
        return {"skip": 1, "removed_entities": 0, "removed_relations": 0, "remain_entities": 0, "remain_relations": 0}

    removed_e = 0
    removed_r = 0
    removed_entities_detail: List[Dict[str, Any]] = []
    removed_relations_detail: List[Dict[str, Any]] = []

    # 建立实体 id 索引，便于关系详情补充
    id_index: Dict[Any, Dict[str, Any]] = {}
    for e in ents:
        eid = e.get('id') or e.get('entity_id')
        if eid is not None:
            id_index[eid] = e

    # 过滤实体
    new_entities = []
    for e in ents:
        et = e.get('type')
        if isinstance(et, str) and et in META_ENTITY_TYPES:
            if keep_title and et == '论文':
                new_entities.append(e)
            else:
                removed_e += 1
                removed_entities_detail.append({
                    'id': e.get('id') or e.get('entity_id'),
                    'text': e.get('text') or e.get('name') or '',
                    'type': et,
                })
        else:
            new_entities.append(e)

    # 过滤关系
    new_relations = []
    for r in rels:
        rt = r.get('type') or r.get('relation')
        if isinstance(rt, str) and rt in META_REL_TYPES:
            removed_r += 1
            head_id = r.get('head') or r.get('from')
            tail_id = r.get('tail') or r.get('to')
            head_ent = id_index.get(head_id, {}) if head_id is not None else {}
            tail_ent = id_index.get(tail_id, {}) if tail_id is not None else {}
            removed_relations_detail.append({
                'id': r.get('id') or r.get('relation_id'),
                'type': rt,
                'head': head_id,
                'head_text': head_ent.get('text') or head_ent.get('name') or '',
                'head_type': head_ent.get('type') or '',
                'tail': tail_id,
                'tail_text': tail_ent.get('text') or tail_ent.get('name') or '',
                'tail_type': tail_ent.get('type') or '',
            })
        else:
            new_relations.append(r)

    changed = (removed_e > 0 or removed_r > 0)
    return {
        "skip": 0,
        "removed_entities": removed_e,
        "removed_relations": removed_r,
        "remain_entities": len(new_entities),
        "remain_relations": len(new_relations),
        "changed": int(changed),
        "_new_entities": new_entities,
        "_new_relations": new_relations,
        "_root": root,
        "_item": item,
        "removed_entities_detail": removed_entities_detail,
        "removed_relations_detail": removed_relations_detail,
    }


def process_model(model: str, args) -> Dict[str, int]:
    mdir = PRE_BASE / f'提取结果_by_{model}' / 'in_scope'
    if not mdir.exists():
        print(f"[WARN] 模型 {model} 目录不存在: {mdir}")
        return {"files":0,"changed_files":0,"removed_entities":0,"removed_relations":0,"remain_entities":0,"remain_relations":0}
    files = sorted(mdir.glob('*.json'))
    changed_files = 0
    total_removed_e = 0
    total_removed_r = 0
    remain_e = 0
    remain_r = 0

    # 备份目录
    backup_dir = None
    if args.backup:
        backup_dir = mdir.parent / '__backup_meta_clean' / 'in_scope'
        backup_dir.mkdir(parents=True, exist_ok=True)

    # 详情收集
    removed_entities_rows: List[List[Any]] = []
    removed_relations_rows: List[List[Any]] = []

    for f in files:
        stats = clean_one(f, keep_title=args.keep_title)
        if stats.get('skip'):
            continue
        total_removed_e += stats['removed_entities']
        total_removed_r += stats['removed_relations']
        remain_e = stats['remain_entities']  # 最后一次覆盖（不用于总和）
        remain_r = stats['remain_relations']
        if stats['changed']:
            changed_files += 1
            if args.verbose:
                print(f"[MODEL={model}] {f.name} - removed E:{stats['removed_entities']} R:{stats['removed_relations']}")
            # 记录详情（即使 dry-run 也记录“将删除”内容）
            for de in stats['removed_entities_detail']:
                removed_entities_rows.append([
                    f.name,
                    de.get('id'),
                    de.get('text'),
                    de.get('type'),
                ])
            for dr in stats['removed_relations_detail']:
                removed_relations_rows.append([
                    f.name,
                    dr.get('id'),
                    dr.get('type'),
                    dr.get('head'),
                    dr.get('head_text'),
                    dr.get('head_type'),
                    dr.get('tail'),
                    dr.get('tail_text'),
                    dr.get('tail_type'),
                ])
            if not args.dry_run:
                # 备份
                if backup_dir is not None:
                    shutil.copy2(f, backup_dir / f.name)
                # 写回
                item = stats['_item']
                item['entities'] = stats['_new_entities']
                item['relations'] = stats['_new_relations']
                save_structure(f, stats['_root'])

    # 写出详情 CSV（即使 dry-run 也写）
    if removed_entities_rows:
        detail_ent_csv = OUT_REPORT_DIR / f'增补前元数据清除_删除实体明细_{model}.csv'
        with detail_ent_csv.open('w', newline='', encoding='utf-8-sig') as fcsv:
            w = csv.writer(fcsv)
            w.writerow(['文件','实体ID','文本','类型'])
            w.writerows(removed_entities_rows)
        if args.verbose:
            print(f'[DETAIL] 实体明细写出: {detail_ent_csv}')
    if removed_relations_rows:
        detail_rel_csv = OUT_REPORT_DIR / f'增补前元数据清除_删除关系明细_{model}.csv'
        with detail_rel_csv.open('w', newline='', encoding='utf-8-sig') as fcsv:
            w = csv.writer(fcsv)
            w.writerow(['文件','关系ID','类型','head','head_text','head_type','tail','tail_text','tail_type'])
            w.writerows(removed_relations_rows)
        if args.verbose:
            print(f'[DETAIL] 关系明细写出: {detail_rel_csv}')
    return {
        "files": len(files),
        "changed_files": changed_files,
        "removed_entities": total_removed_e,
        "removed_relations": total_removed_r,
        "remain_entities": remain_e,
        "remain_relations": remain_r,
    }


def write_summary(rows: List[List[Any]]):
    out_csv = OUT_REPORT_DIR / '增补前元数据清除汇总.csv'
    with out_csv.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['模型','文件数','修改文件数','删除实体数','删除关系数'])
        for r in rows:
            w.writerow(r)
    print('[INFO] 汇总写出:', out_csv)


def main():
    parser = argparse.ArgumentParser(description='清除增补前数据中的元数据实体与关系')
    parser.add_argument('--models', default='deepseek,gemini,kimi', help='模型列表,逗号分隔')
    parser.add_argument('--dry-run', action='store_true', help='仅显示将删除数量，不写回')
    parser.add_argument('--backup', action='store_true', help='写回前备份原 JSON 到 __backup_meta_clean')
    parser.add_argument('--keep-title', action='store_true', help='保留 type=论文 的实体')
    parser.add_argument('--verbose', action='store_true', help='逐文件输出删除详情')
    args = parser.parse_args()

    models = [m.strip() for m in args.models.split(',') if m.strip()]
    summary_rows = []

    for model in models:
        result = process_model(model, args)
        summary_rows.append([
            model,
            result['files'],
            result['changed_files'],
            result['removed_entities'],
            result['removed_relations'],
        ])
        print(f"[SUMMARY][{model}] files={result['files']} changed={result['changed_files']} removedE={result['removed_entities']} removedR={result['removed_relations']}")
    write_summary(summary_rows)
    if args.dry_run:
        print('[NOTE] dry-run 模式未对任何文件做修改。')

if __name__ == '__main__':
    main()
