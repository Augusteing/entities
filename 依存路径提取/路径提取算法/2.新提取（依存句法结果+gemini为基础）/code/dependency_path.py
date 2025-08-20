from collections import deque, defaultdict
import json
import os
from datetime import datetime

"""
批量依存路径提取脚本（支持可选跨句最短路径）

新增 / 变化要点：
1. 配置：
   ENABLE_CROSS_SENTENCE = True 开启跨句；CROSS_SENTENCE_STRATEGY = 'super_root'
2. 句内：保持原逻辑（同一句才做句内 BFS）。
3. 跨句（super_root）：
   - 为每一句的 root（head==0 的 token）挂到虚拟节点 SUPER_ROOT
   - 构建统一图时给每个 token 分配唯一 key: "{sent_idx}:{token_id}"
   - BFS 时若实体在不同句且允许跨句，则在跨句图中找最短路径
   - 输出中添加 path_type: 'intra_sentence' / 'cross_sentence'
4. 输出记录：
   - 对跨句成功的路径同样给出 path（去掉 SUPER_ROOT），并提供 path_positions 以便后续可视化
5. stats 新增：
   cross_sentence_pairs（实体位于不同句的对数）
   cross_sentence_path_found（其中成功找到跨句路径的数量）

保持兼容：
- 原先 path 仍为 list[ (form, deprel) ]
- 仅新增 path_type, path_positions, note 字段（note 原先已存在）

后续可扩展点（未实现）：
- 改进实体匹配（最长匹配 / 覆盖率阈值）
- 多种跨句策略（链式、窗口等）
- 模式库与路径签名
"""

# ================== 配置 ==================
ENABLE_CROSS_SENTENCE = True
CROSS_SENTENCE_STRATEGY = 'super_root'  # 目前仅实现 super_root
# ========================================


def find_entity_token_span(entity_text, tokens):
    """
    在 tokens 中查找能与 entity_text 模糊匹配的 token span，返回 (start_id, end_id)。
    现实现：极简滑窗 + 去空白小写匹配（可能过宽，后续可优化）。
    """
    import re
    norm_entity = re.sub(r"\s+", "", entity_text.lower())
    token_texts = [t["form"].lower() for t in tokens]
    token_ids = [t["id"] for t in tokens]

    for start in range(len(tokens)):
        for end in range(start + 1, len(tokens) + 1):
            span_tokens = token_texts[start:end]
            joined = "".join(span_tokens)
            if norm_entity in joined or joined in norm_entity:
                return (token_ids[start], token_ids[end - 1])
    return None


def build_dependency_graph(parsed_tokens):
    """句内：将单句 parsed tokens 构建为无向图"""
    graph = defaultdict(list)
    id_to_token = {}
    for token in parsed_tokens:
        token_id = token["id"]
        head_id = token["head"]
        id_to_token[token_id] = token
        if head_id == 0:  # root
            continue
        graph[token_id].append(head_id)
        graph[head_id].append(token_id)
    return graph, id_to_token


def find_shortest_dependency_path(graph, id_to_token, start_id, end_id):
    """返回 start_id 到 end_id 的最短路径上的 token 列表（句内）"""
    queue = deque([[start_id]])
    visited = set()
    while queue:
        path = queue.popleft()
        cur = path[-1]
        if cur == end_id:
            return [id_to_token[nid] for nid in path]
        if cur in visited:
            continue
        visited.add(cur)
        for nb in graph[cur]:
            if nb not in visited:
                queue.append(path + [nb])
    return None


# ================== 跨句图构建（super_root 策略） ==================
def build_cross_sentence_graph(sentences_parsed):
    """
    返回：graph, id_to_token, super_root_key
    graph: key -> list[key]  (key 为 "sent_idx:token_id" 或 "SUPER_ROOT")
    id_to_token: key -> token扩展字典 { ..., sentence_index, global_id }
    """
    graph = defaultdict(list)
    id_to_token = {}
    root_keys = []
    for sent_idx, tokens in enumerate(sentences_parsed):
        # 先建立本句节点
        local_index = {tok["id"]: f"{sent_idx}:{tok['id']}" for tok in tokens}
        for tok in tokens:
            key = local_index[tok["id"]]
            id_to_token[key] = {
                **tok,
                "sentence_index": sent_idx,
                "global_id": key
            }
        # 句内边
        for tok in tokens:
            if tok["head"] != 0:
                child_key = local_index[tok["id"]]
                head_key = local_index.get(tok["head"])
                if head_key:
                    graph[child_key].append(head_key)
                    graph[head_key].append(child_key)
            else:
                # root token
                root_keys.append(local_index[tok["id"]])

    super_root_key = "SUPER_ROOT"
    for rk in root_keys:
        graph[super_root_key].append(rk)
        graph[rk].append(super_root_key)

    return graph, id_to_token, super_root_key


def bfs_shortest_path(graph, start_key, end_key):
    """通用 BFS（跨句用），返回 key 序列"""
    queue = deque([[start_key]])
    visited = set()
    while queue:
        path = queue.popleft()
        cur = path[-1]
        if cur == end_key:
            return path
        if cur in visited:
            continue
        visited.add(cur)
        for nb in graph[cur]:
            if nb not in visited:
                queue.append(path + [nb])
    return None
# ===============================================================


def find_entity_in_sentences(entity_text, sentences_parsed):
    """返回 (sentence_index, span_ids) 或 None"""
    for idx, sent in enumerate(sentences_parsed):
        span = find_entity_token_span(entity_text, sent)
        if span:
            return idx, span
    return None


def extract_paths_for_article(dep_json_path, entity_pairs_path, output_dir, log_lines):
    title = os.path.basename(dep_json_path)[:-len("_dependency.json")]
    try:
        with open(dep_json_path, encoding='utf-8') as f:
            dep_data = json.load(f)
    except Exception as e:
        log_lines.append(f"[ERROR] 读取依存文件失败 {title}: {e}")
        return

    try:
        with open(entity_pairs_path, encoding='utf-8') as f:
            entity_pairs = json.load(f)
    except Exception as e:
        log_lines.append(f"[ERROR] 读取实体对文件失败 {title}: {e}")
        return

    analyzed_sentences = dep_data.get("analyzed_sentences", [])
    sentences_parsed = [s.get("parsed", []) for s in analyzed_sentences]

    # 若需要跨句，提前构建跨句图
    cross_graph = cross_id_map = cross_super_root = None
    if ENABLE_CROSS_SENTENCE and CROSS_SENTENCE_STRATEGY == 'super_root' and sentences_parsed:
        cross_graph, cross_id_map, cross_super_root = build_cross_sentence_graph(sentences_parsed)

    article_results = []
    total_pairs = len(entity_pairs)
    aligned = 0
    path_found = 0
    cross_sentence_pairs = 0
    cross_sentence_path_found = 0

    for pair in entity_pairs:
        subj_info = find_entity_in_sentences(pair["subject"], sentences_parsed)
        obj_info = find_entity_in_sentences(pair["object"], sentences_parsed)

        if not subj_info or not obj_info:
            note = "实体至少一端未找到"
            article_results.append({
                "subject": pair["subject"],
                "object": pair["object"],
                "relation": pair.get("relation"),
                "path": None,
                "path_type": None,
                "sentence_index": None,
                "path_positions": None,
                "note": note
            })
            log_lines.append(f"[ALIGN_FAIL] {title} | {pair['subject']} - {pair.get('relation')} - {pair['object']} | {note}")
            continue

        subj_sent, subj_span = subj_info
        obj_sent, obj_span = obj_info

        if subj_sent == obj_sent:
            # 句内
            aligned += 1
            tokens = sentences_parsed[subj_sent]
            subj_id = subj_span[0]
            obj_id = obj_span[0]
            graph, id_to_token = build_dependency_graph(tokens)
            path_tokens = find_shortest_dependency_path(graph, id_to_token, subj_id, obj_id)
            if path_tokens:
                path = [(t["form"], t.get("deprel")) for t in path_tokens]
                path_found += 1
                note = ""
                path_positions = [{"sentence_index": subj_sent, "id": t["id"]} for t in path_tokens]
            else:
                path = None
                note = "无依存路径"
                path_positions = None
                log_lines.append(f"[NO_PATH] {title} | {pair['subject']} - {pair.get('relation')} - {pair['object']}")

            article_results.append({
                "subject": pair["subject"],
                "object": pair["object"],
                "relation": pair.get("relation"),
                "path": path,
                "path_type": "intra_sentence",
                "sentence_index": subj_sent,
                "path_positions": path_positions,
                "note": note or None
            })
        else:
            # 跨句
            cross_sentence_pairs += 1
            if ENABLE_CROSS_SENTENCE and cross_graph:
                subj_key = f"{subj_sent}:{subj_span[0]}"
                obj_key = f"{obj_sent}:{obj_span[0]}"
                if subj_key in cross_graph and obj_key in cross_graph:
                    key_path = bfs_shortest_path(cross_graph, subj_key, obj_key)
                    if key_path:
                        # 去掉 SUPER_ROOT
                        filtered_keys = [k for k in key_path if k != cross_super_root]
                        path_tokens = [cross_id_map[k] for k in filtered_keys]
                        path = [(t["form"], t.get("deprel")) for t in path_tokens]
                        path_positions = [
                            {"sentence_index": t["sentence_index"], "id": t["id"]}
                            for t in path_tokens
                        ]
                        cross_sentence_path_found += 1
                        note = ""
                        article_results.append({
                            "subject": pair["subject"],
                            "object": pair["object"],
                            "relation": pair.get("relation"),
                            "path": path,
                            "path_type": "cross_sentence",
                            "sentence_index": None,  # 跨句不单独给某一句
                            "path_positions": path_positions,
                            "note": None
                        })
                    else:
                        path = None
                        note = "跨句无路径"
                        article_results.append({
                            "subject": pair["subject"],
                            "object": pair["object"],
                            "relation": pair.get("relation"),
                            "path": None,
                            "path_type": "cross_sentence",
                            "sentence_index": None,
                            "path_positions": None,
                            "note": note
                        })
                        log_lines.append(f"[NO_CROSS_PATH] {title} | {pair['subject']} - {pair.get('relation')} - {pair['object']}")
                else:
                    # key 不在图中（极少数：缺失 / 解析异常）
                    note = "跨句节点缺失"
                    article_results.append({
                        "subject": pair["subject"],
                        "object": pair["object"],
                        "relation": pair.get("relation"),
                        "path": None,
                        "path_type": "cross_sentence",
                        "sentence_index": None,
                        "path_positions": None,
                        "note": note
                    })
                    log_lines.append(f"[CROSS_NODE_MISS] {title} | {pair['subject']} - {pair.get('relation')} - {pair['object']}")
            else:
                # 未启用跨句
                note = "实体位于不同句且未开启跨句"
                article_results.append({
                    "subject": pair["subject"],
                    "object": pair["object"],
                    "relation": pair.get("relation"),
                    "path": None,
                    "path_type": None,
                    "sentence_index": None,
                    "path_positions": None,
                    "note": note
                })
                log_lines.append(f"[CROSS_DISABLED] {title} | {pair['subject']} - {pair.get('relation')} - {pair['object']}")

    # -------- 循环结束，统计信息 --------
    stats = {
        "total_pairs": total_pairs,
        "aligned_pairs": aligned,
        "path_found": path_found,
        "cross_sentence_pairs": cross_sentence_pairs,
        "cross_sentence_path_found": cross_sentence_path_found
    }

    out_obj = {
        "title": title,
        "stats": stats,
        "pairs": article_results,
        "config": {
            "enable_cross_sentence": ENABLE_CROSS_SENTENCE,
            "cross_sentence_strategy": CROSS_SENTENCE_STRATEGY if ENABLE_CROSS_SENTENCE else None
        }
    }

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"{title}依存路径.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out_obj, f, ensure_ascii=False, indent=2)

    log_lines.append(f"[DONE] {title} stats={stats}")

def batch_process():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    dep_dir = os.path.join(base_dir, 'dependency_results')
    pair_dir = os.path.join(base_dir, '实体对')
    output_dir = os.path.join(base_dir, '依存路径提取结果')
    os.makedirs(output_dir, exist_ok=True)

    log_lines = [f"=== 依存路径批处理开始 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ==="]

    if not os.path.isdir(dep_dir):
        print(f"未找到 dependency_results 目录: {dep_dir}")
        return
    if not os.path.isdir(pair_dir):
        print(f"未找到 实体对 目录: {pair_dir}")
        return

    dep_files = [f for f in os.listdir(dep_dir) if f.endswith('_dependency.json')]
    if not dep_files:
        print("dependency_results 目录中未找到 *_dependency.json 文件")
        return

    for dep_filename in dep_files:
        title = dep_filename[:-len('_dependency.json')]
        dep_path = os.path.join(dep_dir, dep_filename)
        pair_filename = f"{title}实体对.json"
        pair_path = os.path.join(pair_dir, pair_filename)
        if not os.path.isfile(pair_path):
            print(f"未找到对应实体对文件: {pair_filename}")
            log_lines.append(f"[MISS_PAIRS_FILE] {title} -> {pair_filename}")
            continue
        extract_paths_for_article(dep_path, pair_path, output_dir, log_lines)

    log_lines.append(f"=== 处理结束 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    log_path = os.path.join(output_dir, 'log.txt')
    with open(log_path, 'a', encoding='utf-8') as lf:
        lf.write('\n'.join(log_lines) + '\n')
    print(f"批处理完成，日志写入: {log_path}")

if __name__ == '__main__':
    batch_process()