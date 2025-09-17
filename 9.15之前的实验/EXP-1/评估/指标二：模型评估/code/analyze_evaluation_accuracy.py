# -*- coding: utf-8 -*-
"""
统计脚本：分模型分文章统计评估结果的正确率

功能：
1. 读取三个模型（deepseek, gemini, kimi）的评估结果
2. 分析每篇文章的实体和关系评估正确率
3. 统计各模型的总体表现
4. 生成详细的正确率报告

运行：
    python analyze_evaluation_accuracy.py
"""
import os
import json
from collections import defaultdict
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

def analyze_evaluation_accuracy(paper_data):
    """分析单篇论文的评估正确率"""
    stats = {
        "entities": {"total": 0, "correct": 0, "rate": 0.0},
        "relations": {"total": 0, "correct": 0, "rate": 0.0},
        "overall": {"total": 0, "correct": 0, "rate": 0.0}
    }
    
    # 分析实体
    entities = paper_data.get("entities", [])
    for entity in entities:
        if isinstance(entity, dict) and "evaluation" in entity:
            stats["entities"]["total"] += 1
            evaluation = entity["evaluation"].strip().lower()
            if evaluation in ["正确", "correct", "正确的", "合理", "有效"]:
                stats["entities"]["correct"] += 1
    
    # 分析关系
    relations = paper_data.get("relations", [])
    for relation in relations:
        if isinstance(relation, dict) and "evaluation" in relation:
            stats["relations"]["total"] += 1
            evaluation = relation["evaluation"].strip().lower()
            if evaluation in ["正确", "correct", "正确的", "合理", "有效"]:
                stats["relations"]["correct"] += 1
    
    # 计算正确率
    if stats["entities"]["total"] > 0:
        stats["entities"]["rate"] = stats["entities"]["correct"] / stats["entities"]["total"]
    
    if stats["relations"]["total"] > 0:
        stats["relations"]["rate"] = stats["relations"]["correct"] / stats["relations"]["total"]
    
    # 总体正确率
    stats["overall"]["total"] = stats["entities"]["total"] + stats["relations"]["total"]
    stats["overall"]["correct"] = stats["entities"]["correct"] + stats["relations"]["correct"]
    
    if stats["overall"]["total"] > 0:
        stats["overall"]["rate"] = stats["overall"]["correct"] / stats["overall"]["total"]
    
    return stats

def main():
    base_dir = "e:\\知识图谱构建\\9.15之前的实验\\EXP-1\\评估\\指标二：模型评估"
    results_root = os.path.join(base_dir, "结果")
    
    # 获取需要评估的论文列表
    evaluation_papers = get_evaluation_papers()
    if not evaluation_papers:
        return
    
    print(f"开始分析 {len(evaluation_papers)} 篇论文的评估正确率...")
    
    models = ["deepseek", "gemini", "kimi"]
    all_stats = {}
    
    # 存储所有详细结果
    detailed_results = {}
    
    for model in models:
        print(f"\n分析模型: {model}")
        results_dir = os.path.join(results_root, model)
        
        if not os.path.exists(results_dir):
            print(f"警告：结果文件夹不存在: {results_dir}")
            continue
        
        model_stats = {
            "papers": {},
            "summary": {
                "processed_papers": 0,
                "total_entities": 0,
                "correct_entities": 0,
                "total_relations": 0,
                "correct_relations": 0,
                "entity_accuracy": 0.0,
                "relation_accuracy": 0.0,
                "overall_accuracy": 0.0
            }
        }
        
        processed_count = 0
        
        for paper in evaluation_papers:
            json_filename = f"{paper}.json"
            json_path = os.path.join(results_dir, json_filename)
            
            if not os.path.exists(json_path):
                print(f"  缺失: {json_filename}")
                continue
            
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    paper_data = json.load(f)
                
                # 分析该论文的正确率
                paper_stats = analyze_evaluation_accuracy(paper_data)
                model_stats["papers"][paper] = paper_stats
                
                # 累计统计
                model_stats["summary"]["total_entities"] += paper_stats["entities"]["total"]
                model_stats["summary"]["correct_entities"] += paper_stats["entities"]["correct"]
                model_stats["summary"]["total_relations"] += paper_stats["relations"]["total"]
                model_stats["summary"]["correct_relations"] += paper_stats["relations"]["correct"]
                
                processed_count += 1
                
                print(f"  ✓ {paper}: 实体{paper_stats['entities']['correct']}/{paper_stats['entities']['total']}({paper_stats['entities']['rate']:.2%}), "
                      f"关系{paper_stats['relations']['correct']}/{paper_stats['relations']['total']}({paper_stats['relations']['rate']:.2%}), "
                      f"总体{paper_stats['overall']['correct']}/{paper_stats['overall']['total']}({paper_stats['overall']['rate']:.2%})")
                
            except Exception as e:
                print(f"  错误: 读取文件 {json_filename} 失败: {e}")
                continue
        
        # 计算模型总体统计
        model_stats["summary"]["processed_papers"] = processed_count
        
        if model_stats["summary"]["total_entities"] > 0:
            model_stats["summary"]["entity_accuracy"] = model_stats["summary"]["correct_entities"] / model_stats["summary"]["total_entities"]
        
        if model_stats["summary"]["total_relations"] > 0:
            model_stats["summary"]["relation_accuracy"] = model_stats["summary"]["correct_relations"] / model_stats["summary"]["total_relations"]
        
        total_items = model_stats["summary"]["total_entities"] + model_stats["summary"]["total_relations"]
        correct_items = model_stats["summary"]["correct_entities"] + model_stats["summary"]["correct_relations"]
        if total_items > 0:
            model_stats["summary"]["overall_accuracy"] = correct_items / total_items
        
        all_stats[model] = model_stats
        detailed_results[model] = model_stats
        
        print(f"  {model} 总体统计:")
        print(f"    处理论文数: {processed_count}/{len(evaluation_papers)}")
        print(f"    实体正确率: {model_stats['summary']['correct_entities']}/{model_stats['summary']['total_entities']} = {model_stats['summary']['entity_accuracy']:.2%}")
        print(f"    关系正确率: {model_stats['summary']['correct_relations']}/{model_stats['summary']['total_relations']} = {model_stats['summary']['relation_accuracy']:.2%}")
        print(f"    总体正确率: {correct_items}/{total_items} = {model_stats['summary']['overall_accuracy']:.2%}")
    
    # 生成综合报告
    print(f"\n" + "="*80)
    print("综合正确率报告")
    print("="*80)
    
    print(f"\n模型对比:")
    print(f"{'模型':<10} {'处理论文':<10} {'实体正确率':<12} {'关系正确率':<12} {'总体正确率':<12}")
    print("-" * 70)
    
    for model in models:
        if model in all_stats:
            stats = all_stats[model]["summary"]
            print(f"{model:<10} {stats['processed_papers']:<10} {stats['entity_accuracy']:<11.2%} {stats['relation_accuracy']:<11.2%} {stats['overall_accuracy']:<11.2%}")
    
    # 找出表现最好和最差的论文
    print(f"\n各模型表现分析:")
    for model in models:
        if model not in all_stats:
            continue
        
        papers_stats = all_stats[model]["papers"]
        if not papers_stats:
            continue
        
        # 按总体正确率排序
        sorted_papers = sorted(papers_stats.items(), key=lambda x: x[1]["overall"]["rate"], reverse=True)
        
        print(f"\n{model} 模型:")
        print(f"  表现最好的3篇论文:")
        for i, (paper, stats) in enumerate(sorted_papers[:3]):
            short_name = paper[:50] + "..." if len(paper) > 50 else paper
            print(f"    {i+1}. {short_name}: {stats['overall']['rate']:.2%}")
        
        print(f"  表现最差的3篇论文:")
        for i, (paper, stats) in enumerate(sorted_papers[-3:]):
            short_name = paper[:50] + "..." if len(paper) > 50 else paper
            print(f"    {i+1}. {short_name}: {stats['overall']['rate']:.2%}")
    
    # 保存详细报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "analysis_scope": f"{len(evaluation_papers)} papers",
        "models_analyzed": list(all_stats.keys()),
        "detailed_results": detailed_results,
        "summary": {}
    }
    
    # 添加汇总统计到报告
    for model in models:
        if model in all_stats:
            report["summary"][model] = all_stats[model]["summary"]
    
    report_file = os.path.join(base_dir, "evaluation_accuracy_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 生成CSV报告（按论文）
    csv_file = os.path.join(base_dir, "paper_accuracy_summary.csv")
    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        f.write("论文名称,deepseek_实体正确率,deepseek_关系正确率,deepseek_总体正确率,gemini_实体正确率,gemini_关系正确率,gemini_总体正确率,kimi_实体正确率,kimi_关系正确率,kimi_总体正确率\n")
        
        for paper in evaluation_papers:
            row = [paper]
            for model in models:
                if model in all_stats and paper in all_stats[model]["papers"]:
                    stats = all_stats[model]["papers"][paper]
                    row.extend([
                        f"{stats['entities']['rate']:.4f}",
                        f"{stats['relations']['rate']:.4f}",
                        f"{stats['overall']['rate']:.4f}"
                    ])
                else:
                    row.extend(["", "", ""])  # 缺失数据
            f.write(",".join(row) + "\n")
    
    # 生成CSV报告（模型汇总）
    summary_csv_file = os.path.join(base_dir, "model_accuracy_summary.csv")
    with open(summary_csv_file, "w", encoding="utf-8", newline="") as f:
        f.write("模型,处理论文数,总实体数,正确实体数,实体正确率,总关系数,正确关系数,关系正确率,总项目数,正确项目数,总体正确率\n")
        
        for model in models:
            if model in all_stats:
                stats = all_stats[model]["summary"]
                f.write(f"{model},{stats['processed_papers']},{stats['total_entities']},{stats['correct_entities']},{stats['entity_accuracy']:.4f},{stats['total_relations']},{stats['correct_relations']},{stats['relation_accuracy']:.4f},{stats['total_entities']+stats['total_relations']},{stats['correct_entities']+stats['correct_relations']},{stats['overall_accuracy']:.4f}\n")
    
    print(f"\n报告文件:")
    print(f"  详细报告: {report_file}")
    print(f"  论文统计CSV: {csv_file}")
    print(f"  模型汇总CSV: {summary_csv_file}")

if __name__ == "__main__":
    main()