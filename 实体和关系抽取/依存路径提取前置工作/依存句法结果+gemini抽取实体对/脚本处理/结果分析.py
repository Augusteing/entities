import os
import json

# --- 1. 配置您的目录路径 ---
# 请根据您的实际情况修改以下三个路径

# 新方法生成的实体对目录 (命名格式: 文章标题+实体对.json 或 文章标题实体对.json)
NEW_PAIRS_DIR = r"E:\知识图谱构建\实体和关系抽取\依存句法结果+gemini抽取实体对\实体对"

# 旧方法生成的实体对目录 (命名格式: 文章标题.json)
OLD_PAIRS_DIR = r"E:\知识图谱构建\实体和关系抽取\依存句法结果+gemini抽取实体对\结果分析\旧实体对"

# 保存对比结果的输出目录 (如果不存在，脚本会自动创建)
OUTPUT_DIR = r"E:\知识图谱构建\实体和关系抽取\依存句法结果+gemini抽取实体对\结果分析\对比结果"


# --- 2. 核心功能函数 (与之前版本相同) ---

def normalize_triplet(triplet_dict):
    """
    将一个实体对字典转换为一个标准化的、可哈希的元组。
    """
    try:
        return (
            triplet_dict.get("subject", "").strip(),
            triplet_dict.get("relation", "").strip(),
            triplet_dict.get("object", "").strip(),
        )
    except AttributeError:
        return tuple(triplet_dict.values())


def compare_entity_files(new_file_path, old_file_path):
    """
    比较两个实体对JSON文件，并返回分析结果。
    """
    try:
        with open(new_file_path, 'r', encoding='utf-8') as f:
            new_data = json.load(f)
        with open(old_file_path, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
    except FileNotFoundError as e:
        print(f"警告：文件未找到，跳过对比 -> {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"警告：JSON解析错误，文件可能已损坏，跳过对比 -> {e.F}")
        return None

    new_set = {normalize_triplet(triplet) for triplet in new_data}
    old_set = {normalize_triplet(triplet) for triplet in old_data}

    common_pairs = new_set.intersection(old_set)
    unique_to_new = new_set.difference(old_set)
    unique_to_old = old_set.difference(new_set)
    
    analysis_result = {
        "document_name": os.path.basename(old_file_path), # 以旧文件名作为基准，更简洁
        "comparison_summary": {
            "total_in_new_method": len(new_set),
            "total_in_old_method": len(old_set),
            "common_pairs_count": len(common_pairs),
            "unique_to_new_method_count": len(unique_to_new),
            "unique_to_old_method_count": len(unique_to_old)
        },
        "common_pairs": [
            {"subject": s, "relation": r, "object": o} for s, r, o in common_pairs
        ],
        "unique_to_new_method": [
            {"subject": s, "relation": r, "object": o} for s, r, o in unique_to_new
        ],
        "unique_to_old_method": [
            {"subject": s, "relation": r, "object": o} for s, r, o in unique_to_old
        ]
    }
    
    return analysis_result


# --- 3. 主执行逻辑 (已更新) ---

def main():
    """
    脚本主函数
    """
    print("开始进行实体对比较...")
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"已创建输出目录: {OUTPUT_DIR}")

    new_files = [f for f in os.listdir(NEW_PAIRS_DIR) if f.endswith('.json')]
    
    if not new_files:
        print(f"警告：在新实体对目录 '{NEW_PAIRS_DIR}' 中未找到任何 .json 文件。")
        return

    print(f"在新目录中找到 {len(new_files)} 个文件，将开始根据命名规则进行匹配和对比。")

    for new_filename in new_files:
        print(f"\n正在处理新文件: {new_filename}")

        # --- 这是本次更新的核心逻辑 ---
        # 通过去除新文件名的后缀来构造旧文件名
        # 这种写法可以同时处理 "文章标题+实体对.json" 和 "文章标题实体对.json"
        if new_filename.endswith('实体对.json'):
            base_name = new_filename.removesuffix('实体对.json')
            # 如果存在 "+", 也一并去除
            if base_name.endswith('+'):
                base_name = base_name.removesuffix('+')
            old_filename = base_name + '.json'
        else:
            print(f"  -> 警告：新文件名 '{new_filename}' 不符合 '...实体对.json' 的预期格式，已跳过。")
            continue
        # --- 更新结束 ---
        
        new_file_full_path = os.path.join(NEW_PAIRS_DIR, new_filename)
        old_file_full_path = os.path.join(OLD_PAIRS_DIR, old_filename)
        
        print(f"  -> 尝试匹配旧文件: {old_filename}")

        if not os.path.exists(old_file_full_path):
            print(f"  -> 警告：在旧目录中未找到对应的文件 '{old_filename}'，已跳过。")
            continue
        
        result = compare_entity_files(new_file_full_path, old_file_full_path)
        
        if result:
            # 使用旧文件名作为输出文件的前缀，更清晰
            output_filename = f"comparison_{old_filename}"
            output_filepath = os.path.join(OUTPUT_DIR, output_filename)
            
            with open(output_filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"  -> 对比完成，结果已保存至: {output_filepath}")

    print("\n所有文件处理完毕！")


if __name__ == "__main__":
    main()