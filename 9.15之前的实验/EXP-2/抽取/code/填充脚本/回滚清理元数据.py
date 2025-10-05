import argparse
from pathlib import Path
import shutil
import csv
import json
from typing import List, Tuple

"""
回滚清理元数据脚本
--------------------
用途:
  将之前执行 清理已有元数据.py --backup 时生成的 *.json.bak 备份文件恢复成原始 *.json，
  即撤销删除的元数据实体/关系操作。

备份命名规则回顾:
  清理脚本对 file.json 写回前复制为 file.json.bak

本脚本操作:
  1. 自动向上查找包含 '数据结果' 的根目录 (或使用 --data-base 指定)
  2. 扫描各模型目录 提取结果_by_xxx/in_scope 下的 *.json.bak
  3. 将其内容复制覆盖同名 *.json
  4. 生成回滚明细 CSV: 恢复的文件、模型、大小信息

可选参数:
  --models deepseek,gemini,kimi  仅回滚指定模型 (默认全部存在模型)
  --data-base <dir>             指定 数据结果 根 (默认自动探测)
  --dry-run                     仅展示将回滚的文件数量，不执行复制
  --remove-bak                  回滚成功后删除 .bak 文件
  --output-csv <path>           指定回滚明细 CSV 输出路径
  --limit N                     每模型最多回滚前 N 个 (调试用)

安全性:
  - 若目标 *.json 不存在，仍执行覆盖 (等同恢复)
  - 若没有 .bak 文件，不做任何修改

示例:
  python 回滚清理元数据.py --dry-run
  python 回滚清理元数据.py --models gemini --remove-bak
"""

DEFAULT_MODELS = ['deepseek','gemini','kimi']


def detect_extract_root(script_dir: Path) -> Path | None:
    for p in [script_dir] + list(script_dir.parents):
        data_dir = p / '数据结果'
        if data_dir.is_dir():
            # 需要至少一个 提取结果_by_ 目录判定为抽取根
            has_any = any(data_dir.glob('提取结果_by_*'))
            if has_any:
                return p
    return None


def restore_file(bak_path: Path, dry_run: bool, remove_bak: bool) -> Tuple[bool, str]:
    target = bak_path.with_suffix('')  # 去掉 .bak
    try:
        if dry_run:
            return True, 'DRY-RUN'
        # 复制备份内容 -> 原文件
        shutil.copyfile(bak_path, target)
        if remove_bak:
            try:
                bak_path.unlink()
            except Exception:
                return True, 'RESTORED(keep bak: delete failed)'
        return True, 'RESTORED'
    except Exception as e:
        return False, f'ERROR: {e}'


def main():
    ap = argparse.ArgumentParser(description='回滚之前清理脚本所做的元数据删除 (根据 .bak 备份恢复)')
    ap.add_argument('--models', default=','.join(DEFAULT_MODELS), help='模型列表，逗号分隔; 默认 deepseek,gemini,kimi')
    ap.add_argument('--data-base', type=str, default=None, help='数据结果根目录 (含 提取结果_by_xxx)')
    ap.add_argument('--dry-run', action='store_true', help='仅列出将恢复的文件，不真正覆盖')
    ap.add_argument('--remove-bak', action='store_true', help='恢复成功后删除 .bak 文件')
    ap.add_argument('--output-csv', type=str, default=None, help='回滚明细 CSV 路径')
    ap.add_argument('--limit', type=int, default=0, help='每模型最多恢复文件数 (0=不限)')
    args = ap.parse_args()

    script_dir = Path(__file__).resolve().parent
    extract_root = None
    if args.data_base:
        data_base = Path(args.data_base)
        extract_root = data_base.parent
    else:
        extract_root = detect_extract_root(script_dir)
        if extract_root is None:
            print('[ERROR] 未找到包含 数据结果 的根目录, 请用 --data-base 指定')
            return
        data_base = extract_root / '数据结果'

    if not data_base.exists():
        print(f'[ERROR] 数据结果根目录不存在: {data_base}')
        return

    models = [m.strip() for m in args.models.split(',') if m.strip()]
    if not models:
        print('[ERROR] 未提供模型列表')
        return

    if args.output_csv:
        csv_path = Path(args.output_csv)
    else:
        csv_path = data_base / '回滚元数据_明细.csv'
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    rows: List[dict] = []
    total_restore = 0

    for model in models:
        model_dir = data_base / f'提取结果_by_{model}' / 'in_scope'
        if not model_dir.exists():
            print(f'[WARN] 模型目录不存在: {model_dir}')
            continue
        bak_files = sorted(model_dir.glob('*.json.bak'))
        if args.limit > 0:
            bak_files = bak_files[: args.limit]
        restored_model = 0
        for bak in bak_files:
            ok, status = restore_file(bak, args.dry_run, args.remove_bak)
            if ok:
                restored_model += 1
                rows.append({
                    'model': model,
                    'bak_file': bak.name,
                    'json_file': bak.with_suffix('').name,
                    'status': status,
                    'size_bytes': bak.stat().st_size if bak.exists() else ''
                })
            else:
                rows.append({
                    'model': model,
                    'bak_file': bak.name,
                    'json_file': bak.with_suffix('').name,
                    'status': status,
                    'size_bytes': bak.stat().st_size if bak.exists() else ''
                })
        total_restore += restored_model
        print(f'[模型 {model}] 发现备份 {len(bak_files)} 恢复成功 {restored_model}')

    # 写 CSV
    with csv_path.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['model','bak_file','json_file','status','size_bytes'])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f'[INFO] 回滚明细写入: {csv_path} (记录 {len(rows)} 条)')
    if args.dry_run:
        print('[INFO] dry-run 模式未实际覆盖任何文件')
    else:
        print(f'[SUMMARY] 已恢复文件数: {total_restore}')

if __name__ == '__main__':
    main()
