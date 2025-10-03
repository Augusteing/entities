import json
from pathlib import Path


def has_augmented_signatures(json_path: Path, title: str) -> tuple[bool, dict]:
    """判断是否已包含元信息增补的核心标志：
    - entities 中存在 {type: 论文, text: title}
    - relations 中存在 {type: 撰写, tail: title} 的任意一条
    返回 (augmented, details) 便于调试。
    """
    details = {"has_paper_entity": False, "has_write_relation": False, "has_publish_relation": False}
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        details["error"] = f"json read error: {e}"
        return (False, details)

    if not isinstance(data, list) or not data:
        details["error"] = "invalid top-level structure"
        return (False, details)

    item = data[0]
    entities = item.get("entities") or []
    relations = item.get("relations") or []
    if not isinstance(entities, list) or not isinstance(relations, list):
        details["error"] = "entities/relations not list"
        return (False, details)

    for e in entities:
        if str(e.get("type")) == "论文" and str(e.get("text")) == title:
            details["has_paper_entity"] = True
            break
    for r in relations:
        rtype = str(r.get("type"))
        head = str(r.get("head"))
        tail = str(r.get("tail"))
        if rtype == "撰写" and tail == title:
            details["has_write_relation"] = True
        if rtype == "发表于" and head == title:
            details["has_publish_relation"] = True

    # 放宽判定：有论文实体，且（有撰写关系 或 有发表于关系）之一即可视为已增补
    ok = details["has_paper_entity"] and (details["has_write_relation"] or details["has_publish_relation"])
    return (ok, details)


def main():
    root = Path(__file__).resolve().parents[1]
    json_dir = root / "数据结果" / "提取结果_by_gemini"
    if not json_dir.exists():
        print("[ERROR] JSON 目录不存在:", json_dir)
        return

    not_augmented = []
    augmented = []
    problems = []
    for p in sorted(json_dir.glob("*.json")):
        stem = p.stem
        title = stem.split("_", 1)[0]
        ok, details = has_augmented_signatures(p, title)
        if ok:
            augmented.append(p.name)
        else:
            not_augmented.append((p.name, details))
            if "error" in details:
                problems.append((p.name, details["error"]))

    print(f"[INFO] JSON文件总数: {len(augmented) + len(not_augmented)}")
    print(f"[INFO] 判定已增补: {len(augmented)}")
    print(f"[INFO] 判定未增补: {len(not_augmented)}")
    if problems:
        print("[WARN] 结构/读取异常文件：")
        for name, err in problems:
            print(" -", name, "=>", err)
    if not_augmented:
        print("[MISS] 未增补清单（文件名 | 诊断）：")
        for name, details in not_augmented:
            print(" -", name, "|", details)


if __name__ == "__main__":
    main()
