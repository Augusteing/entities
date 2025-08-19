import os
import json

def create_empty_json_files():
    """
    读取指定文件夹中特定格式的JSON文件，并在另一个文件夹中创建对应的空白JSON文件。
    """
    # --- 1. 定义路径 ---
    # 源文件夹路径
    source_directory = r"E:\知识图谱构建\实体和关系抽取\依存句法结果+gemini抽取实体对（无实体定义）\依存句法分析结果"
    
    # 目标文件夹路径
    destination_directory = r"E:\知识图谱构建\实体和关系抽取\依存句法结果+gemini抽取实体对（无实体定义）\实体对"

    # 定义用于匹配和创建的文件名后缀
    input_suffix = "_dependency_entities.json"
    output_suffix = "实体对.json"

    # --- 2. 检查并创建目标文件夹 ---
    try:
        if not os.path.exists(destination_directory):
            os.makedirs(destination_directory)
            print(f"成功创建目标文件夹: {destination_directory}")
    except OSError as e:
        print(f"错误：无法创建目标文件夹。{e}")
        return

    # --- 3. 检查源文件夹是否存在 ---
    if not os.path.isdir(source_directory):
        print(f"错误：源文件夹不存在: {source_directory}")
        return

    print(f"正在扫描源文件夹: {source_directory}")

    # --- 4. 遍历文件并创建新文件 ---
    # 获取源文件夹中的所有文件名
    try:
        files = os.listdir(source_directory)
    except FileNotFoundError:
        print(f"错误：无法访问源文件夹。请检查路径是否正确。")
        return

    created_count = 0
    for filename in files:
        # 检查文件名是否以指定的后缀结尾
        if filename.endswith(input_suffix):
            # 从文件名中提取文献标题部分
            # 例如, 从 "文献标题_dependency_entities.json" 提取 "文献标题"
            document_title = filename[:-len(input_suffix)]
            
            # 构建新的文件名
            new_filename = f"{document_title}{output_suffix}"
            
            # 构建新文件的完整路径
            new_filepath = os.path.join(destination_directory, new_filename)
            
            # 创建并写入一个空的JSON对象 {}
            try:
                with open(new_filepath, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=4)
                print(f"已创建文件: {new_filepath}")
                created_count += 1
            except IOError as e:
                print(f"错误：无法创建文件 {new_filename}。 {e}")

    if created_count == 0:
        print("\n在源文件夹中没有找到匹配的文件。")
    else:
        print(f"\n任务完成！总共创建了 {created_count} 个文件。")


# --- 运行主函数 ---
if __name__ == "__main__":
    create_empty_json_files()