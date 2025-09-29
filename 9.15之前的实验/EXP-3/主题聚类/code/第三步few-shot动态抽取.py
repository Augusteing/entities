import os
import json  # <-- 1. 引入 json 库
import joblib
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity

# ─── 配置 ─────────────────────────────────────────────────────
DATA_SOURCE_DIR      = "无标注原文"
CLUSTERS_PATH        = "数据结果/embedding_clusters_with_paragraph_annots.json"
UMAP_MODEL_PATH      = "数据结果/umap_model.joblib"
MODEL_NAME           = "BAAI/bge-large-zh-v1.5"
OUTPUT_DIR           = "数据结果/s_modules"
TOP_K                = 3      # 每篇文档的示例数

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ─── 加载示例库与 UMAP ────────────────────────────────────
with open(CLUSTERS_PATH, "r", encoding="utf-8") as f:
    library = json.load(f)
umap_model = joblib.load(UMAP_MODEL_PATH)

# ─── 加载文本嵌入模型 ──────────────────────────────────────────
tokenizer   = AutoTokenizer.from_pretrained(MODEL_NAME)
embed_model = AutoModel.from_pretrained(MODEL_NAME).to(device).eval()

def embed(text: str) -> np.ndarray:
    inputs = tokenizer("[CLS] " + text, return_tensors="pt",
                       truncation=True, max_length=512).to(device)
    with torch.no_grad():
        out = embed_model(**inputs)
    return out.last_hidden_state[:, 0].squeeze().cpu().numpy()

def to_5d(vec: np.ndarray) -> np.ndarray:
    return umap_model.transform([vec])[0]

# ─── 注释识别与规范化工具 ─────────────────────────────────────
ALT_REL_KEYS = [
    ("head", "tail"),
    ("from", "to"),
    ("subject", "object"),
    ("source", "target"),
]

def is_relation_ann(ann: dict) -> bool:
    if not isinstance(ann, dict):
        return False
    for hk, tk in ALT_REL_KEYS:
        if hk in ann and tk in ann:
            return True
    return False

def extract_relation_norm(ann: dict) -> dict:
    """将多种关系键规范为 {type, head, tail}，缺省值为空串。"""
    rtype = ann.get("type", "") if isinstance(ann, dict) else ""
    head = tail = ""
    if isinstance(ann, dict):
        for hk, tk in ALT_REL_KEYS:
            if hk in ann and tk in ann:
                head = ann.get(hk, "")
                tail = ann.get(tk, "")
                break
    return {"type": rtype, "head": head, "tail": tail}

def is_entity_ann(ann: dict) -> bool:
    return isinstance(ann, dict) and ("text" in ann)

def split_annotations(annotations) -> tuple[list, list]:
    entities, relations = [], []
    if annotations:
        for ann in annotations:
            if is_relation_ann(ann):
                relations.append(extract_relation_norm(ann))
            elif is_entity_ann(ann):
                entities.append({
                    "type": ann.get("type", ""),
                    "text": ann.get("text", ""),
                })
    return entities, relations

# ─── 准备库向量与簇标签 ─────────────────────────────────────
lib_vecs_5d  = np.array([e["embedding_5d"] for e in library])
lib_clusters = np.array([e["cluster"]     for e in library])

# ─── 生成 S 模块 ─────────────────────────────────────────────
os.makedirs(OUTPUT_DIR, exist_ok=True)

for fn in sorted(os.listdir(DATA_SOURCE_DIR)):
    if not fn.endswith(".md"):
        continue

    # 1) 读取全文用于向量化（示例选取）
    path = os.path.join(DATA_SOURCE_DIR, fn)
    with open(path, "r", encoding="utf-8") as f:
        full_text = f.read().strip()

    # 2) 嵌入 + 降维 + 相似度
    vec    = embed(full_text)
    vec5d  = to_5d(vec)
    sims   = cosine_similarity([vec5d], lib_vecs_5d)[0]
    primary_cluster = lib_clusters[sims.argmax()]
    idxs_in_cluster = np.where(lib_clusters == primary_cluster)[0]
    sims_in_cluster = sims[idxs_in_cluster]
    
    # 按相似度排序，然后筛选有标注的段落
    sorted_idxs = idxs_in_cluster[np.argsort(sims_in_cluster)[::-1]]
    selected: list[dict] = []
    used_idx: set[int] = set()
    
    # 先确保至少选择一个含关系的示例（优先同簇内）
    for idx in sorted_idxs:
        candidate = library[idx]
        entities, relations = split_annotations(candidate.get("annotations"))
        if relations:  # 含关系
            selected.append(candidate)
            used_idx.add(idx)
            break

    # 填充剩余名额（同簇内，实体或关系皆可）
    for idx in sorted_idxs:
        if len(selected) >= TOP_K:
            break
        if idx in used_idx:
            continue
        candidate = library[idx]
        entities, relations = split_annotations(candidate.get("annotations"))
        if entities or relations:
            selected.append(candidate)
            used_idx.add(idx)
    
    # 如果找不到足够的有标注示例，从其他聚类中补充
    if len(selected) < TOP_K:
        # 在全库按相似度补充，先补充含关系的，仍不足再补实体
        all_sorted_idxs = np.argsort(sims)[::-1]
        # 先找含关系的
        for idx in all_sorted_idxs:
            if len(selected) >= TOP_K:
                break
            if idx in used_idx:
                continue
            candidate = library[idx]
            entities, relations = split_annotations(candidate.get("annotations"))
            if relations:
                selected.append(candidate)
                used_idx.add(idx)
        # 再补实体或关系任一
        for idx in all_sorted_idxs:
            if len(selected) >= TOP_K:
                break
            if idx in used_idx:
                continue
            candidate = library[idx]
            entities, relations = split_annotations(candidate.get("annotations"))
            if entities or relations:
                selected.append(candidate)
                used_idx.add(idx)

    # 3) 拼接 S 模块内容  <-- 2. 此处为核心修改区域
    if not selected:
        print(f"⚠️  警告：未找到有效标注示例，跳过文档：{fn}")
        continue
    # 若依旧没有任何包含关系的示例，给出提醒
    if not any(split_annotations(ex.get("annotations"))[1] for ex in selected):
        print(f"⚠️  提示：文档 {fn} 的示例不包含关系，将仅使用实体示例（库中未找到带关系的标注）。")
        
    lines = [
        "【S：Few-Shot动态采样】",
        "以下示例均为与待抽取文本语义最相关的段落，包含该段落及其标注：",
        ""
    ]
    for i, ex in enumerate(selected, 1):
        lines.append(f"示例{i} 段落：\n{ex['text']}")
        lines.append("标注：")

        entities, relations = split_annotations(ex.get("annotations"))
        
        # 构建完整的JSON对象
        annotation_json = {}
        
        # 只有当实体列表不为空时才添加entities字段
        if entities:
            annotation_json["entities"] = entities
        
        # 只有当关系列表不为空时才添加relations字段
        if relations:
            annotation_json["relations"] = relations
        
        # 将JSON对象转换为格式化的字符串，并添加到内容中
        json_string = json.dumps(annotation_json, ensure_ascii=False, indent=2)
        lines.append(f"```json\n{json_string}\n```")
        lines.append("")

   

    # 4) 保存到文件
    out_fp = os.path.join(OUTPUT_DIR, f"S_module_{fn.replace('.md', '.txt')}")
    with open(out_fp, "w", encoding="utf-8") as fo:
        fo.write("\n".join(lines))

    print(f"✔ 已生成 S 模块：{out_fp}")