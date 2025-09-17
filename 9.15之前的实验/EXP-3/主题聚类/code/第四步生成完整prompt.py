import os
import json

# ─── 配置 ─────────────────────────────────────────────────────
PROMPT_TEMPLATE_PATH = "prompt/prompt/prompt.txt"
S_MODULES_DIR        = "数据结果/s_modules"
UNLABELED_DOCS_DIR   = "无标注原文"
OUTPUT_DIR          = "数据结果/完整prompt"

def read_prompt_template():
    """读取prompt模板"""
    with open(PROMPT_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return f.read()

def extract_examples_from_s_module(s_module_path):
    """从S模块中提取示例内容，去掉标题和说明文字"""
    with open(s_module_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 跳过标题部分，从第一个"示例"开始
    lines = content.split('\n')
    examples_lines = []
    start_extracting = False
    
    for line in lines:
        if line.strip().startswith("示例"):
            start_extracting = True
        if start_extracting:
            examples_lines.append(line)
    
    return '\n'.join(examples_lines).strip()

def read_document_content(doc_path):
    """读取文档内容"""
    with open(doc_path, "r", encoding="utf-8") as f:
        return f.read().strip()

def generate_complete_prompt(template, examples, document_content):
    """生成完整的prompt"""
    # 找到"## 输出格式"的位置
    output_format_marker = "## 输出格式\n请严格按照以下JSON格式输出结果："
    
    if output_format_marker in template:
        # 在输出格式前插入示例
        before_output = template.split(output_format_marker)[0]
        after_output = output_format_marker + template.split(output_format_marker)[1]
        
        # 构建完整prompt
        complete_prompt = before_output.strip() + "\n\n"
        
        # 添加Few-Shot示例部分
        if examples:
            complete_prompt += "## Few-Shot示例\n"
            complete_prompt += "以下是相关领域的标注示例，请参考这些示例的标注风格和粒度：\n\n"
            complete_prompt += examples + "\n\n"
        
        # 添加输出格式部分
        complete_prompt += after_output
        
        # 替换文档内容占位符
        complete_prompt = complete_prompt.replace("{full_text_placeholder}", document_content)
        
        return complete_prompt
    else:
        # 如果没找到标记，直接在末尾添加
        complete_prompt = template
        if examples:
            complete_prompt += "\n\n## Few-Shot示例\n"
            complete_prompt += "以下是相关领域的标注示例，请参考这些示例的标注风格和粒度：\n\n"
            complete_prompt += examples
        
        complete_prompt = complete_prompt.replace("{full_text_placeholder}", document_content)
        return complete_prompt

def main():
    """主函数"""
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 读取prompt模板
    template = read_prompt_template()
    
    # 处理每个无标注文档
    for filename in sorted(os.listdir(UNLABELED_DOCS_DIR)):
        if not filename.endswith(".md"):
            continue
        
        print(f"处理文档: {filename}")
        
        # 构建对应的S模块路径
        s_module_filename = f"S_module_{filename.replace('.md', '.txt')}"
        s_module_path = os.path.join(S_MODULES_DIR, s_module_filename)
        
        # 读取文档内容
        doc_path = os.path.join(UNLABELED_DOCS_DIR, filename)
        document_content = read_document_content(doc_path)
        
        # 提取示例（如果存在）
        examples = ""
        if os.path.exists(s_module_path):
            examples = extract_examples_from_s_module(s_module_path)
        else:
            print(f"  ⚠️ 警告: 未找到对应的S模块: {s_module_filename}")
        
        # 生成完整prompt
        complete_prompt = generate_complete_prompt(template, examples, document_content)
        
        # 保存完整prompt
        output_filename = f"prompt_{filename.replace('.md', '.txt')}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(complete_prompt)
        
        print(f"  ✅ 已生成: {output_filename}")
    
    print(f"\n🎉 所有prompt已生成完成，保存在: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()