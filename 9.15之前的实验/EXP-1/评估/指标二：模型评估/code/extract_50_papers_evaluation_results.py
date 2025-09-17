# -*- coding: utf-8 -*-
"""
筛选脚本：提取50篇评估论文的模型评估结果

功能：
1. 读取"需要评估的论文"文件夹中的50篇论文列表
2. 从三个模型的结果文件夹中找到对应的评估结果
3. 复制到新的文件夹"50篇论文评估结果"中
4. 生成统计报告

运行：
    python extract_50_papers_evaluation_results.py
"""
import os
import shutil
import json
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
    
    print(f"找到 {len(papers)} 篇需要评估的论文")
    return sorted(papers)

def extract_evaluation_results():
    """提取50篇论文的评估结果"""
    base_dir = "e:\\知识图谱构建\\9.15之前的实验\\EXP-1\\评估\\指标二：模型评估"
    results_root = os.path.join(base_dir, "结果")
    output_root = os.path.join(base_dir, "50篇论文评估结果")
    
    # 获取需要评估的论文列表
    evaluation_papers = get_evaluation_papers()
    if not evaluation_papers:
        return
    
    # 转换为.json文件名
    needed_files = [f"{paper}.json" for paper in evaluation_papers]
    
    models = ["deepseek", "gemini", "kimi"]
    stats = {
        "total_found": 0,
        "total_missing": 0,
        "per_model": {}
    }
    
    # 确保输出目录存在
    os.makedirs(output_root, exist_ok=True)
    
    print(f"\n开始提取50篇论文的评估结果...")
    
    for model in models:
        results_dir = os.path.join(results_root, model)
        output_dir = os.path.join(output_root, model)
        
        if not os.path.exists(results_dir):
            print(f"警告：结果文件夹不存在: {results_dir}")
            continue
            
        os.makedirs(output_dir, exist_ok=True)
        
        found = 0
        missing = []
        
        print(f"\n处理模型: {model}")
        print(f"从 {results_dir} 复制到 {output_dir}")
        
        # 遍历需要的文件
        for filename in needed_files:
            src_path = os.path.join(results_dir, filename)
            dst_path = os.path.join(output_dir, filename)
            
            if os.path.exists(src_path):
                try:
                    shutil.copy2(src_path, dst_path)
                    found += 1
                    print(f"  ✓ 复制: {filename}")
                except Exception as e:
                    print(f"  ✗ 复制失败: {filename} - {e}")
                    missing.append(filename)
            else:
                missing.append(filename)
                print(f"  ✗ 缺失: {filename}")
        
        stats["per_model"][model] = {
            "found": found,
            "missing": missing,
            "missing_count": len(missing)
        }
        stats["total_found"] += found
        stats["total_missing"] += len(missing)
        
        print(f"  统计 - 找到: {found}, 缺失: {len(missing)}")
    
    # 验证复制的文件内容
    print(f"\n验证复制的评估结果...")
    validation_stats = {}
    
    for model in models:
        output_dir = os.path.join(output_root, model)
        if not os.path.exists(output_dir):
            continue
        
        valid_evaluations = 0
        total_files = 0
        
        for filename in os.listdir(output_dir):
            if not filename.endswith('.json'):
                continue
                
            total_files += 1
            file_path = os.path.join(output_dir, filename)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 检查是否包含评估结果
                if 'evaluation' in data:
                    valid_evaluations += 1
                    
            except Exception as e:
                print(f"  警告：读取文件 {filename} 失败: {e}")
        
        validation_stats[model] = {
            "total_files": total_files,
            "valid_evaluations": valid_evaluations
        }
        
        print(f"  {model}: {total_files} 个文件，{valid_evaluations} 个包含评估结果")
    
    # 生成统计报告
    summary = {
        "timestamp": datetime.now().isoformat(),
        "operation": "extract_50_papers_evaluation_results",
        "target_papers_count": len(evaluation_papers),
        "needed_files_count": len(needed_files),
        "extraction_stats": stats,
        "validation_stats": validation_stats,
        "output_location": output_root
    }
    
    log_file = os.path.join(base_dir, "extract_50_papers_log.json")
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n" + "="*60)
    print("提取操作完成")
    print("="*60)
    print(f"目标论文数量: {len(evaluation_papers)} 篇")
    print(f"每个模型需要文件数: {len(needed_files)}")
    print(f"总计找到文件: {stats['total_found']}")
    print(f"总计缺失文件: {stats['total_missing']}")
    print(f"输出位置: {output_root}")
    print(f"操作日志: {log_file}")
    
    print(f"\n各模型详细统计:")
    for model in models:
        if model in stats["per_model"]:
            model_stats = stats["per_model"][model]
            val_stats = validation_stats.get(model, {})
            print(f"  {model}:")
            print(f"    - 找到文件: {model_stats['found']}")
            print(f"    - 缺失文件: {model_stats['missing_count']}")
            print(f"    - 包含评估结果: {val_stats.get('valid_evaluations', 0)}")
            
            if model_stats['missing']:
                print(f"    - 缺失文件列表: {model_stats['missing'][:5]}{'...' if len(model_stats['missing']) > 5 else ''}")
    
    # 检查是否有完整的评估结果
    complete_evaluations = 0
    for filename in needed_files:
        has_all_models = True
        for model in models:
            file_path = os.path.join(output_root, model, filename)
            if not os.path.exists(file_path):
                has_all_models = False
                break
        if has_all_models:
            complete_evaluations += 1
    
    print(f"\n完整评估结果统计:")
    print(f"  拥有所有三个模型评估结果的论文数: {complete_evaluations}/{len(needed_files)}")
    
    return summary

if __name__ == "__main__":
    extract_evaluation_results()