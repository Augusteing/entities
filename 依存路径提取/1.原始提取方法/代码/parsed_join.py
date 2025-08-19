import json
#--------------------id 与 head 重映射（子句分词结果拼接）-----------------
def parsed_full(analyzed_sentences):
    """
    输入：
        - analyzed_sentences: 列表，每个元素是一个包含 parsed 的子句
    输出：
        - 拼接后的分词结果以及整个文本
    """
    # 步骤一：拼接 parsed，修正 id 和 head
    parsed_all = []
    current_id = 1
    id_map_global = {}
    id_offset = 0

    for sent in analyzed_sentences:
        id_map = {}
        for tok in sent["parsed"]:
            new_tok = tok.copy()
            old_id = tok["id"]
            id_map[old_id] = current_id
            id_map_global[old_id + id_offset] = current_id
            new_tok["id"] = current_id
            new_tok["head"] = tok["head"] + id_offset  # 先临时存储旧的 head 值加上偏移量
            parsed_all.append(new_tok)
            current_id += 1

        # 在每个子句之间添加句号
        if current_id > 1:  # 确保不是第一个子句
            new_tok = {
                "form": "。",
                "id": current_id,
                "head": current_id-1  # 句号作为根节点
            }
            parsed_all.append(new_tok)
            current_id += 1

        id_offset = current_id  # 更新偏移量

    # 修正 head 字段
    for tok in parsed_all:
        if tok["head"] == 0:
            tok["head"] = 0
        else:
            tok["head"] = id_map_global.get(tok["head"], 0)

    # 步骤二：拼接所有 form，得到 char_text
    forms = [tok["form"] for tok in parsed_all]
    char_text = ''.join(forms)

    return parsed_all, char_text

with open(r"dependency_results\大型飞机发动机故障智能诊断方法研究与仿真_dependency.json", encoding = "utf-8") as file:
    text = json.load(file)
    analyzed_sentences = text["analyzed_sentences"]

parsed_all, char_text = parsed_full(analyzed_sentences)
print(f"分词拼接结果：{parsed_all}；合并文本：{char_text}")


