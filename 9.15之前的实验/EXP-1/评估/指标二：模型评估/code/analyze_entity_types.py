# -*- coding: utf-8 -*-
"""
统计脚本：分析50篇评估论文中不同模型抽取的实体类型数量

功能：
1. 读取三个模型（deepseek, gemini, kimi）的抽取结果
2. 统计每个模型抽取的实体类型（type）
3. 生成详细的统计报告

运行：
    python analyze_entity_types.py
"""
import os
import json
from collections import Counter, defaultdict
from datetime import datetime

def get_evaluation_papers():
    """获取需要评估的50篇论文文件名列表（不含扩展名）"""
    evaluation_dir = "e:\\知识图谱构建\\9.15之前的实验\\EXP-1\\评估\\需要评估的论文"
    
    if not os.path.exists(evaluation_dir):
        print(f"错误：找不到评估论文目录: {evaluation_dir}")
        return []
    
    papers = []
    for file in os.listdir(evaluation_dir):
        if file.endswith('.md'):
            # 去掉.md扩展名
            paper_name = file[:-3]
            papers.append(paper_name)
    
    return sorted(papers)

def analyze_entity_types():
    """分析三个模型的实体类型统计"""
    base_dir = "e:\\知识图谱构建\\9.15之前的实验\\EXP-1\\评估\\指标二：模型评估"
    submit_root = os.path.join(base_dir, "提交文件")
    
    # 获取需要评估的论文列表
    evaluation_papers = get_evaluation_papers()
    if not evaluation_papers:
        print("错误：未找到需要评估的论文")
        return
    
    print(f"开始分析 {len(evaluation_papers)} 篇论文的实体类型...")
    
    models = ["deepseek", "gemini", "kimi"]
    
    # 存储统计结果
    model_stats = {}
    all_entity_types = set()
    
    for model in models:
        print(f"\n分析模型: {model}")
        submit_dir = os.path.join(submit_root, model)
        
        if not os.path.exists(submit_dir):
            print(f"警告：提交文件夹不存在: {submit_dir}")
            continue
        
        # 统计该模型的实体类型
        entity_type_counter = Counter()
        total_entities = 0
        valid_files = 0
        
        for paper in evaluation_papers:
            json_filename = f"{paper}.json"
            json_path = os.path.join(submit_dir, json_filename)
            
            if not os.path.exists(json_path):
                print(f"  警告：文件不存在 {json_filename}")
                continue
            
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # 检查数据结构
                entities = data.get("entities", [])
                if not isinstance(entities, list):
                    print(f"  警告：{json_filename} 中 entities 不是列表")
                    continue
                
                valid_files += 1
                
                # 统计该文件中的实体类型
                for entity in entities:
                    if isinstance(entity, dict) and "type" in entity:
                        entity_type = entity["type"]
                        entity_type_counter[entity_type] += 1
                        all_entity_types.add(entity_type)
                        total_entities += 1
                    else:
                        print(f"  警告：{json_filename} 中发现无效实体格式")
                        
            except Exception as e:
                print(f"  错误：读取文件 {json_filename} 失败: {e}")
                continue
        
        model_stats[model] = {
            "total_entities": total_entities,
            "unique_types": len(entity_type_counter),
            "valid_files": valid_files,
            "type_distribution": dict(entity_type_counter),
            "top_10_types": entity_type_counter.most_common(10)
        }
        
        print(f"  处理文件: {valid_files}/{len(evaluation_papers)}")
        print(f"  总实体数: {total_entities}")
        print(f"  实体类型数: {len(entity_type_counter)}")
        print(f"  最常见的5种类型: {entity_type_counter.most_common(5)}")
    
    # 生成综合统计报告
    print(f"\n" + "="*60)
    print("综合统计报告")
    print("="*60)
    
    print(f"总计发现实体类型数量: {len(all_entity_types)}")
    print(f"所有实体类型: {sorted(list(all_entity_types))}")
    
    print(f"\n各模型统计对比:")
    print(f"{'模型':<10} {'文件数':<8} {'总实体数':<10} {'类型数':<8} {'平均实体/文件':<12}")
    print("-" * 60)
    
    for model in models:
        if model in model_stats:
            stats = model_stats[model]
            avg_entities = stats["total_entities"] / max(stats["valid_files"], 1)
            print(f"{model:<10} {stats['valid_files']:<8} {stats['total_entities']:<10} {stats['unique_types']:<8} {avg_entities:.1f}")
    
    # 找出各模型共同的实体类型
    if len(model_stats) >= 2:
        common_types = None
        for model in models:
            if model in model_stats:
                model_types = set(model_stats[model]["type_distribution"].keys())
                if common_types is None:
                    common_types = model_types
                else:
                    common_types = common_types.intersection(model_types)
        
        print(f"\n所有模型共同的实体类型({len(common_types)}个):")
        print(f"{sorted(list(common_types))}")
    
    # 分析每个模型独有的类型
    print(f"\n各模型独有的实体类型:")
    for model in models:
        if model in model_stats:
            model_types = set(model_stats[model]["type_distribution"].keys())
            other_types = set()
            for other_model in models:
                if other_model != model and other_model in model_stats:
                    other_types.update(model_stats[other_model]["type_distribution"].keys())
            
            unique_types = model_types - other_types
            print(f"  {model} 独有类型({len(unique_types)}个): {sorted(list(unique_types))}")
    
    # 保存详细报告到文件
    report = {
        "timestamp": datetime.now().isoformat(),
        "analysis_scope": f"{len(evaluation_papers)} papers",
        "total_unique_entity_types": len(all_entity_types),
        "all_entity_types": sorted(list(all_entity_types)),
        "model_statistics": model_stats,
        "common_types": sorted(list(common_types)) if common_types else [],
    }
    
    # 添加各模型独有类型到报告
    unique_types_by_model = {}
    for model in models:
        if model in model_stats:
            model_types = set(model_stats[model]["type_distribution"].keys())
            other_types = set()
            for other_model in models:
                if other_model != model and other_model in model_stats:
                    other_types.update(model_stats[other_model]["type_distribution"].keys())
            unique_types_by_model[model] = sorted(list(model_types - other_types))
    
    report["unique_types_by_model"] = unique_types_by_model
    
    report_file = os.path.join(base_dir, "entity_types_analysis_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n详细报告已保存到: {report_file}")
    
    # 生成简化的CSV统计表
    csv_file = os.path.join(base_dir, "entity_types_summary.csv")
    with open(csv_file, "w", encoding="utf-8") as f:
        f.write("实体类型,deepseek数量,gemini数量,kimi数量,总计\n")
        
        for entity_type in sorted(all_entity_types):
            counts = []
            total = 0
            for model in models:
                if model in model_stats:
                    count = model_stats[model]["type_distribution"].get(entity_type, 0)
                    counts.append(str(count))
                    total += count
                else:
                    counts.append("0")
            
            f.write(f"{entity_type},{','.join(counts)},{total}\n")
    
    print(f"CSV统计表已保存到: {csv_file}")
    
    return model_stats

if __name__ == "__main__":
    analyze_entity_types()