import re
from pathlib import Path


def parse_titles_from_summary(txt_path: Path) -> set[str]:
    content = txt_path.read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines()
    titles: set[str] = set()
    for raw in lines:
        m = re.match(r"^Title-题名:\s*(.+)$", raw.strip())
        if m:
            title = m.group(1).strip()
            if title:
                titles.add(title)
    # 也考虑去掉空格的版本，便于宽松匹配
    titles |= {t.replace(" ", "") for t in list(titles)}
    return titles


def main():
    root = Path(__file__).resolve().parents[1]  # 抽取目录
    data_dir = root / "数据结果"
    json_dir = data_dir / "提取结果_by_gemini"
    summary_fp = data_dir / "摘要.txt"

    if not json_dir.exists():
        print("[ERROR] JSON 目录不存在:", json_dir)
        return
    if not summary_fp.exists():
        print("[ERROR] 摘要文件不存在:", summary_fp)
        return

    summary_titles = parse_titles_from_summary(summary_fp)
    json_titles = []
    for p in sorted(json_dir.glob("*.json")):
        stem = p.stem
        # 题名在第一个下划线之前
        title = stem.split("_", 1)[0]
        json_titles.append((title, p.name))

    missing = []
    for title, fname in json_titles:
        t1 = title
        t2 = title.replace(" ", "")
        if (t1 not in summary_titles) and (t2 not in summary_titles):
            missing.append((title, fname))

    print("[INFO] JSON 文件数:", len(json_titles))
    print("[INFO] 摘要中标题条目数(含空格去除并集):", len(summary_titles))
    if not missing:
        print("[OK] 所有 JSON 题名均能在摘要中找到对应标题。")
    else:
        print(f"[MISS] 在摘要中未找到的 JSON（共 {len(missing)} 篇）：")
        for title, fname in missing:
            print(" -", fname, "| 题名:", title)


if __name__ == "__main__":
    main()
