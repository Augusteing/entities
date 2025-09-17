# -*- coding: utf-8 -*-
"""
评估脚本：对提交的实体与关系 JSON 进行合理性评估（Gemini）- 50篇评估论文版

修改要点：
- 只评估"需要评估的论文"文件夹中的50篇论文
- 跳过已经评估过的论文（保持现有结果）
- 保持断点续跑功能

- 读取目录： 评估/指标二：模型评估/提交文件/{deepseek, gemini, kimi}
- 使用提示词：评估/指标二：模型评估/prompt/gemini_entity_relation_evaluation_prompt.md.txt
- 提交给 Gemini（OpenAI 兼容接口 hiapi.online）评估，每条对象追加 evaluation 字段
- 结果输出：评估/指标二：模型评估/结果/{deepseek, gemini, kimi}/同名.json（不覆盖原提交文件）
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
    python evaluate_50_papers_with_gemini.py
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

# 新增：50篇评估论文的目录路径
EVALUATION_PAPERS_DIR = os.path.join(os.path.dirname(BASE_DIR), "需要评估的论文")

PROMPT_FILE = os.path.join(BASE_DIR, "prompt", "gemini_entity_relation_evaluation_prompt.md.txt")
SUBMIT_ROOT = os.path.join(BASE_DIR, "提交文件")
RESULT_ROOT = os.path.join(BASE_DIR, "结果")  # 修改为直接使用"结果"文件夹
LOG_DIR = os.path.join(BASE_DIR, "log")
MAIN_LOG = os.path.join(LOG_DIR, "eval_50_papers_log.ndjson")
TIMINGS_LOG = os.path.join(LOG_DIR, "eval_50_papers_timings.ndjson")
SUMMARY_FILE = os.path.join(BASE_DIR, "eval_50_papers_summary.json")
PROGRESS_FILE = os.path.join(BASE_DIR, "eval_50_papers_progress.json")

# 确保日志目录存在
os.makedirs(LOG_DIR, exist_ok=True)

# 环境变量读取
PROVIDER_NAME = "hiapi.online"  # 默认提供商名称
MODEL_NAME = "gemini-2.5-pro"
SLEEP_SECS = float(os.getenv("EVAL_SLEEP_SECS") or "0.5")
MAX_RETRIES = int(os.getenv("EVAL_MAX_RETRIES") or "3")
SKIP_PREFLIGHT = int(os.getenv("EVAL_SKIP_PREFLIGHT") or "0")
OVERWRITE = int(os.getenv("EVAL_OVERWRITE") or "0")
RESUME = int(os.getenv("EVAL_RESUME") or "1")
RESUME_FROM = os.getenv("EVAL_RESUME_FROM") or ""
EVAL_PARALLELISM = int(os.getenv("EVAL_PARALLELISM") or "3")

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def _mask_key(k: str) -> str:
    if len(k) <= 8:
        return "*" * len(k)
    return k[:4] + "*" * (len(k) - 8) + k[-4:]

def get_evaluation_papers() -> List[str]:
    """获取需要评估的50篇论文文件名列表（不含扩展名）"""
    if not os.path.exists(EVALUATION_PAPERS_DIR):
        print(f"错误：找不到评估论文目录: {EVALUATION_PAPERS_DIR}")
        return []
    
    papers = []
    for file in os.listdir(EVALUATION_PAPERS_DIR):
        if file.endswith('.md'):
            # 去掉.md扩展名
            paper_name = file[:-3]
            papers.append(paper_name)
    
    print(f"找到 {len(papers)} 篇需要评估的论文")
    return sorted(papers)

def load_prompt() -> str:
    if not os.path.isfile(PROMPT_FILE):
        raise FileNotFoundError(f"提示词文件不存在：{PROMPT_FILE}")
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()

def compute_completed_prefix(files: List[str]) -> int:
    """计算已完成的文件前缀长度"""
    models = ["deepseek", "gemini", "kimi"]
    
    for i, fname in enumerate(files):
        json_fname = fname if fname.endswith('.json') else f"{fname}.json"
        all_completed = True
        
        for m in models:
            out_dir = os.path.join(RESULT_ROOT, m)
            out_path = os.path.join(out_dir, json_fname)
            if not os.path.isfile(out_path):
                all_completed = False
                break
        
        if not all_completed:
            return i
    
    return len(files)  # 全部完成

def strip_code_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```") and s.endswith("```"):
        lines = s.split("\n")
        if len(lines) >= 2:
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

# API客户端设置
api_key = ""
api_key_source = ""
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

    user_content = build_user_content(prompt_md, item)
    start_ts = time.time()
    attempts = 0

    for attempt in range(MAX_RETRIES):
        attempts += 1
        try:
            time.sleep(SLEEP_SECS)
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": user_content}],
                temperature=0.1,
            )
            content = response.choices[0].message.content or ""
            
            # 调试：记录API响应内容
            print(f"    API响应内容长度: {len(content)}")
            if len(content) == 0:
                print(f"    警告：API返回空响应")
            elif len(content) < 100:
                print(f"    API响应内容: {repr(content)}")
            else:
                print(f"    API响应前100字符: {repr(content[:100])}")
            
            # 解析JSON并添加evaluation字段
            eval_result = parse_strict_json(content)
            item["evaluation"] = eval_result
            
            # 保存结果
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(item, f, ensure_ascii=False, indent=2)
            
            # 记录成功日志
            append_log({
                "time": now_iso(),
                "provider": PROVIDER_NAME,
                "model": MODEL_NAME,
                "model_name": model_name,
                "input_file": in_path,
                "output_file": out_path,
                "status": "success",
                "attempts": attempts,
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
            return "success"
            
        except Exception as e:
            msg = str(e)
            error_type = type(e).__name__
            print(f"    尝试 {attempt+1}/{MAX_RETRIES} 失败 ({error_type}): {msg}")
            
            # 如果是JSON解析错误，记录更多调试信息
            if "Expecting value" in msg or "JSON" in msg:
                try:
                    # 尝试获取响应内容用于调试
                    if 'response' in locals():
                        debug_content = response.choices[0].message.content or ""
                        print(f"    调试：响应内容长度={len(debug_content)}")
                        if len(debug_content) == 0:
                            print(f"    调试：API返回空响应")
                        elif len(debug_content) < 200:
                            print(f"    调试：完整响应内容: {repr(debug_content)}")
                        else:
                            print(f"    调试：响应前200字符: {repr(debug_content[:200])}")
                except:
                    print(f"    调试：无法获取响应内容用于调试")
            
            # 检查是否为致命错误
            if "insufficient_quota" in msg.lower() or "rate_limit" in msg.lower():
                append_log({
                    "time": now_iso(),
                    "provider": PROVIDER_NAME,
                    "model": MODEL_NAME,
                    "model_name": model_name,
                    "input_file": in_path,
                    "output_file": out_path,
                    "status": "fatal_error",
                    "attempts": attempts,
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
                raise e  # 向上抛出致命错误
            
            if attempt == MAX_RETRIES - 1:
                # 最后一次尝试失败
                append_log({
                    "time": now_iso(),
                    "provider": PROVIDER_NAME,
                    "model": MODEL_NAME,
                    "model_name": model_name,
                    "input_file": in_path,
                    "output_file": out_path,
                    "status": "failed",
                    "attempts": attempts,
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

    return "failed"

def main():
    prompt_md = load_prompt()

    # 三个模型子目录
    models = ["deepseek", "gemini", "kimi"]

    # 获取需要评估的50篇论文清单
    evaluation_papers = get_evaluation_papers()
    if not evaluation_papers:
        print("错误：未找到需要评估的论文")
        return

    # 转换为.json文件名
    files = [f"{paper}.json" for paper in evaluation_papers]
    
    # 过滤掉不存在的文件（确保所有模型都有对应的提交文件）
    valid_files = []
    for fname in files:
        all_exist = True
        for m in models:
            in_path = os.path.join(SUBMIT_ROOT, m, fname)
            if not os.path.isfile(in_path):
                print(f"警告：{m} 模型缺少文件 {fname}，跳过该论文")
                all_exist = False
                break
        if all_exist:
            valid_files.append(fname)
    
    files = valid_files
    print(f"有效的论文文件数量: {len(files)}")

    # 应用断点重续与起始点选择
    start_index = 0
    if files:
        if OVERWRITE:
            start_index = 0
        elif RESUME_FROM:
            key = RESUME_FROM if RESUME_FROM.endswith('.json') else f"{RESUME_FROM}.json"
            start_index = files.index(key) if key in files else 0
        elif RESUME:
            # 基于结果目录中的"已完成前缀"确定起点
            start_index = compute_completed_prefix(files)
        else:
            start_index = 0
    
    if start_index > 0 and start_index < len(files):
        print(f"检测到断点续跑：发现已完成前缀 {start_index} 篇，将从第 {start_index+1} 篇开始（文件：{files[start_index]}）。")
    elif start_index >= len(files):
        print(f"检测到所有 {len(files)} 篇均已完成，无需继续。")
        files = []
    
    files = files[start_index:]
    total_files = len(files)
    print(f"共 {total_files} 篇文章将按'每篇并行三个模型'方式评估。覆盖输出={OVERWRITE}")

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
            print(f"进度 {start_index + idx}/{start_index + total_files}：正在评估 {fname}")

            futures = {}
            for m in models:
                in_dir = os.path.join(SUBMIT_ROOT, m)
                out_dir = os.path.join(RESULT_ROOT, m)
                in_path = os.path.join(in_dir, fname)
                out_path = os.path.join(out_dir, fname)

                if not os.path.isfile(in_path):
                    continue
                
                # 跳过逻辑：不覆盖且已存在输出，视为成功跳过
                if (not OVERWRITE) and os.path.isfile(out_path):
                    per_model_counts[m]["success"] += 1
                    print(f"  - {m}: 已存在，跳过")
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
        "evaluation_papers_count": len(evaluation_papers),
        "valid_files_count": len(valid_files),
        "processed_files": total_files,
        "total_tasks": total_tasks,
        "success": succ,
        "failed": fail,
        "per_model": per_model_counts,
        "aborted": aborted,
    }
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n50篇评估论文处理完成：")
    print(f"  - 评估论文总数: {len(evaluation_papers)}")
    print(f"  - 有效文件数: {len(valid_files)}")
    print(f"  - 处理文件数: {total_files}")
    print(f"  - 总任务数: {total_tasks}")
    print(f"  - 成功: {succ}")
    print(f"  - 失败: {fail}")
    print(f"  - 中止: {aborted}")
    print(f"详细 summary: {SUMMARY_FILE}")
    print(f"进度文件: {PROGRESS_FILE}")
    print(f"日志目录: {LOG_DIR}")

if __name__ == "__main__":
    main()