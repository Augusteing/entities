# -*- coding: utf-8 -*-
"""
批量发送脚本：
- 遍历 BASE_DIR/gemini 下的 .json 文件（最多 50 个，可用 --max 调整）
- 统一使用 BASE_DIR/prompt/prompt.txt 作为评估 Prompt（不再按文件同名查找）
- 通过 hiapi.online 的 OpenAI 兼容接口（与 exact_gemini.py 相同方式）调用 Gemini
- 保存响应到 数据结果/发送结果_by_gemini，记录日志与耗时

运行示例（PowerShell）：
    $env:HIAPI_API_KEY = "sk-xxxxx" ; python ./code/send_gemini_batch.py --max 50 --model gemini-2.5-pro
"""

import os
import json
import time
import argparse
from datetime import datetime, timezone

from openai import OpenAI


# ------------------------------
# 路径配置
# ------------------------------
CODE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CODE_DIR)

DEFAULT_PROMPT_FILE = os.path.join(BASE_DIR, "prompt", "prompt.txt")
GEMINI_INPUT_DIR = os.path.join(BASE_DIR, "gemini")

DATA_RESULT_DIR = os.path.join(BASE_DIR, "数据结果")
SEND_RESULT_DIR = os.path.join(DATA_RESULT_DIR, "发送结果_by_gemini")
LOG_DIR = os.path.join(DATA_RESULT_DIR, "log")
MAIN_LOG_FILE = os.path.join(LOG_DIR, "send_log.ndjson")
TIMING_FILE = os.path.join(LOG_DIR, "send_timings.ndjson")

os.makedirs(DATA_RESULT_DIR, exist_ok=True)
os.makedirs(SEND_RESULT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)


# ------------------------------
# 默认模型配置（可通过命令行覆盖）
# ------------------------------
DEFAULT_MODEL_NAME = "gemini-2.5-pro"
PROVIDER_NAME = "gemini"


# ------------------------------
# 工具函数
# ------------------------------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _usage_to_dict(usage_obj):
    if usage_obj is None:
        return None
    try:
        if hasattr(usage_obj, "model_dump"):
            return usage_obj.model_dump()
        if hasattr(usage_obj, "to_dict"):
            return usage_obj.to_dict()
        if isinstance(usage_obj, dict):
            return usage_obj
        keys = ("prompt_tokens", "completion_tokens", "total_tokens")
        d = {k: getattr(usage_obj, k) for k in keys if hasattr(usage_obj, k)}
        return d or str(usage_obj)
    except Exception:
        return str(usage_obj)


def append_run_log(item: dict):
    with open(MAIN_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def append_timing(item: dict):
    with open(TIMING_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def _mask_key(k: str) -> str:
    if not k or len(k) < 8:
        return "***"
    return f"{k[:6]}...{k[-4:]}"


def strip_code_fences(s: str) -> str:
    """去除```json ... ```样式的围栏，并移除语言行"""
    if not isinstance(s, str):
        return s
    s = s.strip()
    if s.startswith("```") and s.endswith("```"):
        s = s[3:-3].strip()
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


def find_prompt_for_json(json_path: str) -> str:
    """统一返回全局评估 Prompt：BASE_DIR/prompt/prompt.txt"""
    return DEFAULT_PROMPT_FILE


def build_messages(prompt_text: str, json_text: str) -> list:
    """构造对话消息：将 prompt 与 JSON 文本一并发给模型。
    注意：不强制 JSON 响应格式，避免与用户自定义 prompt 冲突。
    """
    content = (
        f"{prompt_text}\n\n"
        f"以下是输入数据(JSON)：\n"
        f"{json_text.strip()}\n"
    )
    return [
        {"role": "system", "content": "你是一个专业助手，请严格按照用户的指令处理输入数据。"},
        {"role": "user", "content": content},
    ]


def main():
    parser = argparse.ArgumentParser(description="批量把 gemini/ 下的 JSON + prompt 发送到 Gemini")
    parser.add_argument("--input-dir", default=GEMINI_INPUT_DIR, help="输入目录（包含 .json 与同名 prompt）")
    parser.add_argument("--max", type=int, default=50, help="最多处理的文件数")
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME, help="模型名称，例如 gemini-2.5-pro")
    parser.add_argument("--force-json-output", action="store_true", help="尝试使用 response_format 强制 JSON 输出（如不支持将自动降级）")
    parser.add_argument("--overwrite", action="store_true", help="存在结果时是否覆盖")
    args = parser.parse_args()

    input_dir = os.path.abspath(args.input_dir)
    if not os.path.isdir(input_dir):
        raise FileNotFoundError(f"找不到输入目录：{input_dir}")

    # 读取并校验 API Key
    api_key_source = None
    for _var in ("HIAPI_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "API_KEY"):
        _v = os.getenv(_var)
        if _v:
            api_key = _v.strip()
            api_key_source = _var
            break
    else:
        api_key = None

    if not api_key:
        raise ValueError("未检测到 API Key。请设置 HIAPI_API_KEY（或 GEMINI_API_KEY/OPENAI_API_KEY/API_KEY）。")

    # base_url 处理：默认 https://hiapi.online/v1，可被 HIAPI_BASE_URL 覆盖
    _base_env = os.getenv("HIAPI_BASE_URL")
    if _base_env:
        _base_clean = _base_env.rstrip("/")
        base_url = _base_clean if _base_clean.endswith("/v1") else _base_clean + "/v1"
    else:
        base_url = "https://hiapi.online/v1"

    if "hiapi.online" in (base_url or "") and not api_key.lower().startswith("sk-"):
        raise ValueError(
            f"当前 base_url={base_url} 指向 hiapi.online，但从 {api_key_source} 读取到的 Key 看起来不是 sk- 开头：{_mask_key(api_key)}。\n"
            "请到 hiapi 后台复制以 sk- 开头的密钥，并设置到 HIAPI_API_KEY。"
        )

    client = OpenAI(api_key=api_key, base_url=base_url)

    # 预检
    try:
        models_res = client.models.list()
        models_cnt = len(getattr(models_res, "data", []) or [])
        print(
            f"预检通过：已连接 {base_url}（模型数≈{models_cnt}）。Key 来源={api_key_source}，Key 掩码={_mask_key(api_key)}"
        )
    except Exception as _e:
        _msg = str(_e)
        if ("401" in _msg) or ("unauthorized" in _msg.lower()) or ("invalid" in _msg.lower()):
            raise RuntimeError(
                "预检失败：鉴权未通过(401)。请确认 base_url、环境变量与 Key 有效后重试。"
            )
        else:
            print("预检警告：/models 不可用或返回非 401 错误，将继续执行。详情：" + _msg)

    # 收集 JSON 输入文件
    all_files = [
        f for f in sorted(os.listdir(input_dir))
        if f.lower().endswith(".json") and os.path.isfile(os.path.join(input_dir, f))
    ]

    if not all_files:
        print(f"在 {input_dir} 未找到 .json 文件。")
        return

    # 限制数量
    target_files = all_files[: max(args.max, 0)]
    print(f"待发送 JSON 数量：{len(target_files)} / {len(all_files)}（目录：{input_dir}）")

    success, failed = 0, 0
    aborted_for_balance = False

    for idx, json_name in enumerate(target_files, start=1):
        json_path = os.path.join(input_dir, json_name)
        stem = os.path.splitext(json_name)[0]

        # 输出文件名：一律保存为 JSON
        out_ext = ".response.json"
        output_file = os.path.join(SEND_RESULT_DIR, stem + out_ext)
        if os.path.exists(output_file) and not args.overwrite:
            print(f"[{idx}/{len(target_files)}] 已存在结果，跳过：{json_name}")
            append_run_log({
                "time": now_iso(),
                "file": json_name,
                "status": "skipped",
                "reason": "exists",
                "output": output_file,
            })
            append_timing({
                "time": now_iso(),
                "file": json_name,
                "provider": PROVIDER_NAME,
                "model": args.model,
                "status": "skipped",
                "duration_seconds": 0,
                "attempts": 0,
                "output": output_file,
            })
            continue

        # 读取 JSON 文本（不解析，避免格式问题）
        with open(json_path, "r", encoding="utf-8") as jf:
            json_text = jf.read()

        # 读取统一评估 prompt（不再按同名文件查找）
        prompt_path = find_prompt_for_json(json_path)
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(
                f"未找到统一评估 prompt：{prompt_path}，请在 prompt/ 下提供 prompt.txt"
            )
        with open(prompt_path, "r", encoding="utf-8") as pf:
            prompt_text = pf.read()

        # 构造消息
        messages = build_messages(prompt_text, json_text)

        print(f"[{idx}/{len(target_files)}] 发送：{json_name}，使用统一 prompt：{os.path.relpath(prompt_path, BASE_DIR)}")
        start_ts = time.time()
        attempts = 0

        max_retries = 3
        for attempt in range(max_retries):
            attempts += 1
            try:
                use_response_format = bool(args.force_json_output)
                try:
                    if use_response_format:
                        resp = client.chat.completions.create(
                            model=args.model,
                            messages=messages,
                            temperature=0,
                            response_format={"type": "json_object"},
                        )
                    else:
                        resp = client.chat.completions.create(
                            model=args.model,
                            messages=messages,
                            temperature=0,
                        )
                except Exception as e_first:
                    msg_first = str(e_first)
                    if use_response_format and ("response_format" in msg_first.lower() or "unsupported" in msg_first.lower()):
                        # 自动降级
                        resp = client.chat.completions.create(
                            model=args.model,
                            messages=messages,
                            temperature=0,
                        )
                    else:
                        raise

                content = resp.choices[0].message.content

                # 保存响应（始终为 JSON）：优先解析；失败则包裹为 {"raw_text": ...}
                try:
                    data = parse_strict_json(content)
                except Exception:
                    data = {"raw_text": content}
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                output_record = output_file

                append_run_log({
                    "time": now_iso(),
                    "file": json_name,
                    "prompt": os.path.relpath(prompt_path, BASE_DIR),
                    "status": "success",
                    "output": output_record,
                    "model": args.model,
                    "usage": _usage_to_dict(getattr(resp, "usage", None)),
                })
                append_timing({
                    "time": now_iso(),
                    "file": json_name,
                    "provider": PROVIDER_NAME,
                    "model": args.model,
                    "status": "success",
                    "duration_seconds": round(time.time() - start_ts, 3),
                    "attempts": attempts,
                    "output": output_record,
                    "usage": _usage_to_dict(getattr(resp, "usage", None)),
                })

                print(f"完成：{json_name} -> {output_record}")
                success += 1
                break
            except Exception as e:
                msg = str(e)
                if ("402" in msg) or ("Insufficient Balance" in msg) or ("insufficient balance" in msg.lower()):
                    print(f"余额不足，终止后续任务：{msg}")
                    append_run_log({
                        "time": now_iso(),
                        "file": json_name,
                        "status": "aborted_balance",
                        "error": msg,
                    })
                    append_timing({
                        "time": now_iso(),
                        "file": json_name,
                        "provider": PROVIDER_NAME,
                        "model": args.model,
                        "status": "aborted_balance",
                        "duration_seconds": round(time.time() - start_ts, 3),
                        "attempts": attempts,
                        "error": msg,
                    })
                    aborted_for_balance = True
                    break

                is_last = (attempt == max_retries - 1)
                print(f"第 {attempt+1}/{max_retries} 次尝试失败：{msg}{'（已放弃）' if is_last else '，重试中…'}")
                if is_last:
                    fail_flag = os.path.join(SEND_RESULT_DIR, stem + ".failed.txt")
                    with open(fail_flag, "w", encoding="utf-8") as ff:
                        ff.write(f"失败时间: {now_iso()}\n异常: {msg}\n")
                    append_run_log({
                        "time": now_iso(),
                        "file": json_name,
                        "prompt": os.path.relpath(prompt_path, BASE_DIR),
                        "status": "failed",
                        "error": msg,
                        "fail_flag": fail_flag,
                    })
                    append_timing({
                        "time": now_iso(),
                        "file": json_name,
                        "provider": PROVIDER_NAME,
                        "model": args.model,
                        "status": "failed",
                        "duration_seconds": round(time.time() - start_ts, 3),
                        "attempts": attempts,
                        "error": msg,
                        "fail_flag": fail_flag,
                    })
                    failed += 1
                else:
                    time.sleep(2 ** attempt)  # 指数退避

        if aborted_for_balance:
            break

        time.sleep(1)  # 轻限速

    print(
        f"批量发送完成。成功: {success}，失败: {failed}，"
        f"{'因余额不足提前终止' if aborted_for_balance else '全部处理完成'}。"
    )


if __name__ == "__main__":
    main()
