import os
import json
from dependency_path import find_entity_token_span, build_dependency_graph, find_shortest_dependency_path
from parsed_join import parsed_full

"""
combine_demo.py
目的：不改原函数逻辑，联合使用：
- 句内：最短依存路径
- 跨句：仅标记，不伪造路径
运行:
  python combine_demo.py 文章标题(不含后缀)
示例:
  python combine_demo.py 大数据下数模联动的随机退化设备剩余寿命预测技术
"""

def load_article(base_dir, title):
    dep_path = os.path.join(base_dir, 'dependency_results', f'{title}_dependency.json')
    pair_path = os.path.join(base_dir, '实体对', f'{title}实体对.json')
    if not os.path.isfile(dep_path):
        raise FileNotFoundError(f'依存文件不存在: {dep_path}')
    if not os.path.isfile(pair_path):
        raise FileNotFoundError(f'实体对文件不存在: {pair_path}')
    with open(dep_path, 'r', encoding='utf-8') as f:
        dep_data = json.load(f)
    with open(pair_path, 'r', encoding='utf-8') as f:
        pair_data = json.load(f)
    analyzed_sentences = dep_data.get('analyzed_sentences', [])
    sentences_parsed = [s.get('parsed', []) for s in analyzed_sentences]
    return sentences_parsed, pair_data

def find_entity_in_sent(entity_text, sentences_parsed):
    for idx, sent in enumerate(sentences_parsed):
        span = find_entity_token_span(entity_text, sent)
        if span:
            return idx, span
    return None

def compute_in_sentence_path(parsed_tokens, subj_id, obj_id):
    graph, id_to_token = build_dependency_graph(parsed_tokens)
    path_tokens = find_shortest_dependency_path(graph, id_to_token, subj_id, obj_id)
    if path_tokens:
        return [(t['form'], t.get('deprel')) for t in path_tokens]
    return None

def combine_demo(title):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    sentences_parsed, entity_pairs = load_article(base_dir, title)
    # 合并视图（仅展示，不做跨句路径）
    merged_tokens, merged_text = parsed_full([{ 'parsed': s } for s in sentences_parsed])
    print(f'[INFO] 文章: {title} | 句子数: {len(sentences_parsed)} | 合并token数: {len(merged_tokens)}')

    results = []
    in_sentence_success = 0
    cross_sentence = 0
    not_found = 0

    for pair in entity_pairs:
        subj_info = find_entity_in_sent(pair['subject'], sentences_parsed)
        obj_info = find_entity_in_sent(pair['object'], sentences_parsed)

        if subj_info and obj_info:
            if subj_info[0] == obj_info[0]:
                sent_idx = subj_info[0]
                parsed_tokens = sentences_parsed[sent_idx]
                subj_id = subj_info[1][0]
                obj_id = obj_info[1][0]
                path = compute_in_sentence_path(parsed_tokens, subj_id, obj_id)
                if path:
                    in_sentence_success += 1
                results.append({
                    'subject': pair['subject'],
                    'relation': pair.get('relation'),
                    'object': pair['object'],
                    'sentence_index': sent_idx,
                    'path': path,
                    'note': None if path else '同句未找到路径'
                })
            else:
                cross_sentence += 1
                results.append({
                    'subject': pair['subject'],
                    'relation': pair.get('relation'),
                    'object': pair['object'],
                    'sentence_index': None,
                    'path': None,
                    'note': '跨句'
                })
        else:
            not_found += 1
            results.append({
                'subject': pair['subject'],
                'relation': pair.get('relation'),
                'object': pair['object'],
                'sentence_index': None,
                'path': None,
                'note': '实体未对齐'
            })

    total = len(entity_pairs)
    summary = {
        'title': title,
        'total_pairs': total,
        'in_sentence_path_found': in_sentence_success,
        'cross_sentence_pairs': cross_sentence,
        'not_found_pairs': not_found,
        'in_sentence_coverage': round(in_sentence_success / total, 4) if total else 0.0
    }
    print('[SUMMARY]')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print('[DETAILS]')
    print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('用法: python combine_demo.py 文章标题(不含后缀)')
    else:
        combine_demo(sys.argv[1])