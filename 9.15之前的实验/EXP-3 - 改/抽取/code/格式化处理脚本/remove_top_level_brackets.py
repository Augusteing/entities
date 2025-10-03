import json
import argparse
from pathlib import Path
from datetime import datetime
import shutil


# 脚本位于 抽取/code/格式化处理脚本/ 下，两级上层即 抽取 目录
DEFAULT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET = '数据结果/提取结果_by_gemini'


def parse_args():
    p = argparse.ArgumentParser(description='移除 JSON 顶层 []：若为数组则合并其 entities/relations 为单对象保存')
    p.add_argument('--root', type=Path, default=DEFAULT_ROOT, help='根目录(指向 抽取 )，默认自动推断')
    p.add_argument('--dir', type=Path, help='目标目录(相对或绝对)，默认 root/数据结果/提取结果_by_gemini')
    p.add_argument('--dry-run', action='store_true', help='仅预览将要修改的文件，不实际写入')
    return p.parse_args()


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None


def ensure_list(x):
    return x if isinstance(x, list) else []


def merge_list_items(items):
    # 将列表中每个 dict 的 entities/relations 合并到单个对象
    merged = { 'entities': [], 'relations': [] }
    for it in items:
        if isinstance(it, dict):
            ents = ensure_list(it.get('entities'))
            rels = ensure_list(it.get('relations'))
            merged['entities'].extend(ents)
            merged['relations'].extend(rels)
    return merged


def main():
    args = parse_args()
    root = args.root
    target_dir = args.dir if args.dir else (root / DEFAULT_TARGET)
    target_dir = target_dir.resolve()

    if not target_dir.exists():
        print('[错误] 目标目录不存在:', target_dir)
        return

    # 建立时间戳存档目录，仅备份将要被修改的文件
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = target_dir / f'存档_去括号前_{ts}'

    changed = []
    skipped = []
    failed = []

    for jp in sorted(target_dir.glob('*.json')):
        data = load_json(jp)
        if data is None:
            failed.append((jp.name, '无法解析为JSON'))
            continue
        if isinstance(data, list):
            # 空数组 -> 转为空对象
            if len(data) == 0:
                new_obj = { 'entities': [], 'relations': [] }
            # 单元素列表且为字典 -> 直接取其对象（并确保键为列表）
            elif len(data) == 1 and isinstance(data[0], dict):
                ents = ensure_list(data[0].get('entities'))
                rels = ensure_list(data[0].get('relations'))
                new_obj = { 'entities': ents, 'relations': rels }
            else:
                # 多元素或含非dict元素 -> 合并
                new_obj = merge_list_items(data)

            # 写入前备份
            changed.append(jp.name)
            if not args.dry_run:
                if not backup_dir.exists():
                    backup_dir.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(jp, backup_dir / jp.name)
                except Exception:
                    pass
                # 覆盖保存
                jp.write_text(json.dumps(new_obj, ensure_ascii=False, indent=2), encoding='utf-8')
        elif isinstance(data, dict):
            # 不是数组，确保结构基本规范
            ents = data.get('entities')
            rels = data.get('relations')
            normalized = False
            if ents is not None and not isinstance(ents, list):
                data['entities'] = ensure_list(ents)
                normalized = True
            if rels is not None and not isinstance(rels, list):
                data['relations'] = ensure_list(rels)
                normalized = True
            if normalized:
                changed.append(jp.name)
                if not args.dry_run:
                    if not backup_dir.exists():
                        backup_dir.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.copy2(jp, backup_dir / jp.name)
                    except Exception:
                        pass
                    jp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            else:
                skipped.append(jp.name)
        else:
            skipped.append(jp.name)

    print('处理完成:')
    print('  目标目录   =', target_dir)
    print('  备份目录   =', backup_dir if changed and not args.dry_run else '（未创建）')
    print('  Dry-Run    =', args.dry_run)
    print('  变更文件数 =', len(changed))
    print('  跳过文件数 =', len(skipped))
    print('  失败文件数 =', len(failed))
    if changed:
        print('\n[变更清单](前10):')
        for n in changed[:10]:
            print(' -', n)
        if len(changed) > 10:
            print(' ... 共', len(changed), '个')
    if failed:
        print('\n[失败清单](最多10):')
        for n, reason in failed[:10]:
            print(' -', n, '|', reason)


if __name__ == '__main__':
    main()
