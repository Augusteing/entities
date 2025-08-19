from collections import deque, defaultdict
import json

def find_entity_token_span(entity_text, tokens):
    """
    在 tokens 中查找能与 entity_text 模糊匹配的 token span，返回起止 token 的 id。
    """
    import re

    norm_entity = re.sub(r"\s+", "", entity_text.lower())
    token_texts = [t["form"].lower() for t in tokens]
    token_ids = [t["id"] for t in tokens]

    # 构建滑动窗口进行模糊匹配
    for start in range(len(tokens)):
        for end in range(start + 1, len(tokens) + 1):
            span_tokens = token_texts[start:end]
            joined = "".join(span_tokens)
            if norm_entity in joined or joined in norm_entity:
                return (token_ids[start], token_ids[end - 1])

    return None

def build_dependency_graph(parsed_tokens):
    """将 parsed 构建为无向图"""
    graph = defaultdict(list)
    id_to_token = {}
    for token in parsed_tokens:
        token_id = token["id"]
        head_id = token["head"]
        id_to_token[token_id] = token
        if head_id == 0:  # root
            continue
        # 添加双向边
        graph[token_id].append(head_id)
        graph[head_id].append(token_id)
    return graph, id_to_token

def find_shortest_dependency_path(graph, id_to_token, start_id, end_id):
    """返回 start_id 到 end_id 的最短路径上的 token 列表"""
    queue = deque([[start_id]])
    visited = set()

    while queue:
        path = queue.popleft()
        current = path[-1]

        if current == end_id:
            return [id_to_token[node_id] for node_id in path]

        if current in visited:
            continue
        visited.add(current)

        for neighbor in graph[current]:
            if neighbor not in visited:
                queue.append(path + [neighbor])

    return None  # 无路径

def process_entity_pair_in_sentence(entity_pair, parsed_tokens):
    # 1. 找实体在分词中的token位置
    subj_span = find_entity_token_span(entity_pair["subject"], parsed_tokens)
    obj_span = find_entity_token_span(entity_pair["object"], parsed_tokens)
    if not subj_span or not obj_span:
        return None

    subj_id = subj_span[0]  # 实体头部
    obj_id = obj_span[0]

    # 2. 构建依存图
    graph, id_to_token = build_dependency_graph(parsed_tokens)

    # 3. 路径查找
    path_tokens = find_shortest_dependency_path(graph, id_to_token, subj_id, obj_id)
    if path_tokens:
        return [(t["form"], t["deprel"]) for t in path_tokens]
    else:
        return None

def extract_dependency_paths_from_clause(parsed_tokens, entity_pairs):
    results = []
    graph, id_to_token = build_dependency_graph(parsed_tokens)
    
    for pair in entity_pairs:
        subj_span = find_entity_token_span(pair["subject"], parsed_tokens)
        obj_span = find_entity_token_span(pair["object"], parsed_tokens)
        
        if not subj_span or not obj_span:
            result = {
                "subject": pair["subject"],
                "object": pair["object"],
                "relation": pair["relation"],
                "path": None,
                "note": "实体对无法与token对齐"
            }
            print(f"对齐失败: subject={pair['subject']}, object={pair['object']}, tokens={[t['form'] for t in parsed_tokens]}")
            results.append(result)
            continue

        

        subj_id = subj_span[0]  # 取起始 token ID
        obj_id = obj_span[0]

        path_tokens = find_shortest_dependency_path(graph, id_to_token, subj_id, obj_id)

        if path_tokens:
            path = [(tok["form"], tok["deprel"]) for tok in path_tokens]
        else:
            path = None

        results.append({
            "subject": pair["subject"],
            "object": pair["object"],
            "relation": pair["relation"],
            "path": path
        })

    return results

with open(r"dependency_results\大数据下数模联动的随机退化设备剩余寿命预测技术_dependency.json", encoding = "utf-8") as file:
    text = json.load(file)
    parsed = text["analyzed_sentences"][0]["parsed"]

entity_pairs = [
  {
    "subject": "基于机器学习的预测技术",
    "subject_type": "Method",
    "relation": "addresses",
    "object": "随机退化设备剩余寿命预测",
    "object_type": "Problem"
  },
  {
    "subject": "统计数据驱动的预测技术",
    "subject_type": "Method",
    "relation": "addresses",
    "object": "不确定性量化问题",
    "object_type": "Problem"
  },
  {
    "subject": "深度学习与退化建模交互联动",
    "subject_type": "Model",
    "relation": "is_applied_to",
    "object": "航空发动机",
    "object_type": "System"
  },
  {
    "subject": "深度学习与退化建模交互联动",
    "subject_type": "Model",
    "relation": "predicts",
    "object": "不确定性量化问题",
    "object_type": "Problem"
  },
  {
    "subject": "数模联动预测思路",
    "subject_type": "Model",
    "relation": "achieves",
    "object": "剩余寿命预测结果",
    "object_type": "Finding"
  },
  {
    "subject": "剩余寿命预测结果",
    "subject_type": "Finding",
    "relation": "suggests",
    "object": "研究展望",
    "object_type": "Future Work"
  },
  {
    "subject": "特征",
    "subject_type": "Feature",
    "relation": "is_from",
    "object": "多源传感监测大数据",
    "object_type": "Sensor"
  }
]

paths = extract_dependency_paths_from_clause(parsed, entity_pairs)
print(json.dumps(paths, indent=2, ensure_ascii=False))