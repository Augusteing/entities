from __future__ import annotations
from pathlib import Path
import re
import json
import shutil
import time
from typing import List, Dict, Tuple


# 元信息来源（用户指定的最新位置）
TXT_PATH = Path(r"E:\知识图谱构建\文献信息\摘要.txt")

# 本脚本位于 抽取/评估/code/填充脚本/ 下，向上三级得到 抽取 根
ROOT = Path(__file__).resolve().parents[3]
EVAL_DIR = ROOT / '评估' / '数据结果' / '发送结果_by_gemini'
BACKUP_DIR = EVAL_DIR / f"备份_元信息注入前_{time.strftime('%Y%m%d_%H%M%S')}"


# 解析 摘要.txt
SEP_RE = re.compile(r"[，,；;、\s]+")


def _after_colon(s: str) -> str:
    parts = re.split(r"[：:\-]\s*", s, maxsplit=1)
    return parts[1].strip() if len(parts) == 2 else s.strip()


def parse_txt_records(txt_path: Path) -> List[Dict]:
    recs: List[Dict] = []
    cur: Dict[str, object] = {}
    if not txt_path.exists():
        print(f"[ERROR] 未找到摘要.txt: {txt_path}")
        return recs
    for raw in txt_path.read_text('utf-8', errors='ignore').splitlines():
        line = raw.strip()
        if not line:
            continue
        low = line.lower()
        if ('题名' in line) or ('标题' in line) or ('title' in low):
            if cur.get('title'):
                recs.append(cur)
                cur = {}
            t = _after_colon(line.replace('题名', '').replace('标题', '').replace('Title', ''))
            cur['title'] = t.strip()
        elif ('作者' in line) or ('author' in low):
            s = _after_colon(line)
            cur['authors'] = [x for x in SEP_RE.split(s) if x]
        elif ('机构' in line) or ('单位' in line) or ('organ' in low) or ('affiliation' in low):
            s = _after_colon(line)
            cur['orgs'] = [x for x in SEP_RE.split(s) if x]
        elif ('发表时间' in line) or ('时间' in line) or ('日期' in line) or ('pubtime' in low) or ('year' in low) or ('date' in low):
            cur['pubtime'] = _after_colon(line)
    if cur.get('title'):
        recs.append(cur)
    return [r for r in recs if r.get('title')]


# 评估 JSON I/O
def load_eval_json(path: Path) -> Dict:
    try:
        data = json.loads(path.read_text('utf-8', errors='ignore'))
    except Exception:
        data = {}
    if isinstance(data, list):
        ents, rels = [], []
        for it in data:
            if isinstance(it, dict):
                ents.extend(it.get('entities', []) or [])
                rels.extend(it.get('relations', []) or [])
        data = {'entities': ents, 'relations': rels}
    if not isinstance(data, dict):
        data = {}
    data.setdefault('entities', [])
    data.setdefault('relations', [])
    return data


def save_eval_json(path: Path, data: Dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), 'utf-8')


def norm_title(s: str) -> str:
    # 归一化：
    # 1) 先去掉首尾空白
    # 2) 去掉前导的中英文冒号
    # 3) 再合并移除空白与下划线，避免文件名中的分隔符影响匹配
    s = (s or "").strip()
    s = re.sub(r"^[：:]+", "", s).strip()
    return re.sub(r"[\s_]+", "", s)


def extract_title_from_filename(name: str) -> str:
    base = name
    if base.lower().endswith('.json'):
        base = base[:-5]
    if base.lower().endswith('.response'):
        base = base[:-9]
    # 优先使用 _MinerU__ 作为截断标志，再取其之前的第一个下划线前的部分（去掉作者段）
    m = re.match(r"^(.*?)_MinerU__", base)
    if m:
        before = m.group(1)
        return before.split('_')[0]
    # 无 MinerU 标志时，保守地取第一个下划线前的部分
    return base.split('_')[0]


def build_eval_title_map(eval_dir: Path) -> Dict[str, Path]:
    fmap: Dict[str, Path] = {}
    # 支持 *.json 与 *.response.json
    files = list(eval_dir.glob('*.json')) + list(eval_dir.glob('*.response.json'))
    for p in files:
        title = extract_title_from_filename(p.name)
        key = norm_title(title)
        if key and (key not in fmap or len(p.name) < len(fmap[key].name)):
            fmap[key] = p
    return fmap


# 元信息 -> 实体/关系
def meta_to_entities_relations(title: str, authors: List[str], orgs: List[str], pubtime: str):
    ents, rels = [], []

    def ent(t, x):
        return {'type': t, 'text': x, 'evaluation': '正确'}

    def rel(h, t, rtype):
        return {'head': h, 'tail': t, 'type': rtype, 'evaluation': '正确'}

    if title:
        ents.append(ent('论文', title))
    if pubtime:
        ents.append(ent('发表时间', pubtime))
        if title:
            rels.append(rel(title, pubtime, '发表于'))
    if authors:
        for a in authors:
            ents.append(ent('作者', a))
            if title:
                rels.append(rel(a, title, '撰写'))
    if orgs:
        # 收录所有单位为实体
        for o in orgs:
            ents.append(ent('发表单位', o))
        # 隶属关系仅生成 第一作者-第一单位
        if authors:
            rels.append(rel(authors[0], orgs[0], '隶属'))

    return ents, rels


def sig_ent(e: Dict) -> Tuple[str, str]:
    return (e.get('type', '').strip(), e.get('text', '').strip())


def sig_rel(r: Dict) -> Tuple[str, str, str]:
    return (r.get('head', '').strip(), r.get('type', '').strip(), r.get('tail', '').strip())


def merge_with_correct(dst: Dict, add_ents: List[Dict], add_rels: List[Dict]) -> Tuple[int, int, int, int]:
    d_ents = dst.get('entities', [])
    d_rels = dst.get('relations', [])
    idx_e = {sig_ent(e): i for i, e in enumerate(d_ents)}
    idx_r = {sig_rel(r): i for i, r in enumerate(d_rels)}
    add_e = upd_e = add_r = upd_r = 0

    for e in add_ents:
        key = sig_ent(e)
        if key in idx_e:
            i = idx_e[key]
            if d_ents[i].get('evaluation') != '正确':
                d_ents[i]['evaluation'] = '正确'
                upd_e += 1
        else:
            d_ents.append(e)
            add_e += 1

    for r in add_rels:
        key = sig_rel(r)
        if key in idx_r:
            i = idx_r[key]
            if d_rels[i].get('evaluation') != '正确':
                d_rels[i]['evaluation'] = '正确'
                upd_r += 1
        else:
            d_rels.append(r)
            add_r += 1

    dst['entities'] = d_ents
    dst['relations'] = d_rels
    return add_e, upd_e, add_r, upd_r


def main():
    print('[路径] 摘要.txt =', TXT_PATH)
    print('[路径] 评估目录 =', EVAL_DIR)

    if not EVAL_DIR.exists():
        print('[ERROR] 未找到评估目录(发送结果_by_gemini)')
        return

    recs = parse_txt_records(TXT_PATH)
    if not recs:
        print('[ERROR] 未从摘要.txt解析到记录')
        return

    title_map = build_eval_title_map(EVAL_DIR)
    if not title_map:
        print('[ERROR] 评估目录下未发现 JSON')
        return

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    matched = updated = 0
    add_e_total = upd_e_total = add_r_total = upd_r_total = 0
    unmatched = []

    for rec in recs:
        title = (rec.get('title') or '').strip()
        key = norm_title(title)
        path = title_map.get(key)
        if not path:
            unmatched.append(title)
            continue

        # 备份一次
        b = BACKUP_DIR / path.name
        if not b.exists():
            try:
                shutil.copy2(path, b)
            except Exception:
                pass

        data = load_eval_json(path)
        authors = list(rec.get('authors') or [])
        orgs = list(rec.get('orgs') or [])
        pubtime = (rec.get('pubtime') or '').strip()

        ents, rels = meta_to_entities_relations(title, authors, orgs, pubtime)
        a_e, u_e, a_r, u_r = merge_with_correct(data, ents, rels)
        if a_e or u_e or a_r or u_r:
            save_eval_json(path, data)
            updated += 1
        matched += 1
        add_e_total += a_e
        upd_e_total += u_e
        add_r_total += a_r
        upd_r_total += u_r

    print(f'[DONE] 匹配篇数: {matched}')
    print(f'[DONE] 写入/更新文件: {updated}')
    print(f'[STAT] 实体 新增/改为正确: {add_e_total}/{upd_e_total}')
    print(f'[STAT] 关系 新增/改为正确: {add_r_total}/{upd_r_total}')
    print(f'[INFO] 备份目录: {BACKUP_DIR}')
    if unmatched:
        print(f'[INFO] 未匹配论文(示例≤20): {unmatched[:20]}')


if __name__ == '__main__':
    main()
