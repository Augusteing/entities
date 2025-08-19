import re
import json

def extract_title_summary(txt_path, json_output_path):
    with open(txt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 按文献记录分割（以两个换行分割文献记录）
    records = re.split(r'\n\s*\n', content.strip())
    seen_summaries = set()  # 用于记录已处理的摘要内容

    result = []
    for record in records:
        title_match = re.search(r'Title-题名:\s*(.+)', record)
        summary_match = re.search(r'Summary-摘要:\s*(.+)', record)

        if title_match and summary_match:
            title = title_match.group(1).strip()
            summary = summary_match.group(1).strip()
            
            # 可选清洗：去除编号、换行符
            summary_clean = re.sub(r'\d+\)', '', summary).replace('\n', '').strip()
            title_clean = title.replace('\n', '').strip()

             # 如果摘要已出现，则跳过
            if summary_clean in seen_summaries:
                continue
            seen_summaries.add(summary_clean)

            result.append({
                "title": title_clean,
                "summary": summary_clean
            })

    # 保存为 JSON 文件
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ 共处理原始记录 {len(records)} 条，去重后保留 {len(result)} 条摘要")
    print(f"📁 结果已保存至：{json_output_path}")

# 示例调用
extract_title_summary(
    txt_path="PHM-217篇摘要.txt",
    json_output_path="summaries.json"
)
