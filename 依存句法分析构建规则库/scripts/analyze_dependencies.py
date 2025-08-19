import json
import hanlp
import re
import os

# 加载 HanLP 预训练依存分析模型
dep_parser = hanlp.load('CTB9_DEP_ELECTRA_SMALL')
tokenizer = hanlp.load('CTB9_TOK_ELECTRA_SMALL')   #分词模型，记得关掉梯子
pos_tagger = hanlp.load('CTB9_POS_ELECTRA_SMALL')


def split_sentences(text):
    """使用中文标点进行分句，先使用句号、问号和感叹号分割，再使用逗号或分号分割子句"""
    sentences = re.split(r'[。！？]', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    sub_sentences = []
    for sentence in sentences:
        if '；' in sentence:
            sub_sentence = re.split(r'；', sentence)
        else:
            sub_sentence = re.split(r'，', sentence)
        sub_sentences.extend([s.strip() for s in sub_sentence if s.strip()])
    return sub_sentences

def analyze_dependencies(records,  output_dir):
    results = []
    for record in records:
        title = record.get('title', '').strip()
        summary = record.get('summary', '').strip()
        # 分句
        sentences = split_sentences(summary)
        analyzed_sentences = []

        for sent in sentences:
            # 分词处理
            tokens = tokenizer(sent)
            # 词性标注
            pos_tags = pos_tagger(tokens)
            # 依存句法分析
            parsed = dep_parser(tokens)
            #只保留parsed中的id、form、head和deprel字段
            filtered_parsed = []
            for item, pos in zip(parsed, pos_tags):
                filtered_item = {
                    "id": item.get("id"),
                    "form": item.get("form"),
                    "head": item.get("head"),          # 依存关系的头节点
                    "deprel": item.get("deprel"),      # 依存关系类型
                    "pos": pos                        # 词性标注
                }
                filtered_parsed.append(filtered_item)

            analyzed_sentences.append({
                "sentence": sent,
                "tokens": tokens,
                "parsed": filtered_parsed
            })
        
        title_clean = re.sub(r'[\\/:*?"<>|]', '', title)
        output_json_path = f"{output_dir}\\{title_clean}_dependency.json"
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存结果到 JSON 文件
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump({
                "title": title_clean,
                "summary": summary,
                "analyzed_sentences": analyzed_sentences
            }, f, ensure_ascii=False, indent=2)

        print(f"✅ 成功分析 {title_clean} 的依存句法，结果保存至 {output_json_path}")

    return results

if __name__ == "__main__":
    input_json_path = 'd:\\科研竞赛\\LLM实体冲突识别优化\\航空\\依存句法分析构建规则库\\outputs\\summaries.json'
    
    with open(input_json_path, 'r', encoding='utf-8') as f:
        records = json.load(f)
    
    
    output_dir = 'd:\\科研竞赛\\LLM实体冲突识别优化\\航空\\依存句法分析构建规则库\\dependency_results'
    analyze_dependencies(records, output_dir)

