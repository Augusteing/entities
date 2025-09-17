import json
import csv
from pathlib import Path

# 配置路径
ROOT = Path(r"e:\知识图谱构建\9.15之前的实验\EXP-1")
RESULTS_DIR = ROOT / "评估" / "指标二：模型评估" / "结果分三个模型保存"
PAPERS_DIR = ROOT / "评估" / "需要评估的论文"
OUT_CSV = ROOT / "数据结果" / "accuracy_by_model_entities_relations.csv"

# 目标模型子目录（按文件夹名）
MODELS = ["deepseek", "gemini", "kimi"]

def load_target_paper_stems():
    stems = []
    for md in sorted(PAPERS_DIR.glob("*.md")):
        stems.append(md.stem)
    return set(stems)

def count_correct_wrong(items):
    correct = sum(1 for x in items if str(x.get("evaluation", "")).strip() == "正确")
    wrong = sum(1 for x in items if str(x.get("evaluation", "")).strip() == "错误")
    total = len(items)
    # 未标注或其他标签计入 total 但不计入 correct/wrong
    acc = (correct / total) if total else 0.0
    return correct, wrong, total, acc

def read_json_safe(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def main():
    target_stems = load_target_paper_stems()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    rows = []

    for model in MODELS:
        model_dir = RESULTS_DIR / model
        if not model_dir.exists():
            continue

        ent_correct = ent_wrong = ent_total = 0
        rel_correct = rel_wrong = rel_total = 0

        # 按目标50篇匹配文件名
        json_files = sorted(model_dir.glob("*.json"))
        # 建立 stem -> path 映射
        stem_map = {p.stem: p for p in json_files}
        for stem in target_stems:
            jp = stem_map.get(stem)
            if not jp:
                # 缺失文件，跳过
                continue
            data = read_json_safe(jp)
            if not isinstance(data, dict):
                continue
            entities = data.get("entities", []) or []
            relations = data.get("relations", []) or []

            c, w, t, _ = count_correct_wrong(entities)
            ent_correct += c; ent_wrong += w; ent_total += t

            c, w, t, _ = count_correct_wrong(relations)
            rel_correct += c; rel_wrong += w; rel_total += t

        ent_acc = (ent_correct / ent_total) if ent_total else 0.0
        rel_acc = (rel_correct / rel_total) if rel_total else 0.0

        rows.append({
            "model": model,
            "entities_correct": ent_correct,
            "entities_wrong": ent_wrong,
            "entities_total": ent_total,
            "entities_accuracy": f"{ent_acc:.4f}",
            "relations_correct": rel_correct,
            "relations_wrong": rel_wrong,
            "relations_total": rel_total,
            "relations_accuracy": f"{rel_acc:.4f}",
        })

    # 写出CSV
    fieldnames = [
        "model",
        "entities_correct", "entities_wrong", "entities_total", "entities_accuracy",
        "relations_correct", "relations_wrong", "relations_total", "relations_accuracy",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # 控制台摘要
    for r in rows:
        print(
            f"{r['model']}: entities {r['entities_correct']}/{r['entities_total']} acc={r['entities_accuracy']}, "
            f"relations {r['relations_correct']}/{r['relations_total']} acc={r['relations_accuracy']}"
        )

if __name__ == "__main__":
    main()
