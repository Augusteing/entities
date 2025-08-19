import os
import json
import re
import requests
import time

# --- 配置路径 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 源文件夹现在是包含md和仅实体json的地方
SOURCE_ANNOTATION_DIR = os.path.join(BASE_DIR, "自我标注数据") 
# 我们将把增强后的结果保存在一个新的文件夹中，以防覆盖原始文件
ENRICHED_OUTPUT_DIR = os.path.join(BASE_DIR, "自我标注数据_已增强关系")
PROMPT_TEMPLATE_FILE = os.path.join(BASE_DIR, "prompt_for_relations.txt") # <-- 使用新的Prompt模板
SCHEMA_FILE = os.path.join(BASE_DIR, "schema.json")

# --- 辅助函数 (基本与之前脚本相同) ---
def load_prompt_template():
    with open(PROMPT_TEMPLATE_FILE, 'r', encoding='utf-8') as f: return f.read()
def load_schema_text():
    with open(SCHEMA_FILE, 'r', encoding='utf-8') as f: return f.read()

def build_relation_prompt(template, full_text, schema_text, entities_json_str):
    return (template
            .replace('{full_text_placeholder}', full_text)
            .replace('{schema_placeholder}', schema_text)
            .replace('{entities_placeholder}', entities_json_str))

def call_deepseek(api_key, prompt):
    # (这个函数与之前的版本完全相同，此处省略以保持简洁，实际使用时请复制过来)
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "top_p": 1, "stream": False, "max_tokens": 4096}
    try:
        resp = requests.post(url, headers=headers, json=payload); resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL); json_str = match.group(1) if match else content
        try: return json.loads(json_str)
        except json.JSONDecodeError: return {"raw_output": json_str}
    except Exception as e: print(f"❌ API调用或解析失败：{e}"); return None

# --- 主逻辑 ---
def main():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key: raise ValueError("请先设置环境变量 DEEPSEEK_API_KEY")

    prompt_template = load_prompt_template()
    schema_text = load_schema_text()
    os.makedirs(ENRICHED_OUTPUT_DIR, exist_ok=True)

    print("🚀 开始关系增强流程...")

    for filename in sorted(os.listdir(SOURCE_ANNOTATION_DIR)):
        if filename.endswith(".json"):
            json_path = os.path.join(SOURCE_ANNOTATION_DIR, filename)
            md_path = os.path.join(SOURCE_ANNOTATION_DIR, filename.replace('.json', '.md'))
            output_path = os.path.join(ENRICHED_OUTPUT_DIR, filename)

            if not os.path.exists(md_path):
                print(f"⚠️ 找不到 {filename} 对应的原文 {md_path}，跳过。")
                continue
            
            if os.path.exists(output_path):
                print(f"✅ 已存在增强版文件 {filename}，跳过。")
                continue

            # 1. 加载原文和仅有实体的JSON
            with open(md_path, 'r', encoding='utf-8') as f: full_text = f.read()
            with open(json_path, 'r', encoding='utf-8') as f: original_data = json.load(f)
            
            entities_list = original_data.get("entities", [])
            if not entities_list:
                print(f"ℹ️ {filename} 中没有实体，无法抽取关系，跳过。")
                continue
                
            entities_json_str = json.dumps(entities_list, ensure_ascii=False, indent=4)

            # 2. 构建新的Prompt并调用API
            print(f"🔍 正在为《{filename}》中的实体寻找关系...")
            prompt = build_relation_prompt(prompt_template, full_text, schema_text, entities_json_str)
            relations_result = call_deepseek(api_key, prompt)

            # 3. 合并结果并保存
            if relations_result and 'relations' in relations_result:
                # 将模型生成的关系列表合并回原始数据
                original_data['relations'] = relations_result['relations']
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(original_data, f, ensure_ascii=False, indent=4)
                print(f"✅ 成功为《{filename}》增强关系并保存！")
            else:
                print(f"❌ 未能为《{filename}》获取有效关系。")
            
            time.sleep(1) # 增加一个小的延时，避免API调用过于频繁

if __name__ == "__main__":
    main()