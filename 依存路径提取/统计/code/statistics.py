import os
import json
import logging
from collections import Counter
import pandas as pd
from datetime import datetime

def setup_logging():
    """配置日志功能，同时输出到文件和控制台"""
    script_path = os.path.abspath(__file__)
    code_dir = os.path.dirname(script_path)
    base_dir = os.path.dirname(code_dir)
    log_dir = os.path.join(base_dir, 'dosc')

    os.makedirs(log_dir, exist_ok=True)

    log_filename = f"semantic_pattern_analysis_log_{datetime.now().strftime('%Y-%m-%d')}.txt"
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
    """
    将扁平的依存路径切分为三段式：主体短语、核心关系、客体短语
    """
    if not path_list:
        return None

    root_indices = [i for i, item in enumerate(path_list) if item[1] and item[1].lower() == 'root']
    subject_chunk_words, core_relation_words, object_chunk_words = [], [], []

    if not root_indices:
        core_relation_words = [item[0] for item in path_list]
    elif len(root_indices) == 1:
        idx = root_indices[0]
        subject_chunk_words = [item[0] for item in path_list[:idx]]
        core_relation_words = [path_list[idx][0]]
        object_chunk_words = [item[0] for item in path_list[idx+1:]]
    else:
        first_root_idx, last_root_idx = root_indices[0], root_indices[-1]
        subject_chunk_words = [item[0] for item in path_list[:first_root_idx]]
        core_relation_words = [item[0] for item in path_list[first_root_idx : last_root_idx+1]]
        object_chunk_words = [item[0] for item in path_list[last_root_idx+1:]]

    return {
        "subject_chunk": " ".join(subject_chunk_words),
        "core_relation": " ".join(core_relation_words),
        "object_chunk": " ".join(object_chunk_words)
    }

def main():
    """主执行函数"""
    setup_logging()
    logging.info("脚本开始执行: 提取基于核心关系的路径模式。")

    # --- 路径处理 ---
    script_path = os.path.abspath(__file__)
    code_dir = os.path.dirname(script_path)
    base_dir = os.path.dirname(code_dir)
    result_dir = os.path.join(base_dir, '依存路径提取结果')
    output_dir = os.path.join(base_dir, '统计提取结果') # 新增：定义输出文件夹

    # 新增：确保输出文件夹存在
    os.makedirs(output_dir, exist_ok=True)

    logging.info(f"项目根目录被识别为: {base_dir}")
    logging.info(f"正在从数据目录读取文件: {result_dir}")
    logging.info(f"分析结果将保存到目录: {output_dir}")

    if not os.path.isdir(result_dir):
        logging.error(f"错误：找不到数据目录 '{result_dir}'。请检查文件夹结构。")
        return

    json_files = [f for f in os.listdir(result_dir) if f.endswith('依存路径.json')]
    if not json_files:
        logging.warning(f"在 '{result_dir}' 目录中未找到任何 '...依存路径.json' 文件。")
        return
    logging.info(f"发现 {len(json_files)} 个JSON结果文件。")

    # --- 数据处理 ---
    all_simplified_paths = []
    for filename in json_files:
        filepath = os.path.join(result_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                count = 0
                for pair in data.get('pairs', []):
                    if pair.get('path'):
                        simplified = simplify_path(pair['path'])
                        if simplified and simplified['core_relation']:
                            all_simplified_paths.append({**pair, "simplified": simplified})
                            count += 1
                logging.info(f"从 {filename} 中成功处理了 {count} 条路径。")
        except Exception as e:
            logging.error(f"读取或解析文件 {filename} 时出错: {e}")

    if not all_simplified_paths:
        logging.warning("未能从任何文件中提取出有效的核心关系路径。脚本执行结束。")
        return

    logging.info(f"共聚合了 {len(all_simplified_paths)} 条可供分析的路径。")

    # --- 统计与展示 ---
    core_relation_counts = Counter(p['simplified']['core_relation'] for p in all_simplified_paths)
    logging.info(f"统计出 {len(core_relation_counts)} 种不同的核心关系模式。")

    results = []
    for core, count in core_relation_counts.most_common(20):
        examples = []
        for p in all_simplified_paths:
            if p['simplified']['core_relation'] == core:
                subj_phrase = p['simplified']['subject_chunk']
                obj_phrase = p['simplified']['object_chunk']
                example_str = f"[{p['subject']}]({subj_phrase}) → {core} → [{p['object']}]({obj_phrase})"
                examples.append(example_str)
                if len(examples) >= 2:
                    break
        results.append({
            "核心关系 (Core Relation)": core,
            "出现频次 (Frequency)": count,
            "模式样例 (Pattern Examples)": "; ".join(examples)
        })

    df = pd.DataFrame(results)

    # --- 结果输出 ---
    # 1. 打印到控制台
    print("\n--- 基于“核心关系”的经典路径模式 (Top 20) ---")
    print(df.to_string())
    
    # 2. 新增：保存到文件
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    output_filename = f"semantic_patterns_summary_{timestamp}.csv"
    output_filepath = os.path.join(output_dir, output_filename)
    
    try:
        # 使用 utf_8_sig 编码确保 Excel 能正确识别中文
        df.to_csv(output_filepath, index=False, encoding='utf_8_sig')
        logging.info(f"分析结果已成功保存到文件: {output_filepath}")
        # 在控制台也给出明确提示
        print(f"\n[+] 分析结果已保存到 '统计提取结果' 文件夹下的 '{output_filename}' 文件中。")
    except Exception as e:
        logging.error(f"保存结果文件失败: {e}")
        print(f"\n[!] 保存结果文件失败，错误信息: {e}")
    
    print("\n")
    logging.info("脚本成功执行完毕。")


if __name__ == '__main__':
    main()