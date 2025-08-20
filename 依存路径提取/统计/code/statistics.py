import os
import json
import logging
from collections import Counter
import pandas as pd
from datetime import datetime

def setup_logging(base_dir):
    """配置日志功能，同时输出到文件和控制台"""
    log_dir = os.path.join(base_dir, 'dosc')
    os.makedirs(log_dir, exist_ok=True)
    log_filename = f"semantic_path_pattern_analysis_log_{datetime.now().strftime('%Y-%m-%d')}.txt"
    log_filepath = os.path.join(log_dir, log_filename)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filepath, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logging.info(f"日志将记录到: {log_filepath}")

def simplify_path(path_list):
    """将扁平的依存路径切分为三段式：主体短语、核心关系、客体短语"""
    if not path_list: return None
    root_indices = [i for i, item in enumerate(path_list) if item[1] and item[1].lower() == 'root']
    core_relation_words = []
    if not root_indices:
        core_relation_words = [item[0] for item in path_list]
    elif len(root_indices) == 1:
        core_relation_words = [path_list[root_indices[0]][0]]
    else:
        core_relation_words = [item[0] for item in path_list[root_indices[0] : root_indices[-1]+1]]
    return " ".join(core_relation_words)

def normalize_entity_type(type_str):
    """标准化实体类型标签，处理中英文混用问题"""
    mapping = {
        "研究方法": "Method",
        "研究问题": "Problem",
        "系统/部件": "System/Component",
        "模型": "Model",
        "研究结果": "Finding",
        "性能指标": "Performance Metric",
        "应用场景": "Application",
        "数据集": "Dataset",
        "特征/健康指标": "Sensor/Parameter",
        # 英文标签统一为首字母大写
        "problem": "Problem",
        "method": "Method",
        "model": "Model",
        "tool": "Tool"
    }
    # 统一大小写并查找映射
    normalized = type_str.strip()
    return mapping.get(normalized, normalized)


def main():
    """主执行函数"""
    # --- 路径处理 ---
    try:
        script_path = os.path.abspath(__file__)
        code_dir = os.path.dirname(script_path)
        base_dir = os.path.dirname(code_dir)
    except NameError:
        # 在交互式环境中, __file__ 未定义, 使用当前工作目录
        base_dir = os.getcwd()

    setup_logging(base_dir)
    logging.info("脚本开始执行: 提取语义路径模式。")

    entity_pair_dir = os.path.join(base_dir, '实体对')
    path_result_dir = os.path.join(base_dir, '依存路径提取结果')
    output_dir = os.path.join(base_dir, '统计提取结果')
    os.makedirs(output_dir, exist_ok=True)
    
    logging.info(f"项目根目录: {base_dir}")
    logging.info(f"读取实体对类型: {entity_pair_dir}")
    logging.info(f"读取依存路径: {path_result_dir}")
    logging.info(f"结果将保存到: {output_dir}")

    # --- 1. 读取并标准化所有实体对的类型信息 ---
    type_lookup = {}
    entity_pair_files = [f for f in os.listdir(entity_pair_dir) if f.endswith('实体对.json')]
    for filename in entity_pair_files:
        title = filename.replace('实体对.json', '')
        filepath = os.path.join(entity_pair_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                pairs = json.load(f)
                for pair in pairs:
                    # 使用 (文章标题, subject, object) 作为唯一键
                    key = (title, pair['subject'], pair['object'])
                    subj_type = normalize_entity_type(pair.get('subject_type', 'Unknown'))
                    obj_type = normalize_entity_type(pair.get('object_type', 'Unknown'))
                    type_lookup[key] = (subj_type, obj_type)
        except Exception as e:
            logging.error(f"读取实体对文件 {filename} 失败: {e}")
    logging.info(f"成功加载了 {len(type_lookup)} 个实体对的类型信息。")

    # --- 2. 结合路径信息，生成语义模式 ---
    semantic_patterns = []
    path_result_files = [f for f in os.listdir(path_result_dir) if f.endswith('依存路径.json')]
    for filename in path_result_files:
        title = filename.replace('依存路径.json', '')
        filepath = os.path.join(path_result_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for pair in data.get('pairs', []):
                    if not pair.get('path'): continue
                    
                    key = (title, pair['subject'], pair['object'])
                    subj_type, obj_type = type_lookup.get(key, ('Unknown', 'Unknown'))
                    core_relation = simplify_path(pair['path'])
                    
                    if core_relation:
                        pattern = f"{subj_type} → {core_relation} → {obj_type}"
                        semantic_patterns.append({
                            "pattern": pattern,
                            "subject": pair['subject'],
                            "relation": pair.get('relation', 'N/A'),
                            "object": pair['object']
                        })
        except Exception as e:
            logging.error(f"读取路径文件 {filename} 失败: {e}")

    logging.info(f"成功生成了 {len(semantic_patterns)} 条语义路径。")

    # --- 3. 统计与展示 ---
    pattern_counts = Counter(p['pattern'] for p in semantic_patterns)
    logging.info(f"统计出 {len(pattern_counts)} 种不同的语义路径模式。")

    results = []
    for pattern, count in pattern_counts.most_common(20):
        examples = []
        for p in semantic_patterns:
            if p['pattern'] == pattern:
                examples.append(f"[{p['subject']}]--({p['relation']})-->[{p['object']}]")
                if len(examples) >= 2: break
        results.append({
            "语义路径模式 (Semantic Path Pattern)": pattern,
            "出现频次 (Frequency)": count,
            "样例 (Examples)": "; ".join(examples)
        })
    
    df = pd.DataFrame(results)

    # --- 4. 结果输出 ---
    print("\n--- 经典语义路径模式 (Top 20) ---")
    print(df.to_string())
    
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    output_filename = f"semantic_path_patterns_summary_{timestamp}.csv"
    output_filepath = os.path.join(output_dir, output_filename)
    try:
        df.to_csv(output_filepath, index=False, encoding='utf_8_sig')
        logging.info(f"分析结果已成功保存到文件: {output_filepath}")
        print(f"\n[+] 分析结果已保存到 '统计提取结果' 文件夹下的 '{output_filename}' 文件中。")
    except Exception as e:
        logging.error(f"保存结果文件失败: {e}")
        print(f"\n[!] 保存结果文件失败，错误信息: {e}")
    
    print("\n")
    logging.info("脚本成功执行完毕。")

if __name__ == '__main__':
    main()