"""定位 Kimi 打分结果目录中造成 raw 计数 1253 但唯一签名 1252 的重复实体。

背景：
1. 对比脚本(去重后) 显示 抽取 与 打分 唯一实体数均为 1252。
2. 正确率统计脚本统计的 entity_total = 1253（raw 列表长度）。
3. 说明在打分结果某个 JSON 中存在 1 条实体记录重复（文本 + 类型 同一签名出现 2 次）。

本脚本：
 - 遍历 指标统计计算/指标三：模型打分/打分结果/kimi 下所有 .json
 - 计算每文件 raw 数、唯一数、重复条目列表
 - 汇总全局重复签名与出现位置
 - 输出到 结果/ 目录一个报告 txt 和 csv

使用：
  python 定位_kimi打分结果内部重复实体.py

输出：
  结果/kimi_打分结果_内部重复实体报告.txt
  结果/kimi_打分结果_内部重复实体明细.csv
"""
from __future__ import annotations
import json, csv, sys
from pathlib import Path
from collections import defaultdict

def norm_text(t: str) -> str:
    return t.strip().lower()

def main():
    script_dir = Path(__file__).resolve().parent
    # 根 -> EXP-1  (code -> 差异性 -> 指标统计计算 -> EXP-1)
    # parents[0]=差异性, parents[1]=指标统计计算, parents[2]=EXP-1
    root_dir = script_dir.parents[2]
    score_dir = root_dir / '指标统计计算' / '指标三：模型打分' / '打分结果' / 'kimi'
    if not score_dir.exists():
        print(f'[ERROR] 未找到目录: {score_dir}')
        sys.exit(1)

    out_dir = script_dir.parent / '结果'
    out_dir.mkdir(parents=True, exist_ok=True)
    report_txt = out_dir / 'kimi_打分结果_内部重复实体报告.txt'
    detail_csv = out_dir / 'kimi_打分结果_内部重复实体明细.csv'

    total_raw = 0
    total_unique = 0
    file_stats = []  # (file, raw, unique, dup_count)
    dup_records = []  # rows for csv
    global_sig_files = defaultdict(list)  # sig -> list[(file, indices)]

    json_files = sorted([p for p in score_dir.glob('*.json')])
    for jf in json_files:
        try:
            data = json.loads(jf.read_text(encoding='utf-8'))
        except Exception as e:
            print('[WARN] 读取失败', jf, e)
            continue
        ents = data.get('entities') or []
        total_raw += len(ents)
        sig_to_indices = defaultdict(list)
        for idx, ent in enumerate(ents):
            t = ent.get('text') or ''
            tp = ent.get('type') or ''
            sig = (norm_text(t), tp)
            sig_to_indices[sig].append(idx)
        unique_count = len(sig_to_indices)
        total_unique += unique_count
        dup_sigs = {sig: idxs for sig, idxs in sig_to_indices.items() if len(idxs) > 1}
        file_stats.append((jf.name, len(ents), unique_count, len(dup_sigs)))
        for sig, idxs in dup_sigs.items():
            text_norm, tp = sig
            dup_records.append([jf.name, tp, text_norm, len(idxs), ';'.join(map(str, idxs))])
            global_sig_files[sig].append((jf.name, idxs))

    # 汇总重复签名数
    total_dup_sig = len({sig for sig, occ in global_sig_files.items()})
    total_dup_instances = sum(len(idxs) - 1 for _, occ in global_sig_files.items() for _, idxs in occ)

    # 写文本报告
    with report_txt.open('w', encoding='utf-8') as f:
        f.write(f'文件数: {len(json_files)}\n')
        f.write(f'Raw 实体总数: {total_raw}\n')
        f.write(f'唯一签名实体总数: {sum(len({(norm_text(e.get("text","")), e.get("type","")) for e in (json.loads(p.read_text(encoding="utf-8")).get("entities") or [])}) for p in json_files)}\n')
        f.write(f'（注：上行重新独立计算，避免累加误差）\n')
        f.write(f'文件级去重后求和(逐文件 unique 累加) : {total_unique}\n')
        f.write(f'包含重复实体的文件数: {sum(1 for _,_,_,dc in file_stats if dc>0)}\n')
        f.write(f'重复签名数量(全局) : {total_dup_sig}\n')
        f.write(f'多余实例数(重复造成的额外条目) : {total_dup_instances}\n')
        if total_dup_instances == 1:
            f.write('=> 这 1 条多余实例解释了 “1253 vs 1252” 的差异。\n')
        f.write('\n逐文件统计: file, raw, unique, dup_sig_count\n')
        for row in file_stats:
            f.write(','.join(map(str,row))+'\n')

    # 写明细 CSV
    with detail_csv.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['文件','类型','文本(归一)','重复出现次数','索引列表'])
        for r in dup_records:
            w.writerow(r)

    print('[INFO] 报告写出:', report_txt)
    print('[INFO] 明细写出:', detail_csv)
    if not dup_records:
        print('[INFO] 未发现任何重复实体。若仍存在 1253 vs 1252 差异，需检查统计脚本逻辑。')

if __name__ == '__main__':
    main()
