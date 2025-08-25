# -*- coding: utf-8 -*-
# 文件：code/提取脚本.py
import os
import json
import time
from datetime import datetime, timezone

# 使用 OpenAI 官方 SDK 直连 DeepSeek
from openai import OpenAI

# ------------------------------
# 路径配置
# ------------------------------
CODE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CODE_DIR)

SCHEMA_FILE = os.path.join(BASE_DIR, "schema文件", "schema.txt")
PROMPT_FILE = os.path.join(BASE_DIR, "prompt", "prompt.txt")
PAPERS_DIR = os.path.join(BASE_DIR, "论文文献")
OUTPUT_DIR = os.path.join(BASE_DIR, "数据结果")
PROMPT_LOG_DIR = os.path.join(OUTPUT_DIR, "prompts")       # 保存每篇论文的 prompt
PROMPT_LOG_FILE = os.path.join(OUTPUT_DIR, "prompt_log.ndjson")  # 全局 prompt 日志（追加）
RUN_LOG_FILE = os.path.join(OUTPUT_DIR, "run_log.ndjson")  # 全局运行日志（追加）

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PROMPT_LOG_DIR, exist_ok=True)

MODEL_NAME = "deepseek-chat"  # 可按需改为 deepseek-reasoner

# ------------------------------
# 工具函数
# ------------------------------
def strip_code_fences(s: str) -> str:
    """去除```json ... ```样式的围栏，并移除语言行"""
    if not isinstance(s, str):
        return s
    s = s.strip()
    if s.startswith("```") and s.endswith("```"):
        s = s[3:-3].strip()
        # 可能以语言标记开头，比如 "json"
        if "\n" in s:
            first_line, rest = s.split("\n", 1)
            if first_line.strip().lower() in {"json", "js", "javascript"}:
                s = rest
    return s

def parse_strict_json(content: str):
    """将模型输出解析为严格 JSON，自动剥离代码围栏"""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        cleaned = strip_code_fences(content)
        return json.loads(cleaned)

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _usage_to_dict(usage_obj):
    """尽量把 usage 转为 dict。"""
    if usage_obj is None:
        return None
    try:
        if hasattr(usage_obj, "model_dump"):
            return usage_obj.model_dump()
        if hasattr(usage_obj, "to_dict"):
            return usage_obj.to_dict()
        if isinstance(usage_obj, dict):
            return usage_obj
        # 尝试提取常见字段
        keys = ("prompt_tokens", "completion_tokens", "total_tokens")
        d = {k: getattr(usage_obj, k) for k in keys if hasattr(usage_obj, k)}
        return d or str(usage_obj)
    except Exception:
        return str(usage_obj)

def append_run_log(item: dict):
    with open(RUN_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

def save_prompt(paper_file: str, prompt_text: str) -> str:
    """保存单篇论文的 prompt，并写入全局日志，返回 prompt 文件路径"""
    prompt_path = os.path.join(PROMPT_LOG_DIR, paper_file.replace(".md", "_prompt.txt"))
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt_text)

    log_item = {
        "time": now_iso(),
        "paper": paper_file,
        "prompt_file": prompt_path
    }
    with open(PROMPT_LOG_FILE, "a", encoding="utf-8") as logf:
        logf.write(json.dumps(log_item, ensure_ascii=False) + "\n")

    return prompt_path

# ------------------------------
# 加载 schema 和 prompt
# ------------------------------
with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
    schema_data = f.read()

with open(PROMPT_FILE, "r", encoding="utf-8") as f:
    prompt_template = f.read()

# ------------------------------
# 初始化 DeepSeek 客户端（通过 OpenAI SDK 直连）
# ------------------------------
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise ValueError("请先在环境变量中设置 DEEPSEEK_API_KEY")

client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

# ------------------------------
# 获取所有论文文件
# ------------------------------
papers = sorted(f for f in os.listdir(PAPERS_DIR) if f.endswith(".md"))
print(f"找到 {len(papers)} 篇论文：{papers}")

# ------------------------------
# 批量提交
# ------------------------------
success, failed = 0, 0
aborted_for_balance = False

for paper_file in papers:
    # 输出文件路径（支持断点续跑）
    output_file = os.path.join(OUTPUT_DIR, paper_file.replace(".md", ".json"))
    if os.path.exists(output_file):
        print(f"已存在结果，跳过：{paper_file}")
        append_run_log({
            "time": now_iso(),
            "paper": paper_file,
            "status": "skipped",
            "reason": "exists",
            "output": output_file
        })
        continue

    paper_path = os.path.join(PAPERS_DIR, paper_file)
    with open(paper_path, "r", encoding="utf-8") as f:
        paper_text = f.read()

    # 填充 prompt（占位符替换）
    prompt_filled = (
        prompt_template
        .replace("{schema_placeholder}", schema_data)
        .replace("{full_text_placeholder}", paper_text)
    )

    # 记录 prompt
    prompt_file_path = save_prompt(paper_file, prompt_filled)

    print(f"提交论文：{paper_file} ...")

    # 轻量重试
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "你是信息抽取助手，只输出严格的 JSON，不要添加多余文本。"},
                    {"role": "user", "content": prompt_filled}
                ],
                temperature=0,
                response_format={"type": "json_object"}  # 强制 JSON 输出
            )
            content = resp.choices[0].message.content
            data = parse_strict_json(content)
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 日志：成功与用量
            append_run_log({
                "time": now_iso(),
                "paper": paper_file,
                "status": "success",
                "output": output_file,
                "model": MODEL_NAME,
                "usage": _usage_to_dict(getattr(resp, "usage", None))
            })

            print(f"结果已保存到 {output_file}；对应 prompt 已记录：{prompt_file_path}")
            success += 1
            break  # 成功则跳出重试
        except Exception as e:
            msg = str(e)
            # 余额不足：HTTP 402 或错误信息包含关键词，直接中止后续任务
            if ("402" in msg) or ("Insufficient Balance" in msg) or ("insufficient balance" in msg.lower()):
                print(f"余额不足，终止后续任务：{msg}")
                append_run_log({
                    "time": now_iso(),
                    "paper": paper_file,
                    "status": "aborted_balance",
                    "error": msg
                })
                aborted_for_balance = True
                break
            is_last = (attempt == max_retries - 1)
            print(f"第 {attempt+1}/{max_retries} 次尝试失败：{msg}{'（已放弃）' if is_last else '，重试中…'}")
            if is_last:
                # 失败也保留 prompt 记录，便于复现
                fail_flag = output_file.replace(".json", ".failed.txt")
                with open(fail_flag, "w", encoding="utf-8") as ff:
                    ff.write(f"失败时间: {now_iso()}\n异常: {msg}\nPrompt文件: {prompt_file_path}\n")
                append_run_log({
                    "time": now_iso(),
                    "paper": paper_file,
                    "status": "failed",
                    "error": msg,
                    "fail_flag": fail_flag
                })
                failed += 1
            else:
                # 指数退避
                time.sleep(2 ** attempt)

    if aborted_for_balance:
        break

    # 轻限速（可按需调整或移除）
    time.sleep(1)

print(f"批量提交完成。成功: {success}，失败: {failed}，{'因余额不足提前终止' if aborted_for_balance else '全部处理完成'}。")