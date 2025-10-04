# -*- coding: utf-8 -*-
"""清除 指标三：模型打分/打分结果 中残留的元数据实体/关系

目标: 与增补前清理脚本口径一致, 删除以下类型, 以便后续统计(正确率/混淆等)不被规则注入元数据干扰。
  实体 type ∈ {论文, 作者, 发表单位, 发表时间}
  关系 type ∈ {撰写, 隶属, 发表于}

作用范围:
  ROOT/指标统计计算/指标三：模型打分/打分结果/<model>/*.json

特性:
  --models deepseek,gemini,kimi   指定模型(逗号分隔)
  --dry-run                       只统计不写回
  --backup                        写回前备份到 当前 model 目录下 __backup_meta_clean/
  --keep-title                    不删除 type=论文 实体
  --verbose                       输出逐文件删除详情

输出:
  汇总 CSV: 指标统计计算/指标三：模型打分/统计结果/打分结果_元数据清除汇总.csv
  明细 CSV: 指标统计计算/指标三：模型打分/统计结果/打分结果_删除实体明细_<model>.csv
            指标统计计算/指标三：模型打分/统计结果/打分结果_删除关系明细_<model>.csv

幂等: 重复执行第二次会删除数量=0。
"""
from __future__ import annotations
import argparse, json, csv, shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(r"e:\知识图谱构建\9.15之前的实验\EXP-1")
SCORED_BASE = ROOT / '指标统计计算' / '指标三：模型打分' / '打分结果'
OUT_BASE = ROOT / '指标统计计算' / '指标三：模型打分' / '统计结果'
OUT_BASE.mkdir(parents=True, exist_ok=True)

META_ENTITY_TYPES = {"论文","作者","发表单位","发表时间"}
META_REL_TYPES = {"撰写","隶属","发表于"}

def load_structure(p: Path):
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return None, None
    if isinstance(data, dict):
        return data, data
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data, data[0]
    return None, None

def save_structure(p: Path, root):
    p.write_text(json.dumps(root, ensure_ascii=False, indent=2), encoding='utf-8')

def clean_one(path: Path, keep_title: bool):
    root, item = load_structure(path)
    if root is None:
        return {"skip":1}
    ents = item.get('entities') or []
    rels = item.get('relations') or []
    if not isinstance(ents, list) or not isinstance(rels, list):
        return {"skip":1}
    removed_e = 0; removed_r = 0
    rem_ent_detail = []; rem_rel_detail = []
    id_index = {}
    for e in ents:
        eid = e.get('id') or e.get('entity_id')
        if eid is not None: id_index[eid]=e
    new_entities = []
    for e in ents:
        et = e.get('type')
        if isinstance(et,str) and et in META_ENTITY_TYPES:
            if keep_title and et=='论文':
                new_entities.append(e)
            else:
                removed_e += 1
                rem_ent_detail.append([
                    path.name,
                    e.get('id') or e.get('entity_id'),
                    e.get('text') or e.get('name') or '',
                    et,
                    e.get('evaluation',''),
                ])
        else:
            new_entities.append(e)
    new_relations = []
    for r in rels:
        rt = r.get('type') or r.get('relation')
        if isinstance(rt,str) and rt in META_REL_TYPES:
            removed_r += 1
            h = r.get('head') or r.get('from'); t = r.get('tail') or r.get('to')
            head_ent = id_index.get(h,{}) if h is not None else {}
            tail_ent = id_index.get(t,{}) if t is not None else {}
            rem_rel_detail.append([
                path.name,
                r.get('id') or r.get('relation_id'), rt,
                h, head_ent.get('text') or head_ent.get('name') or '', head_ent.get('type') or '',
                t, tail_ent.get('text') or tail_ent.get('name') or '', tail_ent.get('type') or '',
                r.get('evaluation','')
            ])
        else:
            new_relations.append(r)
    changed = removed_e>0 or removed_r>0
    return {
        'skip':0,'changed':changed,
        'removed_entities':removed_e,'removed_relations':removed_r,
        'new_entities':new_entities,'new_relations':new_relations,
        'root':root,'item':item,
        'removed_entities_detail': rem_ent_detail,
        'removed_relations_detail': rem_rel_detail,
    }

def process_model(model: str, args):
    mdir = SCORED_BASE / model
    if not mdir.exists():
        print(f"[WARN] 模型目录不存在: {mdir}"); return None
    files = sorted(mdir.glob('*.json'))
    backup_dir = None
    if args.backup:
        backup_dir = mdir / '__backup_meta_clean'
        backup_dir.mkdir(parents=True, exist_ok=True)

    removed_e_total = removed_r_total = 0
    changed_files = 0
    ent_rows: List[List[Any]] = []
    rel_rows: List[List[Any]] = []

    for f in files:
        stat = clean_one(f, keep_title=args.keep_title)
        if stat['skip']:
            continue
        if stat['changed']:
            removed_e_total += stat['removed_entities']
            removed_r_total += stat['removed_relations']
            changed_files += 1
            if args.verbose:
                print(f"[{model}] {f.name} - rmE:{stat['removed_entities']} rmR:{stat['removed_relations']}")
            ent_rows.extend(stat['removed_entities_detail'])
            rel_rows.extend(stat['removed_relations_detail'])
            if not args.dry_run:
                if backup_dir is not None:
                    shutil.copy2(f, backup_dir / f.name)
                item = stat['item']
                item['entities'] = stat['new_entities']
                item['relations'] = stat['new_relations']
                save_structure(f, stat['root'])
    # 写明细
    if ent_rows:
        ent_csv = OUT_BASE / f'打分结果_删除实体明细_{model}.csv'
        with ent_csv.open('w', newline='', encoding='utf-8-sig') as fw:
            w = csv.writer(fw)
            w.writerow(['文件','实体ID','文本','类型','evaluation'])
            w.writerows(ent_rows)
    if rel_rows:
        rel_csv = OUT_BASE / f'打分结果_删除关系明细_{model}.csv'
        with rel_csv.open('w', newline='', encoding='utf-8-sig') as fw:
            w = csv.writer(fw)
            w.writerow(['文件','关系ID','类型','head','head_text','head_type','tail','tail_text','tail_type','evaluation'])
            w.writerows(rel_rows)
    return {
        'model': model,
        'files': len(files),
        'changed_files': changed_files,
        'removed_entities': removed_e_total,
        'removed_relations': removed_r_total,
    }

def main():
    ap = argparse.ArgumentParser(description='清除打分结果中元数据实体与关系')
    ap.add_argument('--models', default='deepseek,gemini,kimi', help='模型列表')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--backup', action='store_true')
    ap.add_argument('--keep-title', action='store_true')
    ap.add_argument('--verbose', action='store_true')
    args = ap.parse_args()

    models = [m.strip() for m in args.models.split(',') if m.strip()]
    summary_rows = []
    for m in models:
        res = process_model(m, args)
        if res:
            summary_rows.append([res['model'], res['files'], res['changed_files'], res['removed_entities'], res['removed_relations']])
            print(f"[SUMMARY][{m}] files={res['files']} changed={res['changed_files']} rmE={res['removed_entities']} rmR={res['removed_relations']}")
    if summary_rows:
        out_csv = OUT_BASE / '打分结果_元数据清除汇总.csv'
        with out_csv.open('w', newline='', encoding='utf-8-sig') as fw:
            w = csv.writer(fw)
            w.writerow(['模型','文件数','修改文件数','删除实体数','删除关系数'])
            for r in summary_rows:
                w.writerow(r)
        print('[INFO] 汇总写出:', out_csv)
    if args.dry_run:
        print('[NOTE] dry-run 模式未修改文件。')

if __name__ == '__main__':
    main()
