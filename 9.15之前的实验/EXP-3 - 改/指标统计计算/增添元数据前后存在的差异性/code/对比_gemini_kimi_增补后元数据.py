"""对比 增补后 gemini 与 kimi 两模型在 50 篇文件上的元数据(实体+关系)一致性。

元数据实体类型: 论文 / 作者 / 发表单位 / 发表时间
元数据关系类型: 撰写 / 隶属 / 发表于

输出 (到 本目录上级 结果/ ): 
  - 元数据实体对比_gemini_vs_kimi.csv
  - 元数据关系对比_gemini_vs_kimi.csv
  - 元数据对比汇总_gemini_vs_kimi.txt

判定：按文件同名(精确文件名匹配)。实体签名 = (text.lower().strip(), type)；
关系签名 = (head.lower().strip(), tail.lower().strip(), type)。

为每篇文件计算：
  每种实体类型的差异(缺失 / 多出)
  关系差异
并计算总体：完全一致文件数、存在差异文件数、Jaccard 等。
"""
from __future__ import annotations
import json, csv
from pathlib import Path
from typing import Dict, List, Tuple, Set

META_ENTITY_TYPES = {"论文", "作者", "发表单位", "发表时间"}
META_RELATION_TYPES = {"撰写", "隶属", "发表于"}

def norm(s: str) -> str:
    return s.strip().lower()

def load_json_entities_relations(p: Path):
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return [], []
    if isinstance(data, list) and data and isinstance(data[0], dict):
        item = data[0]
    elif isinstance(data, dict):
        item = data
    else:
        return [], []
    ents = item.get('entities') or []
    rels = item.get('relations') or []
    return ents, rels

def extract_meta_sets(p: Path):
    ents, rels = load_json_entities_relations(p)
    ent_set: Set[Tuple[str,str]] = set()
    rel_set: Set[Tuple[str,str,str]] = set()
    for e in ents:
        ty = str(e.get('type',''))
        if ty in META_ENTITY_TYPES:
            txt = str(e.get('text',''))
            if txt.strip():
                ent_set.add((norm(txt), ty))
    for r in rels:
        ty = str(r.get('type',''))
        if ty in META_RELATION_TYPES:
            h = str(r.get('head',''))
            t = str(r.get('tail',''))
            if h.strip() and t.strip():
                rel_set.add((norm(h), norm(t), ty))
    return ent_set, rel_set

def jaccard(a: Set, b: Set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b) if (a or b) else 1.0

def main():
    script_dir = Path(__file__).resolve().parent
    root = script_dir.parents[2]
    base_after = root / '抽取' / '数据结果' / '增补后'
    gem_dir = base_after / '提取结果_by_gemini' / 'in_scope'
    kimi_dir = base_after / '提取结果_by_kimi' / 'in_scope'
    if not gem_dir.exists() or not kimi_dir.exists():
        print('[ERROR] 目录不存在:', gem_dir, kimi_dir)
        return

    gem_files = {p.name: p for p in gem_dir.glob('*.json')}
    kimi_files = {p.name: p for p in kimi_dir.glob('*.json')}
    common = sorted(set(gem_files) & set(kimi_files))
    only_gem = sorted(set(gem_files) - set(kimi_files))
    only_kimi = sorted(set(kimi_files) - set(gem_files))

    out_dir = script_dir.parent / '结果'
    out_dir.mkdir(parents=True, exist_ok=True)
    ent_csv = out_dir / '元数据实体对比_gemini_vs_kimi.csv'
    rel_csv = out_dir / '元数据关系对比_gemini_vs_kimi.csv'
    summary_txt = out_dir / '元数据对比汇总_gemini_vs_kimi.txt'

    # 实体对比 CSV: 文件, 实体类型, gemini_count, kimi_count, gemini-缺失项, kimi-缺失项, 实体Jaccard
    with ent_csv.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['文件','类型','gemini数','kimi数','仅gemini有','仅kimi有','Jaccard'])
        entity_diff_files = 0
        total_entity_equal_files = 0
        total_entity_jacc_sum = 0.0
        per_file_entity_jacc: Dict[str, float] = {}

        # 为关系单独准备收集，在另一个表里写
        rel_rows: List[List[str]] = []
        relation_diff_files = 0
        total_rel_equal_files = 0
        total_rel_jacc_sum = 0.0
        per_file_rel_jacc: Dict[str, float] = {}

        for fname in common:
            g_ent_set, g_rel_set = extract_meta_sets(gem_files[fname])
            k_ent_set, k_rel_set = extract_meta_sets(kimi_files[fname])

            # 按实体类型细分
            types_present = META_ENTITY_TYPES
            file_all_equal = True
            for ty in sorted(types_present):
                g_ty = {e for e in g_ent_set if e[1]==ty}
                k_ty = {e for e in k_ent_set if e[1]==ty}
                only_g = sorted(txt for txt,_ in { (t,ty) for (t,ty) in g_ty } - { (t,ty) for (t,ty) in k_ty })
                only_k = sorted(txt for txt,_ in { (t,ty) for (t,ty) in k_ty } - { (t,ty) for (t,ty) in g_ty })
                j = jaccard(g_ty, k_ty)
                if only_g or only_k:
                    file_all_equal = False
                w.writerow([
                    fname, ty, len(g_ty), len(k_ty), ';'.join(only_g), ';'.join(only_k), f'{j:.4f}'
                ])
            # 文件整体实体 Jaccard（四类合并）
            file_j = jaccard(g_ent_set, k_ent_set)
            per_file_entity_jacc[fname] = file_j
            total_entity_jacc_sum += file_j
            if file_all_equal and file_j == 1.0:
                total_entity_equal_files += 1
            else:
                entity_diff_files += 1

            # 关系
            file_rel_all_equal = True
            # 分类型
            for rty in sorted(META_RELATION_TYPES):
                g_r = {r for r in g_rel_set if r[2]==rty}
                k_r = {r for r in k_rel_set if r[2]==rty}
                only_g_r = sorted(f'{h}->{t}' for (h,t,_) in g_r - k_r)
                only_k_r = sorted(f'{h}->{t}' for (h,t,_) in k_r - g_r)
                r_j = jaccard(g_r, k_r)
                if only_g_r or only_k_r:
                    file_rel_all_equal = False
                rel_rows.append([
                    fname, rty, len(g_r), len(k_r), ';'.join(only_g_r), ';'.join(only_k_r), f'{r_j:.4f}'
                ])
            file_rel_j = jaccard(g_rel_set, k_rel_set)
            per_file_rel_jacc[fname] = file_rel_j
            total_rel_jacc_sum += file_rel_j
            if file_rel_all_equal and file_rel_j == 1.0:
                total_rel_equal_files += 1
            else:
                relation_diff_files += 1

        # 写关系表
        with rel_csv.open('w', newline='', encoding='utf-8-sig') as rf:
            rw = csv.writer(rf)
            rw.writerow(['文件','关系类型','gemini数','kimi数','仅gemini有','仅kimi有','Jaccard'])
            for row in rel_rows:
                rw.writerow(row)

    # 汇总文本
    with summary_txt.open('w', encoding='utf-8') as s:
        s.write(f'文件总数(共同): {len(common)}\n')
        s.write(f'仅 gemini 存在文件数: {len(only_gem)}\n')
        s.write(f'仅 kimi 存在文件数: {len(only_kimi)}\n')
        def avg(d: Dict[str,float]):
            return sum(d.values())/len(d) if d else 1.0
        s.write(f'实体平均 Jaccard: {avg(per_file_entity_jacc):.4f}\n')
        s.write(f'关系平均 Jaccard: {avg(per_file_rel_jacc):.4f}\n')
        # 统计完全一致数
        ent_equal = sum(1 for v in per_file_entity_jacc.values() if v==1.0)
        rel_equal = sum(1 for v in per_file_rel_jacc.values() if v==1.0)
        both_equal = sum(1 for f in common if per_file_entity_jacc.get(f)==1.0 and per_file_rel_jacc.get(f)==1.0)
        s.write(f'实体完全一致文件数: {ent_equal}\n')
        s.write(f'关系完全一致文件数: {rel_equal}\n')
        s.write(f'实体+关系均完全一致文件数: {both_equal}\n')

    print('[INFO] 对比完成。汇总:', summary_txt)
    print('[INFO] 实体差异 CSV:', ent_csv)
    print('[INFO] 关系差异 CSV:', rel_csv)

if __name__ == '__main__':
    main()
