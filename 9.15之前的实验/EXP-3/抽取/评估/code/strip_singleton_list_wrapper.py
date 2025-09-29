import json
from pathlib import Path
import shutil

"""批量处理 抽取/评估/gemini 目录下的 JSON 文件：
如果顶层是 [ { ... } ] 且只有 1 个元素，则去掉外层 []，
并把原始文件备份到同级目录 <gemini>_backup_before_strip/ 中。

重复执行时已处理过的文件会被跳过（因为已不是单元素 list）。
"""

def main():
    script_dir = Path(__file__).resolve().parent  # .../抽取/评估/code
    eval_dir = script_dir.parent                 # .../抽取/评估
    gemini_dir = eval_dir / 'gemini'
    if not gemini_dir.exists():
        raise SystemExit(f"[ERROR] 目录不存在: {gemini_dir}")
    backup_dir = gemini_dir.parent / (gemini_dir.name + '_backup_before_strip')
    backup_dir.mkdir(exist_ok=True)

    total = 0
    modified = 0
    skipped_parse = 0
    already_plain = 0

    for jf in sorted(gemini_dir.glob('*.json')):
        total += 1
        try:
            data = json.loads(jf.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"[SKIP] 解析失败 {jf.name}: {e}")
            skipped_parse += 1
            continue
        if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
            # 备份（仅第一次）
            backup_file = backup_dir / jf.name
            if not backup_file.exists():
                shutil.copy2(jf, backup_file)
            # 写回
            jf.write_text(json.dumps(data[0], ensure_ascii=False, indent=2), encoding='utf-8')
            modified += 1
        else:
            already_plain += 1
    print('\n== 处理结果 ==')
    print('目标目录      :', gemini_dir)
    print('备份目录      :', backup_dir)
    print('总文件数      :', total)
    print('修改(去壳)数  :', modified)
    print('已是对象数    :', already_plain)
    print('解析失败数    :', skipped_parse)
    if modified:
        print('[DONE] 已去除外层单元素数组包装。')
    else:
        print('[INFO] 无需修改或已全部处理。')

if __name__ == '__main__':
    main()
