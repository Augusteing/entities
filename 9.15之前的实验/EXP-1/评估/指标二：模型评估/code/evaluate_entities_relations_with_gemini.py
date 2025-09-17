# -*- coding: utf-8 -*-
"""
评估脚本：对提交的实体与关系 JSON 进行合理性评估（Gemini）

- 读取目录： 评估/指标二：模型评估/提交文件/{deepseek, gemini, kimi}
- 使用提示词：评估/指标二：模型评估/prompt/gemini_entity_relation_evaluation_prompt.md.txt
- 提交给 Gemini（OpenAI 兼容接口 hiapi.online）评估，每条对象追加 evaluation 字段
- 结果输出：评估/指标二：模型评估/结果分三个模型保存/{deepseek, gemini, kimi}/同名.json（不覆盖原提交文件）
- 日志：评估/指标二：模型评估/log 下保存 ndjson 日志与耗时

环境变量（与 exact_gemini.py 一致的取值优先级）：
- HIAPI_API_KEY / GEMINI_API_KEY / OPENAI_API_KEY / API_KEY
- HIAPI_BASE_URL（默认 https://hiapi.online/v1）
- EVAL_SLEEP_SECS（默认 0.5）
- EVAL_MAX_RETRIES（默认 3）
- EVAL_SKIP_PREFLIGHT=1 跳过 /models 预检
 - EVAL_OVERWRITE（默认 0：不覆盖，便于断点续跑）
 - EVAL_RESUME（默认 1：根据进度文件自动续跑）
 - EVAL_RESUME_FROM（可选：从指定文件名或id开始）

运行：
    python .\\评估\\指标二：模型评估\\code\\evaluate_entities_relations_with_gemini.py
"""
import os
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, Any, List

# OpenAI 兼容客户端（hiapi.online）
from openai import OpenAI  # type: ignore

# ------------------------------
# 路径配置
# ------------------------------
THIS_FILE = os.path.abspath(__file__)
CODE_DIR = os.path.dirname(THIS_FILE)
BASE_DIR = os.path.dirname(CODE_DIR)  # 指向 "评估/指标二：模型评估"

PROMPT_FILE = os.path.join(BASE_DIR, "prompt", "gemini_entity_relation_evaluation_prompt.md.txt")
SUBMIT_ROOT = os.path.join(BASE_DIR, "提交文件")
RESULT_ROOT = os.path.join(BASE_DIR, "结果分三个模型保存")
LOG_DIR = os.path.join(BASE_DIR, "log")
MAIN_LOG = os.path.join(LOG_DIR, "eval_log.ndjson")
TIMINGS_LOG = os.path.join(LOG_DIR, "eval_timings.ndjson")
SUMMARY_FILE = os.path.join(BASE_DIR, "eval_build_summary.json")
PROGRESS_FILE = os.path.join(BASE_DIR, "eval_progress.json")
SHARED_IDS_FILE = os.path.join(BASE_DIR, "提交文件", "shared_doc_ids.json")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(RESULT_ROOT, exist_ok=True)
for _sub in ("deepseek", "gemini", "kimi"):
    os.makedirs(os.path.join(RESULT_ROOT, _sub), exist_ok=True)

# ------------------------------
# 参数配置（可环境变量覆盖）
# ------------------------------
MODEL_NAME = os.getenv("EVAL_MODEL", "gemini-2.5-pro")
PROVIDER_NAME = os.getenv("EVAL_PROVIDER", "gemini")

try:
    SLEEP_SECS = float(os.getenv("EVAL_SLEEP_SECS", "0.5"))
except Exception:
    SLEEP_SECS = 0.5
try:
    MAX_RETRIES = int(os.getenv("EVAL_MAX_RETRIES", "3"))
except Exception:
    MAX_RETRIES = 3
SKIP_PREFLIGHT = os.getenv("EVAL_SKIP_PREFLIGHT", "0") in {"1", "true", "TRUE"}
try:
    EVAL_PARALLELISM = int(os.getenv("EVAL_PARALLELISM", "3"))
except Exception:
    EVAL_PARALLELISM = 3
# 覆盖输出：为便于断点续跑，默认不覆盖（设置为 1 才会覆盖）
OVERWRITE = os.getenv("EVAL_OVERWRITE", "0") in {"1", "true", "TRUE"}

# 断点续跑控制
RESUME = os.getenv("EVAL_RESUME", "1") in {"1", "true", "TRUE"}
# 从指定文件名开始（可为不带后缀的 id 或带 .json 的文件名）
RESUME_FROM = os.getenv("EVAL_RESUME_FROM", "").strip() or None

# ------------------------------
# 工具函数
# ------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def strip_code_fences(s: str) -> str:
    """去除 ```json ... ``` 的围栏，尽可能容错。"""
    if not isinstance(s, str):
        return s
    s = s.strip()
    if s.startswith("```") and s.endswith("```"):
        s = s[3:-3].strip()
        if "\n" in s:
            first, rest = s.split("\n", 1)
            if first.strip().lower() in {"json", "js", "javascript"}:
                s = rest
    return s


def parse_strict_json(content: str) -> Dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        cleaned = strip_code_fences(content)
        return json.loads(cleaned)


_log_lock = threading.Lock()

def append_log(item: Dict[str, Any]):
    with _log_lock:
        with open(MAIN_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def append_timing(item: Dict[str, Any]):
    with _log_lock:
        with open(TIMINGS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

def write_progress(idx: int, total: int, fname: str):
    data = {
        "time": now_iso(),
        "current_index": idx,
        "total": total,
        "filename": fname,
    }
    with _log_lock:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def read_progress() -> Dict[str, Any]:
    """读取进度文件，若不存在则返回空字典。"""
    try:
        if os.path.isfile(PROGRESS_FILE):
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


# 不再使用失败标记文件（.failed.txt）。是否已完成仅以结果 JSON 是否存在来判断。


def load_prompt() -> str:
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


def is_article_completed(fname: str) -> bool:
    """判断一篇文章是否已完成：三个模型的结果 JSON 是否都存在。
    注意：若输入端某模型本就没有该文件，则该模型不会被提交，本函数只检查存在输入文件的模型对应输出是否存在。
    """
    models = ["deepseek", "gemini", "kimi"]
    completed_any = False
    for m in models:
        in_path = os.path.join(SUBMIT_ROOT, m, fname)
        if os.path.isfile(in_path):
            # 该模型有输入，则需要有输出才算该模型完成
            out_path = os.path.join(RESULT_ROOT, m, fname)
            if not os.path.isfile(out_path):
                return False
            completed_any = True
    # 如果没有任何模型有这个输入（极端情况），视为未完成
    return completed_any


def compute_completed_prefix(file_list: List[str]) -> int:
    """计算 file_list 的已完成前缀长度：从第一项起连续满足 is_article_completed 的数量。
    用于断点续跑的安全起点（例如已完成25篇则从索引25处的第26篇开始）。
    """
    count = 0
    for fname in file_list:
        if is_article_completed(fname):
            count += 1
        else:
            break
    return count


# ------------------------------
# 初始化客户端（与 exact_gemini.py 兼容）
# ------------------------------

def _mask_key(k: str) -> str:
    if not k or len(k) < 8:
        return "***"
    return f"{k[:6]}...{k[-4:]}"

api_key_source = None
api_key = None
for _var in ("HIAPI_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "API_KEY"):
    _v = os.getenv(_var)
    if _v:
        api_key = _v.strip()
        api_key_source = _var
        break
if not api_key:
    raise ValueError("未检测到 API Key。请设置 HIAPI_API_KEY（或 GEMINI_API_KEY/OPENAI_API_KEY/API_KEY）。")

_base_env = os.getenv("HIAPI_BASE_URL")
if _base_env:
    _base_clean = _base_env.rstrip("/")
    BASE_URL = _base_clean if _base_clean.endswith("/v1") else _base_clean + "/v1"
else:
    BASE_URL = "https://hiapi.online/v1"

if "hiapi.online" in (BASE_URL or "") and not api_key.lower().startswith("sk-"):
    raise ValueError(
        f"当前 base_url={BASE_URL} 指向 hiapi.online，但从 {api_key_source} 读取到的 Key 不是 sk- 开头：{_mask_key(api_key)}。\n"
        "请使用 hiapi 后台颁发的 sk- 开头密钥，设置到 HIAPI_API_KEY 并重试。"
    )

client = OpenAI(api_key=api_key, base_url=BASE_URL)

if not SKIP_PREFLIGHT:
    try:
        models_res = client.models.list()
        print(f"预检通过：已连接 {BASE_URL}（模型数≈{len(getattr(models_res, 'data', []) or [])}）。Key 来源={api_key_source}，Key 掩码={_mask_key(api_key)}")
    except Exception as _e:
        print("预检警告：/models 接口不可用或返回错误，将继续执行。详情：" + str(_e))


# ------------------------------
# 主流程
# ------------------------------

def build_user_content(prompt_md: str, item_json: Dict[str, Any]) -> str:
    # 将抽取结果 JSON 嵌入提示词后面，明确仅输出严格 JSON
    merged = (
        f"{prompt_md}\n\n"
        f"以下为需要评估的抽取结果（严格 JSON）：\n"
        f"{json.dumps(item_json, ensure_ascii=False, indent=2)}\n\n"
        f"请仅输出严格 JSON（UTF-8，无多余文本）。"
    )
    return merged


def eval_one_file(model_name: str, in_path: str, out_path: str, prompt_md: str) -> str:
    with open(in_path, "r", encoding="utf-8") as f:
        item = json.load(f)

    # 构建消息
    user_content = build_user_content(prompt_md, item)

    start_ts = time.time()
    attempts = 0

    for attempt in range(MAX_RETRIES):
        attempts += 1
        try:
            try:
                resp = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": "你是信息抽取评估助手，只输出严格的 JSON，不要添加多余文本。"},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0,
                    response_format={"type": "json_object"},
                )
            except Exception as e_first:
                msg_first = str(e_first)
                if "response_format" in msg_first.lower() or "unsupported" in msg_first.lower():
                    resp = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[
                            {"role": "system", "content": "你是信息抽取评估助手，只输出严格的 JSON，不要添加多余文本。"},
                            {"role": "user", "content": user_content},
                        ],
                        temperature=0,
                    )
                else:
                    raise

            content = resp.choices[0].message.content
            data = parse_strict_json(content)

            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as wf:
                json.dump(data, wf, ensure_ascii=False, indent=2)

            # 日志
            append_log({
                "time": now_iso(),
                "provider": PROVIDER_NAME,
                "model": MODEL_NAME,
                "input_file": in_path,
                "output_file": out_path,
                "status": "success",
                "usage": getattr(resp, "usage", None) and getattr(resp.usage, "model_dump", lambda: resp.usage.__dict__)(),
            })
            append_timing({
                "time": now_iso(),
                "provider": PROVIDER_NAME,
                "model": MODEL_NAME,
                "input_file": in_path,
                "output_file": out_path,
                "status": "success",
                "duration_seconds": round(time.time() - start_ts, 3),
                "attempts": attempts,
            })

            if SLEEP_SECS > 0:
                time.sleep(SLEEP_SECS)
            return "success"
        except Exception as e:
            msg = str(e)
            # 余额不足直接中断该文件并上抛（由上层决定是否整体中止）
            if ("402" in msg) or ("Insufficient Balance" in msg) or ("insufficient balance" in msg.lower()):
                append_log({
                    "time": now_iso(),
                    "provider": PROVIDER_NAME,
                    "model": MODEL_NAME,
                    "input_file": in_path,
                    "status": "aborted_balance",
                    "error": msg,
                })
                append_timing({
                    "time": now_iso(),
                    "provider": PROVIDER_NAME,
                    "model": MODEL_NAME,
                    "input_file": in_path,
                    "status": "aborted_balance",
                    "duration_seconds": round(time.time() - start_ts, 3),
                    "attempts": attempts,
                    "error": msg,
                })
                raise

            is_last = (attempt == MAX_RETRIES - 1)
            if is_last:
                # 失败记录日志，但不写失败标记文件
                append_log({
                    "time": now_iso(),
                    "provider": PROVIDER_NAME,
                    "model": MODEL_NAME,
                    "input_file": in_path,
                    "output_file": out_path,
                    "status": "failed",
                    "error": msg,
                })
                append_timing({
                    "time": now_iso(),
                    "provider": PROVIDER_NAME,
                    "model": MODEL_NAME,
                    "input_file": in_path,
                    "output_file": out_path,
                    "status": "failed",
                    "duration_seconds": round(time.time() - start_ts, 3),
                    "attempts": attempts,
                    "error": msg,
                })
                return "failed"
            else:
                # 指数退避
                time.sleep(2 ** attempt)

    # 理论上不会到这里
    return "failed"


def main():
    prompt_md = load_prompt()

    # 三个模型子目录
    models = ["deepseek", "gemini", "kimi"]

    # 组装要评估的文件名清单（优先使用 shared_doc_ids.json）
    files: List[str] = []
    if os.path.isfile(SHARED_IDS_FILE):
        try:
            with open(SHARED_IDS_FILE, "r", encoding="utf-8") as f:
                ids = json.load(f)
            # ids 是无扩展名，需补 .json
            files = [f"{x}.json" for x in ids if isinstance(x, str)]
        except Exception:
            files = []
    if not files:
        # 回退：取三个目录的交集
        sets = []
        for m in models:
            d = os.path.join(SUBMIT_ROOT, m)
            if os.path.isdir(d):
                names = {fn for fn in os.listdir(d) if fn.endswith('.json')}
                sets.append(names)
        if sets:
            inter = set.intersection(*sets) if len(sets) >= 2 else (sets[0] if sets else set())
            files = sorted(inter)

    # 应用断点重续与起始点选择（基于“已完成前缀”）
    start_index = 0
    if files:
        if OVERWRITE:
            start_index = 0
        elif RESUME_FROM:
            key = RESUME_FROM if RESUME_FROM.endswith('.json') else f"{RESUME_FROM}.json"
            start_index = files.index(key) if key in files else 0
        elif RESUME:
            # 基于结果目录中的“已完成前缀”确定起点
            start_index = compute_completed_prefix(files)
        else:
            start_index = 0
    if start_index > 0 and start_index < len(files):
        print(f"检测到断点续跑：发现已完成前缀 {start_index} 篇，将从第 {start_index+1} 篇开始（文件：{files[start_index]}）。")
    elif start_index >= len(files):
        print(f"检测到所有 {len(files)} 篇均已完成，无需继续。")
        # 仍然继续走后续逻辑以写 summary，但 files 置空
        files = []
    files = files[start_index:]

    total_files = len(files)
    print(f"共 {total_files} 篇文章将按‘每篇并行三个模型’方式评估。覆盖输出={OVERWRITE}")

    # 初始化计数
    per_model_counts = {m: {"inputs": total_files, "success": 0, "failed": 0} for m in models}
    total_tasks = 0
    succ = fail = 0
    aborted = False

    # 预建输出目录
    for m in models:
        os.makedirs(os.path.join(RESULT_ROOT, m), exist_ok=True)

    # 线程池：并行度控制（每篇最多三个并发）
    with ThreadPoolExecutor(max_workers=EVAL_PARALLELISM) as executor:
        for idx, fname in enumerate(files, 1):
            write_progress(idx, total_files, fname)
            print(f"进度 {idx}/{total_files}：正在评估 {fname}")

            futures = {}
            for m in models:
                in_dir = os.path.join(SUBMIT_ROOT, m)
                out_dir = os.path.join(RESULT_ROOT, m)
                in_path = os.path.join(in_dir, fname)
                out_path = os.path.join(out_dir, fname)

                if not os.path.isfile(in_path):
                    continue
                # 跳过逻辑：不覆盖且已存在输出，视为成功跳过。
                if (not OVERWRITE) and os.path.isfile(out_path):
                    per_model_counts[m]["success"] += 1
                    continue
                total_tasks += 1
                futures[executor.submit(eval_one_file, m, in_path, out_path, prompt_md)] = (m, fname)

            # 收集本篇的三个（或更少）任务结果
            for fut in as_completed(futures):
                m, f = futures[fut]
                try:
                    status = fut.result()
                    if status == "success":
                        succ += 1
                        per_model_counts[m]["success"] += 1
                        print(f"  - {m}: success")
                    else:
                        fail += 1
                        per_model_counts[m]["failed"] += 1
                        print(f"  - {m}: failed")
                except Exception as e:
                    # 余额不足等致命错误：终止整体评估
                    aborted = True
                    per_model_counts[m]["failed"] += 1
                    fail += 1
                    print(f"  - {m}: aborted ({e})")
            if aborted:
                print("检测到致命错误（可能为余额不足或 API 拒绝），提前结束。本次进度已写入：" + PROGRESS_FILE)
                break

    # 写 summary
    summary = {
        "time": now_iso(),
        "provider": PROVIDER_NAME,
        "model": MODEL_NAME,
        "submit_root": SUBMIT_ROOT,
        "result_root": RESULT_ROOT,
        "total_files": total_files,
        "total_tasks": total_tasks,
        "success": succ,
        "failed": fail,
        "per_model": per_model_counts,
        "aborted": aborted,
    }
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n评估完成：files={total_files}, tasks={total_tasks}, success={succ}, failed={fail}, aborted={aborted}")
    print(f"详细 summary: {SUMMARY_FILE}")
    print(f"进度文件: {PROGRESS_FILE}  日志目录: {LOG_DIR}")


if __name__ == "__main__":
    main()
