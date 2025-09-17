import json
import os
import pandas as pd
from collections import defaultdict

def get_evaluation_papers():
    """获取需要评估的论文文件名列表"""
    eval_papers_dir = r"E:\知识图谱构建\9.15之前的实验\EXP-1\评估\需要评估的论文"
    papers = []
    for file in os.listdir(eval_papers_dir):
        if file.endswith('.md'):
            # 去掉.md扩展名，添加.json
            paper_name = file.replace('.md', '.json')
            papers.append(paper_name)
    return papers

def extract_entities_from_json(json_file):
    """从JSON文件中提取实体及其类型"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        entity_types = defaultdict(int)
        
        # 遍历所有实体
        if 'entities' in data:
            for entity in data['entities']:
                if 'type' in entity:  # 修改为使用 'type' 字段
                    entity_type = entity['type']
                    entity_types[entity_type] += 1
        
        return entity_types
    except Exception as e:
        print(f"处理文件 {json_file} 时出错: {e}")
        return defaultdict(int)

def process_model_results(model_name, papers_to_analyze):
    """处理特定模型的结果"""
    model_dir = f"E:\\知识图谱构建\\9.15之前的实验\\EXP-1\\数据结果\\提取结果_by_{model_name}"
    
    all_entity_types = defaultdict(int)
    processed_papers = []
    
    for paper in papers_to_analyze:
        json_file = os.path.join(model_dir, paper)
        if os.path.exists(json_file):
            entity_types = extract_entities_from_json(json_file)
            processed_papers.append(paper)
            
            # 累加实体类型计数
            for entity_type, count in entity_types.items():
                all_entity_types[entity_type] += count
    
    print(f"\n{model_name.upper()} 模型处理了 {len(processed_papers)} 篇论文")
    return all_entity_types

def main():
    # 获取需要评估的论文列表
    papers_to_analyze = get_evaluation_papers()
    print(f"需要评估的论文数量: {len(papers_to_analyze)}")
    
    # 确认论文数量是否为50篇
    if len(papers_to_analyze) != 50:
        print(f"警告：期望50篇论文，但实际找到 {len(papers_to_analyze)} 篇")
        print("论文列表：")
        for i, paper in enumerate(papers_to_analyze, 1):
            print(f"  {i:2d}. {paper}")
    else:
        print("✓ 确认：找到50篇评估论文")
    
    # 处理三个模型的结果
    models = ['gemini', 'deepseek', 'kimi']
    model_results = {}
    
    for model in models:
        print(f"\n正在处理 {model} 模型...")
        entity_types = process_model_results(model, papers_to_analyze)
        model_results[model] = entity_types
    
    # 获取所有出现过的实体类型
    all_entity_types = set()
    for model_data in model_results.values():
        all_entity_types.update(model_data.keys())
    
    all_entity_types = sorted(all_entity_types)
    
    # 创建统计表格
    statistics_data = []
    for entity_type in all_entity_types:
        row = {'type': entity_type}
        for model in models:
            row[model] = model_results[model].get(entity_type, 0)
        statistics_data.append(row)
    
    # 保存到CSV文件
    df = pd.DataFrame(statistics_data)
    output_file = "evaluation_papers_entity_type_counts.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n统计结果已保存到: {output_file}")
    
    # 计算每个模型抽取的实体类型数量（只计算>0的）
    print("\n" + "="*50)
    print("各模型在50篇评估论文中抽取的实体类型数量统计：")
    print("="*50)
    
    for model in models:
        count = sum(1 for entity_type in all_entity_types 
                   if model_results[model].get(entity_type, 0) > 0)
        print(f"{model.capitalize()}: {count} 种实体类型")
    
    # 显示总计信息
    total_entity_types = len(all_entity_types)
    print(f"\n总共发现的实体类型数量: {total_entity_types}")
    
    # 显示每个模型的前10个实体类型（按数量排序）
    print("\n" + "="*50)
    print("各模型抽取数量最多的前10种实体类型：")
    
    for model in models:
        print(f"\n{model.upper()}:")
        sorted_types = sorted(model_results[model].items(), 
                            key=lambda x: x[1], reverse=True)
        for i, (entity_type, count) in enumerate(sorted_types[:10], 1):
            if count > 0:
                print(f"  {i:2d}. {entity_type}: {count}")

if __name__ == "__main__":
    main()