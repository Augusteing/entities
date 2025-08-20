from collections import deque, defaultdict
import json
import os
import re

def tokenize_entity_by_sentence_tokens(entity_text, all_sentence_tokens):
    """
    通过贪心算法，使用句子中已有的词元来“切分”实体字符串。
    
    这种方法可以避免为实体单独建立一个NLP处理流程，并确保实体和句子
    的词元标准保持一致。
    
    Args:
        entity_text (str): 实体短语，例如："航空发动机健康管理系统"。
        all_sentence_tokens (list): 从句子中提取的所有不重复的词元列表。
        
    Returns:
        list: 实体被切分后的字符串列表，例如：['航空', '发动机', '健康', '管理', '系统']。
    """
    # 规范化实体文本：移除空格并转为小写
    norm_entity = re.sub(r"\s+", "", entity_text.lower())
    
    # 按长度降序排序词元，以优先匹配更长的词（贪心策略）
    # 这样可以确保"机器学习"优先于"机器"被匹配
    sorted_tokens = sorted(list(set(all_sentence_tokens)), key=len, reverse=True)
    
    entity_tokens = []
    while norm_entity:
        found_match = False
        for token in sorted_tokens:
            if norm_entity.startswith(token):
                entity_tokens.append(token)
                norm_entity = norm_entity[len(token):]
                found_match = True
                break
        # 如果句子中的任何词元都无法匹配实体字符串的剩余部分，则终止循环
        if not found_match:
            break
            
    return entity_tokens

def find_entity_token_span(entity_text, tokens):
    """
    使用F1分数匹配算法，为实体在句子中寻找最佳的词元跨度（span）。
    
    相比简单的子字符串匹配，此方法对于处理非连续的词元更为鲁棒。
    
    Returns:
        tuple: 最佳匹配词元跨度的 (起始索引, 结束索引) 元组。如果找不到合适的跨度，则返回 None。
    """
    token_texts = [t["form"].lower() for t in tokens]
    
    # 1. 基于句子中存在的词元，对实体短语进行切分。
    entity_words = tokenize_entity_by_sentence_tokens(entity_text, token_texts)
    if not entity_words:
        return None
    entity_words_set = set(entity_words)

    best_score = -1.0
    best_span = None

    # 2. 遍历句子中所有可能的词元跨度。
    for i in range(len(tokens)):
        for j in range(i, len(tokens)):
            # 优化：如果当前跨度比实体包含的词元数还少，则不可能完全匹配，直接跳过。
            if j - i + 1 < len(entity_words_set):
                continue
                
            span_texts = token_texts[i:j+1]
            span_set = set(span_texts)
            
            # 3. 为当前跨度计算F1分数。
            common_words = entity_words_set.intersection(span_set)
            
            if not common_words:
                continue

            precision = len(common_words) / len(span_set)
            recall = len(common_words) / len(entity_words_set)
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

            # 4. 更新最高分。如果分数相同，优先选择更短的跨度。
            if f1 > best_score:
                best_score = f1
                best_span = (i, j)
            elif f1 == best_score and best_span and (j - i) < (best_span[1] - best_span[0]):
                best_span = (i, j)
    
    # 5. 仅当最高分超过预设阈值时，才返回最佳跨度。
    # 这个阈值可以防止匹配到相似度过低的跨度。
    if best_score > 0.5:
        return best_span

    return None

def find_head_token_id(token_span, tokens):
    """
    寻找给定词元跨度（span）的核心词（head）。
    
    核心词指的是跨度内的一个词元，其自身的依存指向（head）位于该跨度之外。
    
    Args:
        token_span (tuple): 词元跨度的 (起始索引, 结束索引)。
        tokens (list): 句子中所有词元对象的列表。
        
    Returns:
        int: 核心词的ID。
    """
    start_idx, end_idx = token_span
    span_tokens = tokens[start_idx : end_idx + 1]
    span_token_ids = {t['id'] for t in span_tokens}

    # 寻找头部（head）在跨度外部的词元
    for token in span_tokens:
        if token['head'] not in span_token_ids:
            return token['id']
            
    # 作为备选方案（例如，当整个句子都是跨度时），返回最后一个词元的ID。
    # 对于像中文这样的核心词后置语言，这是一个合理的启发式规则。
    if span_tokens:
        return span_tokens[-1]['id']
        
    return None


def build_dependency_graph(parsed_tokens):
    """将依存分析结果构建为一个无向图。"""
    graph = defaultdict(list)
    id_to_token = {}
    for token in parsed_tokens:
        token_id = token["id"]
        head_id = token["head"]
        id_to_token[token_id] = token
        if head_id == 0:  # 根节点
            continue
        graph[token_id].append(head_id)
        graph[head_id].append(token_id)
    return graph, id_to_token

def find_shortest_dependency_path(graph, id_to_token, start_id, end_id):
    """使用广度优先搜索（BFS）寻找两个词元之间的最短路径。"""
    if start_id is None or end_id is None or start_id not in graph or end_id not in graph:
        return None
    queue = deque([[start_id]])
    visited = {start_id}

    while queue:
        path = queue.popleft()
        current_id = path[-1]

        if current_id == end_id:
            return [id_to_token[node_id] for node_id in path]

        for neighbor_id in graph.get(current_id, []):
            if neighbor_id not in visited:
                visited.add(neighbor_id)
                new_path = list(path)
                new_path.append(neighbor_id)
                queue.append(new_path)

    return None

def extract_dependency_paths_from_clause(parsed_tokens, entity_pairs):
    """
    处理单个句子的主提取逻辑。
    
    此函数现在使用了优化后的跨度查找和核心词识别功能。
    """
    results = []
    if not parsed_tokens:
        return []

    graph, id_to_token = build_dependency_graph(parsed_tokens)
    
    for pair in entity_pairs:
        # 1. 为主语和宾语找到最佳的词元跨度。
        subj_span_indices = find_entity_token_span(pair["subject"], parsed_tokens)
        obj_span_indices = find_entity_token_span(pair["object"], parsed_tokens)
        
        path = None
        note = None

        if subj_span_indices and obj_span_indices:
            # 2. 为每个跨度找到核心词。
            subj_head_id = find_head_token_id(subj_span_indices, parsed_tokens)
            obj_head_id = find_head_token_id(obj_span_indices, parsed_tokens)

            # 3. 寻找两个核心词之间的最短依存路径。
            path_tokens = find_shortest_dependency_path(graph, id_to_token, subj_head_id, obj_head_id)
            
            if path_tokens:
                path = [(tok["form"], tok["deprel"]) for tok in path_tokens]
            else:
                note = "实体核心词之间不存在依存路径" 
        else:
            note = "实体对无法与词元对齐" 
            print(f"对齐失败: subject='{pair['subject']}', object='{pair['object']}', tokens={[t['form'] for t in parsed_tokens]}")

        result = {
            "subject": pair["subject"],
            "object": pair["object"],
            "relation": pair.get("relation"), # 使用 .get() 方法以安全地访问字典
            "path": path
        }
        if note:
            result["note"] = note
        
        results.append(result)

    return results


def process_entity_pairs_folder():
    """批量处理函数，读取实体对和依存分析结果，并生成最终的路径文件。"""
    entity_folder = "实体对"
    dep_folder = "dependency_results"
    output_folder = "路径结果" # 修改输出文件夹名称，以区别于旧版本
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    for filename in os.listdir(entity_folder):
        if filename.endswith(".json"):
            entity_path = os.path.join(entity_folder, filename)
            with open(entity_path, encoding="utf-8") as f:
                entity_pairs = json.load(f)

            article_title = filename.replace(".json", "")
            dep_filename = f"{article_title}_dependency.json"
            dep_path = os.path.join(dep_folder, dep_filename)
            
            if not os.path.exists(dep_path):
                print(f"依存分析文件未找到，跳过: {dep_path}")
                continue
                
            with open(dep_path, encoding="utf-8") as f:
                dep_json = json.load(f)
                
            all_results = []
            for sent_data in dep_json.get("analyzed_sentences", []):
                parsed_tokens = sent_data.get("parsed", [])
                sentence_text = sent_data.get("text", "")
                
                # 仅当句子包含有效的解析结果时才进行处理
                if parsed_tokens:
                    paths = extract_dependency_paths_from_clause(parsed_tokens, entity_pairs)
                    if paths: # 仅当路径被处理过（即列表不为空）时才添加结果
                         all_results.append({
                            "sentence": sentence_text,
                            "paths": paths
                        })

            outname = filename.replace(".json", "_paths.json")
            outpath = os.path.join(output_folder, outname)
            with open(outpath, "w", encoding="utf-8") as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2)
                
            print(f"已处理: {filename} -> {outname}")

if __name__ == "__main__":
    process_entity_pairs_folder()