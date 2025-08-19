# batch_run.py

import os
import json
import re
import requests

# ========== 配置路径 ==========
BASE_DIR = os.path.dirname(__file__)
SOURCE_DIR = os.path.join(BASE_DIR, "数据来源")
OUTPUT_DIR = os.path.join(BASE_DIR, "数据结果")
PROMPT_TEMPLATE_FILE = os.path.join(BASE_DIR, "prompt_tip.txt")
SCHEMA_FILE = os.path.join(BASE_DIR, "schema.json")

# ========== 加载模板 ==========
def load_prompt_template():
    with open(PROMPT_TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        return f.read()

def load_schema_text():
    with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
        return f.read()

# ========== 构造 Prompt ==========
def build_prompt(template: str, full_text: str, schema_text: str) -> str:
    return (template
            .replace('{full_text_placeholder}', full_text)
            .replace('{schema_placeholder}', schema_text))

# ========== 调用 API ==========
def call_deepseek(api_key: str, prompt: str):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "top_p": 1,
        "stream": False,
        "max_tokens": 4096
    }

    try:
        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

        # 提取 JSON 内容
        match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        json_str = match.group(1) if match else content
        return json.loads(json_str)

    except Exception as e:
        print("❌ API调用或解析失败：", e)
        return None

# ========== 主函数 ==========
def main():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("请先设置环境变量 DEEPSEEK_API_KEY")

    prompt_template = load_prompt_template()
    schema_text = load_schema_text()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for filename in sorted(os.listdir(SOURCE_DIR)):
        if filename.endswith(".md") and filename.startswith("paper"):
            paper_id = filename.replace(".md", "")
            source_path = os.path.join(SOURCE_DIR, filename)
            output_path = os.path.join(OUTPUT_DIR, paper_id + ".json")

            # 跳过已处理文件
            if os.path.exists(output_path):
                print(f"✅ 已存在：{paper_id}.json，跳过")
                continue

            # 读取文章内容
            with open(source_path, 'r', encoding='utf-8') as f:
                full_text = f.read()

            # 构造 prompt 并调用 LLM
            prompt = build_prompt(prompt_template, full_text, schema_text)
            print(f"🚀 正在处理 {filename} ...")
            result = call_deepseek(api_key, prompt)

            if result:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=4)
                print(f"✅ 成功生成：{paper_id}.json")
            else:
                print(f"❌ 处理失败：{filename}")

if __name__ == "__main__":
    main()
