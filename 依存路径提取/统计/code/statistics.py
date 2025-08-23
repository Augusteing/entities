import os
import json
import logging
from collections import Counter, defaultdict
import pandas as pd
from datetime import datetime

def setup_logging(base_dir):
    """配置日志功能，同时输出到文件和控制台"""
    log_dir = os.path.join(base_dir, 'dosc')
    os.makedirs(log_dir, exist_ok=True)
    log_filename = f"semantic_syntactic_pattern_analysis_log_{datetime.now().strftime('%Y-%m-%d')}.txt"
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

def get_syntactic_path_key(path_list):
    """将依存路径列表转换为用于统计的key（仅含依存关系）"""
    if not path_list: return "N/A"
    deprels = [item[1] for item in path_list if item[1] is not None]
    return "->".join(d.lower() for d in deprels)

def format_display_path(path_list):
    """将依存路径列表转换为用于展示的字符串：Word(deprel) — Word(deprel)"""
    if not path_list: return "N/A"
    display_parts = [f"{item[0]}({item[1] or 'N/A'})" for item in path_list]
    return " — ".join(display_parts)

def normalize_entity_type(type_str):
    """标准化实体类型标签，处理中英文混用问题"""
    if not isinstance(type_str, str): return "Unknown"
    mapping = {
        "研究方法": "Method", "研究问题": "Problem", "系统/部件": "System/Component",
        "模型": "Model", "研究结果": "Finding", "性能指标": "Performance Metric",
        "应用场景": "Application", "数据集": "Dataset", "特征/健康指标": "Sensor/Parameter",
        "problem": "Problem", "method": "Method", "model": "Model", "tool": "Tool"
    }
    normalized = type_str.strip()
    return mapping.get(normalized, normalized)

def main():
    """主执行函数"""
    try:
        script_path = os.path.abspath(__file__)
        code_dir = os.path.dirname(script_path)
        base_dir = os.path.dirname(code_dir)
    except NameError:
        base_dir = os.getcwd()

    setup_logging(base_dir)
    logging.info("脚本开始执行: 分析'语义-句法'对应模式。")

    entity_pair_dir = os.path.join(base_dir, '实体对')
    path_result_dir = os.path.join(base_dir, '依存路径提取结果')
    output_dir = os.path.join(base_dir, '统计提取结果')
    os.makedirs(output_dir, exist_ok=True)

    logging.info(f"读取实体对(含类型和关系): {entity_pair_dir}")
    logging.info(f"读取依存路径: {path_result_dir}")

    # --- 1. 读取并标准化所有实体对的类型和关系信息 ---
    ground_truth_lookup = {}
    entity_pair_files = [f for f in os.listdir(entity_pair_dir) if f.endswith('实体对.json')]
    for filename in entity_pair_files:
        title = filename.replace('实体对.json', '')
        filepath = os.path.join(entity_pair_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                pairs = json.load(f)
                for pair in pairs:
                    key = (title, pair['subject'], pair['object'])
                    subj_type = normalize_entity_type(pair.get('subject_type', 'Unknown'))
                    obj_type = normalize_entity_type(pair.get('object_type', 'Unknown'))
                    relation = pair.get('relation', 'N/A')
                    ground_truth_lookup[key] = (subj_type, obj_type, relation)
        except Exception as e:
            logging.error(f"读取实体对文件 {filename} 失败: {e}")
    logging.info(f"成功加载了 {len(ground_truth_lookup)} 个实体对的真值信息。")

    # --- 2. 聚合数据: 将语义真值和句法路径关联 ---
    analysis_data = defaultdict(list)
    path_result_files = [f for f in os.listdir(path_result_dir) if f.endswith('依存路径.json')]
    for filename in path_result_files:
        title = filename.replace('依存路径.json', '')
        filepath = os.path.join(path_result_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for pair in data.get('pairs', []):
                    key = (title, pair['subject'], pair['object'])
                    subj_type, obj_type, relation = ground_truth_lookup.get(key, ('Unknown', 'Unknown', 'N/A'))
                    
                    semantic_pattern = f"{subj_type} → {relation} → {obj_type}"
                    
                    full_path = pair.get('path')
                    if not full_path: continue

                    analysis_data[semantic_pattern].append({
                        "syntactic_key": get_syntactic_path_key(full_path),
                        "display_path": format_display_path(full_path),
                        "example": f"[{pair['subject']}] → [{pair['object']}]"
                    })
        except Exception as e:
            logging.error(f"读取路径文件 {filename} 失败: {e}")
    logging.info(f"成功关联了 {sum(len(v) for v in analysis_data.values())} 条数据。")

    # --- 3. 整理与展示 ---
    final_results = []
    sorted_patterns = sorted(analysis_data.items(), key=lambda item: len(item[1]), reverse=True)

    for semantic_pattern, instances in sorted_patterns:
        total_frequency = len(instances)
        # 统计每种句法路径key的频次
        syntactic_key_counts = Counter(inst['syntactic_key'] for inst in instances)
        
        syntactic_details = []
        # 为了展示，我们需要将key映射回一个具体的display_path
        key_to_display_map = {inst['syntactic_key']: inst['display_path'] for inst in instances}
        key_to_example_map = {inst['syntactic_key']: inst['example'] for inst in instances}

        for syntactic_key, count in syntactic_key_counts.most_common():
            display_path = key_to_display_map.get(syntactic_key, "N/A")
            example = key_to_example_map.get(syntactic_key, "")
            syntactic_details.append(f"  - 句法路径: {display_path} (频次: {count}, 样例: {example})")

        final_results.append({
            "语义模式 (Semantic Pattern)": semantic_pattern,
            "总频次 (Total Freq)": total_frequency,
            "句法实现路径 (Syntactic Realizations)": "\n".join(syntactic_details)
        })

    df = pd.DataFrame(final_results)
    df_top20 = df.head(20)

    # --- 4. 结果输出 ---
    print("\n--- 经典'语义-句法'模式对应报告 (Top 20) ---")
    for index, row in df_top20.iterrows():
        print("="*80)
        print(f"语义模式: {row['语义模式 (Semantic Pattern)']} (总频次: {row['总频次 (Total Freq)']})")
        print("句法实现:")
        print(row['句法实现路径 (Syntactic Realizations)'])
    
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    output_filename = f"semantic_syntactic_patterns_report_{timestamp}.csv"
    output_filepath = os.path.join(output_dir, output_filename)
    try:
        df.to_csv(output_filepath, index=False, encoding='utf_8_sig')
        logging.info(f"分析报告已成功保存到文件: {output_filepath}")
        print(f"\n[+] 完整分析报告已保存到 '统计提取结果' 文件夹下的 '{output_filename}' 文件中。")
    except Exception as e:
        logging.error(f"保存结果文件失败: {e}")
    
    print("\n")
    logging.info("脚本成功执行完毕。")

if __name__ == '__main__':
    main()