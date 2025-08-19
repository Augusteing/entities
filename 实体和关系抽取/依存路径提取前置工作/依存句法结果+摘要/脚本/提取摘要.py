import os
import re

# --- 1. 配置您的文件和目录路径 ---
# 请根据您的实际情况修改以下路径

# 包含所有文献摘要的总TXT文件
ABSTRACTS_FILE_PATH = r"E:\知识图谱构建\文献信息\PHM-217篇摘要.txt"

# 存放JSON文件的目录
JSON_FILES_DIR = r"E:\知识图谱构建\实体和关系抽取\依存句法结果+摘要\依存句法分析结果"

# 保存抽取出的摘要的输出目录 (如果不存在，脚本会自动创建)
OUTPUT_ABSTRACTS_DIR = r"E:\知识图谱构建\实体和关系抽取\依存句法结果+摘要\摘要"


# --- 2. 核心功能函数 ---

def parse_all_abstracts(file_path):
    """
    解析包含所有摘要的TXT文件，返回一个 标题->摘要 的字典。
    """
    print(f"正在从 '{file_path}' 解析所有文献摘要...")
    abstracts_map = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 使用'DataType: 1'作为每篇文献记录的开始分隔符
        articles = content.split('DataType: 1')
        
        for article_text in articles:
            if not article_text.strip():
                continue
            
            # 使用正则表达式提取标题和摘要
            title_match = re.search(r"Title-题名:\s*(.+)", article_text)
            summary_match = re.search(r"Summary-摘要:\s*([\s\S]+?)(?=\n[A-Z][a-zA-Z]+-|\Z)", article_text)

            if title_match and summary_match:
                title = title_match.group(1).strip()
                summary = summary_match.group(1).strip()
                abstracts_map[title] = summary
                
    except FileNotFoundError:
        print(f"错误：摘要总文件未找到 -> {file_path}")
        return None
    except Exception as e:
        print(f"解析摘要文件时出错: {e}")
        return None
        
    print(f"成功解析 {len(abstracts_map)} 篇文献摘要。")
    return abstracts_map


def extract_title_from_json_filename(json_filename):
    """
    从JSON文件名中提取文献标题。
    例如：'文章标题_dependency_entities.json' -> '文章标题'
    """
    suffix_to_remove = "_dependency_entities.json"
    if json_filename.endswith(suffix_to_remove):
        return json_filename[:-len(suffix_to_remove)]
    return None


# --- 3. 主执行逻辑 ---

def main():
    """
    脚本主函数
    """
    # 确保输出目录存在
    if not os.path.exists(OUTPUT_ABSTRACTS_DIR):
        os.makedirs(OUTPUT_ABSTRACTS_DIR)
        print(f"已创建摘要输出目录: {OUTPUT_ABSTRACTS_DIR}")

    # 第一步：解析所有摘要，存入内存
    all_abstracts = parse_all_abstracts(ABSTRACTS_FILE_PATH)
    if all_abstracts is None:
        print("因无法解析摘要文件，程序终止。")
        return

    # 第二步：遍历JSON文件目录
    json_filenames = [f for f in os.listdir(JSON_FILES_DIR) if f.endswith('.json')]

    if not json_filenames:
        print(f"警告：在JSON目录 '{JSON_FILES_DIR}' 中未找到任何 .json 文件。")
        return

    print(f"\n在JSON目录中找到 {len(json_filenames)} 个文件，将开始匹配和提取摘要。")
    
    extracted_count = 0
    not_found_count = 0

    # 第三步：对每个JSON文件进行处理
    for json_filename in json_filenames:
        # 从JSON文件名中提取标题
        title = extract_title_from_json_filename(json_filename)
        
        if not title:
            print(f"  -> 警告：无法从 '{json_filename}' 提取标题，已跳过。")
            continue

        # 在摘要库中查找对应的摘要
        if title in all_abstracts:
            summary_text = all_abstracts[title]
            
            # 构造输出文件名（去除不适合做文件名的字符）
            safe_title_filename = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).rstrip()
            output_filepath = os.path.join(OUTPUT_ABSTRACTS_DIR, f"{safe_title_filename}.txt")
            
            # 将摘要写入新的TXT文件
            try:
                with open(output_filepath, 'w', encoding='utf-8') as f:
                    f.write(summary_text)
                print(f"  -> 成功提取 '{title}' 的摘要，已保存。")
                extracted_count += 1
            except Exception as e:
                print(f"  -> 错误：无法写入文件 {output_filepath}。原因: {e}")
        else:
            print(f"  -> 警告：在摘要库中未找到标题为 '{title}' 的文献。")
            not_found_count += 1
            
    print(f"\n处理完成！共成功提取 {extracted_count} 篇摘要，{not_found_count} 篇未找到匹配项。")


if __name__ == "__main__":
    main()