import re
import json
from pathlib import Path
from typing import List, Optional, Dict, Tuple


def parse_txt_records(txt_path: Path) -> List[Dict[str, object]]:
    """从单个 txt 文件中解析出多条记录，每条记录含题名/作者/机构/时间。
    适配“摘要.txt”这类文件，里面包含多篇的重复键段：
      DataType: ...
      Title-题名: ...
      Author-作者: ...
      Organ-机构: ...
      PubTime-出版时间: ...
    返回记录列表。
    """
    content = txt_path.read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines()

    def split_items(s: str) -> List[str]:
        parts = re.split(r"[;；、，,]+", s)
        items = [p.strip() for p in parts if p and p.strip()]
        items = [re.sub(r"^[\-—·•]\s*", "", it) for it in items]
        return items

    records: List[Dict[str, object]] = []
    cur: Dict[str, object] = {}

    def push_cur():
        if not cur:
            return
        title = str(cur.get("title", "")).strip()
        if not title:
            return
        # 复制并规范类型
        rec = {
            "title": title,
            "authors": list(cur.get("authors", [])),
            "orgs": list(cur.get("orgs", [])),
            "pub_time": str(cur.get("pub_time", "")),
            "source_file": str(txt_path),
        }
        records.append(rec)

    # 键名正则（支持多写法与中英文冒号）
    title_patterns = [r"^Title-题名\s*[:：]\s*(.+)$", r"^题名-Title\s*[:：]\s*(.+)$", r"^题名\s*[:：]\s*(.+)$", r"^Title\s*[:：]\s*(.+)$"]
    author_patterns = [r"^Author-作者\s*[:：]\s*(.+)$", r"^作者-Author\s*[:：]\s*(.+)$", r"^作者\s*[:：]\s*(.+)$", r"^Author\s*[:：]\s*(.+)$"]
    organ_patterns = [r"^Organ-机构\s*[:：]\s*(.+)$", r"^机构-Organ\s*[:：]\s*(.+)$", r"^机构\s*[:：]\s*(.+)$", r"^Organ\s*[:：]\s*(.+)$"]
    pubtime_patterns = [r"^PubTime-出版时间\s*[:：]\s*(.+)$", r"^出版时间-PubTime\s*[:：]\s*(.+)$", r"^出版时间\s*[:：]\s*(.+)$", r"^PubTime\s*[:：]\s*(.+)$"]

    for raw in lines:
        line = raw.strip()
        if not line:
            # 空行标志一个记录结束（保守，不强依赖）
            continue
        # 标题行：遇到新 Title/题名 则推入上一条记录并开始新记录
        m_title = None
        for pat in title_patterns:
            m_title = re.match(pat, line)
            if m_title:
                break
        if m_title:
            # 如果已有当前记录，先推入
            if cur.get("title"):
                push_cur()
                cur = {}
            cur["title"] = m_title.group(1).strip()
            continue

        m_author = None
        for pat in author_patterns:
            m_author = re.match(pat, line)
            if m_author:
                break
        if m_author:
            cur["authors"] = split_items(m_author.group(1))
            continue

        m_org = None
        for pat in organ_patterns:
            m_org = re.match(pat, line)
            if m_org:
                break
        if m_org:
            cur["orgs"] = split_items(m_org.group(1))
            continue

        m_time = None
        for pat in pubtime_patterns:
            m_time = re.match(pat, line)
            if m_time:
                break
        if m_time:
            cur["pub_time"] = m_time.group(1).strip()
            continue

        # 其它键忽略（如 Keyword、Source 等），避免干扰

    # 文件结束，推入最后一条
    if cur.get("title"):
        push_cur()

    return records


def find_json_for_title(json_dir: Path, title: str) -> Optional[Path]:
    # 依据文件名前缀匹配：以题名起始的 json 文件
    candidates: List[Path] = []
    for p in json_dir.glob("*.json"):
        stem = p.stem  # 文件名不含扩展名
        if stem.startswith(title):
            candidates.append(p)
    if not candidates:
        # 二次尝试：去除空格再匹配
        t2 = title.replace(" ", "")
        for p in json_dir.glob("*.json"):
            if p.stem.replace(" ", "").startswith(t2):
                candidates.append(p)
    if not candidates:
        return None
    # 若多个，取最短文件名（更可能是精确匹配）
    candidates.sort(key=lambda p: len(p.name))
    return candidates[0]


def dedup_entities(entities: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen: set[Tuple[str, str]] = set()
    result: List[Dict[str, str]] = []
    for e in entities:
        t = e.get("text", "").strip()
        ty = e.get("type", "").strip()
        key = (t.lower(), ty)
        if key in seen:
            continue
        seen.add(key)
        result.append({"text": t, "type": ty})
    return result


def dedup_relations(relations: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen: set[Tuple[str, str, str]] = set()
    result: List[Dict[str, str]] = []
    for r in relations:
        head = r.get("head", "").strip()
        tail = r.get("tail", "").strip()
        ty = r.get("type", "").strip()
        key = (head, tail, ty)
        if key in seen:
            continue
        seen.add(key)
        result.append({"head": head, "tail": tail, "type": ty})
    return result


def augment_one(json_path: Path, meta: Dict[str, object]) -> bool:
    """将 meta 中的论文元信息追加到指定 JSON 文件。
    JSON 结构示例： [ { "entities": [...], "relations": [...] } ]
    返回 True 表示已修改并写回。
    """
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[WARN] 读取 JSON 失败：{json_path} -> {e}")
        return False

    # 容错：顶层若为对象 -> 包装为数组；若为空数组 -> 填充默认项
    if isinstance(data, dict):
        data = [data]
    if isinstance(data, list) and len(data) == 0:
        data = [{"entities": [], "relations": []}]
    if not isinstance(data, list) or not data:
        print(f"[WARN] JSON 结构异常（无法修复）：{json_path}")
        return False

    item = data[0]
    if not isinstance(item, dict):
        print(f"[WARN] JSON 结构异常（首项非对象）：{json_path}")
        return False
    entities = item.get("entities")
    relations = item.get("relations")
    if entities is None:
        entities = []
    if relations is None:
        relations = []
    if not isinstance(entities, list):
        print(f"[WARN] JSON 结构异常（entities 非列表，已跳过）：{json_path}")
        return False
    if not isinstance(relations, list):
        print(f"[WARN] JSON 结构异常（relations 非列表，已跳过）：{json_path}")
        return False

    title: str = meta.get("title", "")  # type: ignore
    authors: List[str] = meta.get("authors", [])  # type: ignore
    orgs: List[str] = meta.get("orgs", [])  # type: ignore
    pub_time: str = meta.get("pub_time", "")  # type: ignore

    # 构造需要追加的实体
    add_entities: List[Dict[str, str]] = []
    if title:
        add_entities.append({"type": "论文", "text": title})
    for a in authors:
        if a:
            add_entities.append({"type": "作者", "text": a})
    for o in orgs:
        if o:
            add_entities.append({"type": "发表单位", "text": o})
    if pub_time:
        add_entities.append({"type": "发表时间", "text": pub_time})

    # 构造需要追加的关系
    add_relations: List[Dict[str, str]] = []
    # 作者-撰写-论文
    for a in authors:
        if a and title:
            add_relations.append({"type": "撰写", "head": a, "tail": title})
    # 第一作者-隶属-第一单位
    if authors and orgs and authors[0] and orgs[0]:
        add_relations.append({"type": "隶属", "head": authors[0], "tail": orgs[0]})
    # 论文-发表于-发表时间
    if title and pub_time:
        add_relations.append({"type": "发表于", "head": title, "tail": pub_time})

    # 合并并去重
    entities_extended = dedup_entities(entities + add_entities)
    relations_extended = dedup_relations(relations + add_relations)

    changed = (len(entities_extended) != len(entities)) or (len(relations_extended) != len(relations))
    if not changed:
        return False

    item["entities"] = entities_extended
    item["relations"] = relations_extended

    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def main():
    # 目录定位
    root = Path(__file__).resolve().parents[1]  # 抽取 目录
    data_dir = root / "数据结果"
    json_dir = data_dir / "提取结果_by_gemini"

    print("[路径] data_dir:", data_dir)
    print("[路径] json_dir:", json_dir)

    if not json_dir.exists():
        print("[ERROR] JSON 目录不存在:", json_dir)
        return

    # 收集 txt 元信息（支持一个txt中多条记录，例如 摘要.txt）
    metas: List[Dict[str, object]] = []
    for txt in data_dir.glob("*.txt"):
        recs = parse_txt_records(txt)
        if not recs:
            continue
        metas.extend(recs)

    if not metas:
        print("[WARN] 未在", data_dir, "发现可解析的 txt 元信息。")
        return

    # 为每条元信息匹配 JSON 并增补
    updated, skipped = 0, 0
    matched_jsons: set[str] = set()
    updated_jsons: set[str] = set()
    for meta in metas:
        title = str(meta["title"])  # type: ignore
        jpath = find_json_for_title(json_dir, title)
        if not jpath:
            print(f"[INFO] 未找到匹配 JSON：{title}")
            skipped += 1
            continue
        matched_jsons.add(jpath.name)
        ok = augment_one(jpath, meta)
        if ok:
            print(f"[OK] 已增补：{jpath.name}")
            updated += 1
            updated_jsons.add(jpath.name)
        else:
            print(f"[SKIP] 无需更新或失败：{jpath.name}")
            skipped += 1

    print(f"[DONE] 更新完成，成功 {updated}，跳过 {skipped}")
    # 输出匹配到但完全未被更新过的 JSON 文件（用于定位未发生变化的篇目）
    never_updated = sorted(matched_jsons - updated_jsons)
    if never_updated:
        print(f"[REPORT] 匹配到但未发生更新的 JSON（按文件名）：共 {len(never_updated)} 篇")
        for name in never_updated:
            print(" -", name)
    else:
        print("[REPORT] 所有匹配到的 JSON 至少发生过一次更新。")


if __name__ == "__main__":
    main()
