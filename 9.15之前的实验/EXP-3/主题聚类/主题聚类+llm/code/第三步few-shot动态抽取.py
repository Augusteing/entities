import os
import json  # <-- 1. 引入 json 库
import joblib
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity

# ─── 配置 ─────────────────────────────────────────────────────
DATA_SOURCE_DIR      = "文献来源"
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
    topk_idxs       = idxs_in_cluster[np.argsort(sims_in_cluster)[-TOP_K:][::-1]]
    selected        = [library[i] for i in topk_idxs]

    # 3) 拼接 S 模块内容  <-- 2. 此处为核心修改区域
    lines = [
        "【S：Few-Shot动态采样】",
        "以下示例均为与待抽取文本语义最相关的段落，包含该段落及其标注：",
        ""
    ]
    for i, ex in enumerate(selected, 1):
        lines.append(f"示例{i} 段落：\n{ex['text']}")
        lines.append("标注：")

        entities = []
        relations = []

        # 检查并分类标注信息
        if ex.get("annotations"):
            for ann in ex["annotations"]:
                if "head" in ann and "tail" in ann:
                    relations.append({
                        "type": ann.get("type", ""),
                        "head": ann.get("head", ""),
                        "tail": ann.get("tail", "")
                    })
                elif "text" in ann:
                    entities.append({
                        "type": ann.get("type", ""),
                        "text": ann.get("text", "")
                    })
        
        # 构建完整的JSON对象
        annotation_json = {
            "entities": entities,
            "relations": relations
        }
        
        # 将JSON对象转换为格式化的字符串，并添加到内容中
        json_string = json.dumps(annotation_json, ensure_ascii=False, indent=2)
        lines.append(f"```json\n{json_string}\n```")
        lines.append("")

   

    # 4) 保存到文件
    out_fp = os.path.join(OUTPUT_DIR, f"S_module_{fn.replace('.md', '.txt')}")
    with open(out_fp, "w", encoding="utf-8") as fo:
        fo.write("\n".join(lines))

    print(f"✔ 已生成 S 模块：{out_fp}")