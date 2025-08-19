import os
import json
import re
import requests

# 加载 Prompt 并填充 full_text 与 schema
def load_and_prepare_prompt(prompt_filepath: str, full_text: str, schema_text: str) -> str:
    with open(prompt_filepath, 'r', encoding='utf-8') as f:
        prompt_template = f.read()

    # 校验模板格式
    for placeholder in ['{full_text_placeholder}', '{schema_placeholder}']:
        if placeholder not in prompt_template:
            raise ValueError(f"Prompt 模板中缺少占位符: {placeholder}")

    # 替换
    prompt_filled = prompt_template.replace('{full_text_placeholder}', full_text)
    prompt_filled = prompt_filled.replace('{schema_placeholder}', schema_text)
    return prompt_filled

# 调用 DeepSeek API
def call_llm_api(api_key: str, final_prompt: str) -> dict:
    print("🔁 调用 DeepSeek API...")
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": final_prompt}],
        "temperature": 0.3,
        "top_p": 1,
        "stream": False,
        "max_tokens": 4096
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']

        # 抽取 JSON 格式内容
        match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
        json_str = match.group(1).strip() if match else content.strip()
        return json.loads(json_str)

    except requests.HTTPError as e:
        print(f"❌ HTTP 错误: {e.response.status_code} - {e.response.text}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解码失败: {e}")
        print("原始返回内容：", content)
    except Exception as e:
        print(f"❌ 其他错误: {e}")

    return None

# 主函数
if __name__ == "__main__":
    # 读取 API KEY
    API_KEY = os.getenv("DEEPSEEK_API_KEY")
    if not API_KEY:
        raise ValueError("❌ 请设置环境变量 DEEPSEEK_API_KEY")

    # 路径配置
    INPUT_MD_FILE = "full.md"
    SCHEMA_FILE = "schema.json"
    PROMPT_TEMPLATE_FILE = "prompt_tip.txt"

    try:
        # 读取文件
        with open(INPUT_MD_FILE, 'r', encoding='utf-8') as f:
            full_text = f.read()
        with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
            schema_text = f.read()

        # 构建 Prompt
        final_prompt = load_and_prepare_prompt(
            PROMPT_TEMPLATE_FILE, full_text, schema_text
        )

        # 调用模型
        llm_output = call_llm_api(API_KEY, final_prompt)

        # 保存输出
        if llm_output:
            output_file = INPUT_MD_FILE.replace(".md", "_extracted_output.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(llm_output, f, ensure_ascii=False, indent=4)
            print(f"✅ 成功：结果保存在 {output_file}")
        else:
            print("❌ 没有返回结果")
    except Exception as e:
        print(f"❌ 运行错误: {e}")
