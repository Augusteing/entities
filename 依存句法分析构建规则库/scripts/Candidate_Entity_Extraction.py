import json
import re
import os
from typing import List, Dict, Set, Tuple
from collections import deque

# ------------------ 加载规则 ------------------
def load_templates(json_path: str) -> List[Dict]:
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)
    
# ------------------ R1: 模板规则匹配器 ------------------
def match_templates(sentence: str, templates: List[Dict]) -> Set[Tuple[str, str, str, str]]:
    matched = set()

    for temp in templates:
        pattern = temp.get("pattern")
        template_id = temp.get("template_id", "T?")
        entity_type = temp.get("entity_type", "未知类型")

        try:
            for m in re.finditer(pattern, sentence):
                matched.add((
                    m.group(0),
                    entity_type,
                    template_id,
                    pattern,
                ))

        except re.error as e:
            print(f"[RegexError] 模板 {template_id} 错误: {e}")
            continue

    return matched
# ------------------ R2 实现：依存+词性规则 ------------------
def apply_r2(parsed: List[Dict], rule: Dict) -> Set[str]:
    candidates = set()
    for i, t in enumerate(parsed):
        if t['pos'] != rule['center_pos']:
            continue
        entity_chain = [(i, t['form'])]
        for j, m in enumerate(parsed):
            if m['head'] == i + 1 and m['deprel'] in rule['dependency_chain'] and m['pos'] in rule['allowed_pos']:
                entity_chain.append((j, m['form']))
        if len(entity_chain) > 1:
            entity = ''.join([w for _, w in sorted(entity_chain, key=lambda x: x[0])])
            candidates.add(entity)
    return candidates

# ------------------ R3 实现：依存 + 相邻位置 ------------------
def apply_r3(parsed: List[Dict], rule: Dict) -> Set[str]:
    candidates = set()
    for i, t in enumerate(parsed):
        if t['pos'] != rule['center_pos']:
            continue
        entity_chain = [(i, t['form'])]
        for j in range(i - 1, -1, -1):  
            m = parsed[j]
            if m['pos'] in rule['allowed_pos'] and m['deprel'] in rule['dependency_chain'] and m['head'] == i + 1:
                if j == i - 1:  # strict left-adjacent
                    entity_chain.append((j, m['form']))
        if len(entity_chain) > 1:
            entity = ''.join([w for _, w in sorted(entity_chain, key=lambda x: x[0])])
            candidates.add(entity)
    return candidates

# ------------------ R4 实现：词性 + 相邻位置 ------------------
def apply_r4(parsed: List[Dict], rule: Dict) -> Set[str]:
    candidates = set()
    for i, token in enumerate(parsed):
        if token['pos'] != rule['center_pos']:
            continue

        entity_chain = [(i, token['form'])]
        current_idx = i
        for j in range(1, rule['max_length']):
            left_idx = current_idx - 1
            if left_idx < 0:
                break
            left_token = parsed[left_idx]
            if left_token['pos'] in rule['left_adjacent_pos']:
                entity_chain.append((left_idx, left_token['form']))
                current_idx = left_idx
            else:
                break  # 不满足词性则终止扩展

        if len(entity_chain) > 1:
            # 根据索引升序拼接实体短语
            sorted_chain = sorted(entity_chain, key=lambda x: x[0])
            phrase = ''.join([word for _, word in sorted_chain])
            candidates.add(phrase)

    return candidates

# ------------------ 单篇处理 ------------------
def extract_entities(article: Dict, r1_templates: List[Dict], r2_r4_rules: List[Dict]) -> List[str]:
    entity_set = set()
    for sent_info in article.get("analyzed_sentences", []):
        sentence = sent_info["sentence"]
        parsed = sent_info["parsed"]

        # R1: 模板匹配
        r1_entities_set = match_templates(sentence, r1_templates)
        r1_entities_only = {entity for entity, _, _, _ in r1_entities_set}

        # R2-R4
        r2_r4_entities = set()
        for rule in r2_r4_rules:
            if rule["rule_id"] == "R2":
                r2_r4_entities |= apply_r2(parsed, rule)
            elif rule["rule_id"] == "R3":
                r2_r4_entities |= apply_r3(parsed, rule)
            elif rule["rule_id"] == "R4":
                r2_r4_entities |= apply_r4(parsed, rule)

        entity_set |= r1_entities_only | r2_r4_entities

    return list(entity_set)

# ------------------ 批量处理 ------------------
def process_directory(input_dir: str, output_dir: str, r1_path: str, r2_r4_rules: List[Dict]):
    os.makedirs(output_dir, exist_ok=True)
    r1_templates = load_templates(r1_path)

    for fname in os.listdir(input_dir):
        if not fname.endswith('.json'):
            continue
        input_path = os.path.join(input_dir, fname)
        with open(input_path, 'r', encoding='utf-8') as f:
            article = json.load(f)

        entities = extract_entities(article, r1_templates, r2_r4_rules)

        output_data = {
            "article_id": fname,
            "extracted_entities": entities
        }
        output_path = os.path.join(output_dir, fname.replace('.json', '_entities.json'))
        with open(output_path, 'w', encoding='utf-8') as out_f:
            json.dump(output_data, out_f, ensure_ascii=False, indent=2)

    print(f"✅ 处理完成，共保存到：{output_dir}")


with open(r"inputs\dependency_rules.json", 'r', encoding='utf-8') as f:
    other_rules = json.load(f)

process_directory(
    input_dir = r"dependency_results",         # 包含多个article.json的目录
    output_dir=r"entities_result",       # 每篇抽取后的结果文件
    r1_path=r"inputs\template_rules.json",  # 模板文件
    r2_r4_rules = other_rules
)