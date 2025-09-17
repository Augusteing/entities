# -*- coding: utf-8 -*-
"""
筛选脚本：只保留需要评估的50篇论文的抽取结果

功能：
1. 读取"需要评估的论文"文件夹中的50篇论文列表
2. 在三个模型的提交文件夹中，只保留对应的JSON文件
3. 将其他文件移动到备份文件夹，避免删除
4. 生成操作日志

运行：
    python filter_50_papers.py
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

def filter_submission_files():
    """筛选提交文件，只保留需要的50篇"""
    base_dir = "e:\\知识图谱构建\\9.15之前的实验\\EXP-1\\评估\\指标二：模型评估"
    submit_root = os.path.join(base_dir, "提交文件")
    backup_root = os.path.join(base_dir, "备份_原始提交文件")
    
    # 获取需要评估的论文列表
    evaluation_papers = get_evaluation_papers()
    if not evaluation_papers:
        return
    
    # 转换为.json文件名
    needed_files = set(f"{paper}.json" for paper in evaluation_papers)
    
    models = ["deepseek", "gemini", "kimi"]
    stats = {
        "total_moved": 0,
        "total_kept": 0,
        "per_model": {}
    }
    
    # 确保备份目录存在
    os.makedirs(backup_root, exist_ok=True)
    
    for model in models:
        submit_dir = os.path.join(submit_root, model)
        backup_dir = os.path.join(backup_root, model)
        
        if not os.path.exists(submit_dir):
            print(f"警告：提交文件夹不存在: {submit_dir}")
            continue
            
        os.makedirs(backup_dir, exist_ok=True)
        
        moved = 0
        kept = 0
        missing = []
        
        print(f"\n处理模型: {model}")
        
        # 遍历提交文件夹中的所有文件
        for filename in os.listdir(submit_dir):
            if not filename.endswith('.json'):
                continue
                
            src_path = os.path.join(submit_dir, filename)
            
            if filename in needed_files:
                # 需要的文件，保留
                kept += 1
                print(f"  保留: {filename}")
            else:
                # 不需要的文件，移动到备份
                dst_path = os.path.join(backup_dir, filename)
                try:
                    shutil.move(src_path, dst_path)
                    moved += 1
                    print(f"  移动: {filename} -> 备份文件夹")
                except Exception as e:
                    print(f"  错误：移动文件 {filename} 失败: {e}")
        
        # 检查是否有缺失的文件
        existing_files = set(f for f in os.listdir(submit_dir) if f.endswith('.json'))
        for needed_file in needed_files:
            if needed_file not in existing_files:
                missing.append(needed_file)
        
        stats["per_model"][model] = {
            "moved": moved,
            "kept": kept,
            "missing": missing
        }
        stats["total_moved"] += moved
        stats["total_kept"] += kept
        
        print(f"  统计 - 保留: {kept}, 移动: {moved}, 缺失: {len(missing)}")
        if missing:
            print(f"  缺失文件: {missing[:5]}{'...' if len(missing) > 5 else ''}")
    
    # 保存操作日志
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "operation": "filter_50_papers",
        "evaluation_papers_count": len(evaluation_papers),
        "needed_files_count": len(needed_files),
        "statistics": stats,
        "backup_location": backup_root
    }
    
    log_file = os.path.join(base_dir, "filter_operation_log.json")
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n筛选操作完成:")
    print(f"  需要评估的论文: {len(evaluation_papers)} 篇")
    print(f"  总计保留文件: {stats['total_kept']}")
    print(f"  总计移动文件: {stats['total_moved']}")
    print(f"  备份位置: {backup_root}")
    print(f"  操作日志: {log_file}")
    
    # 检查是否所有模型都有完整的50个文件
    all_complete = True
    for model in models:
        model_stats = stats["per_model"].get(model, {})
        if model_stats.get("kept", 0) < len(evaluation_papers):
            all_complete = False
            print(f"  警告: {model} 模型缺少 {len(evaluation_papers) - model_stats.get('kept', 0)} 个文件")
    
    if all_complete:
        print(f"  ✓ 所有模型都有完整的 {len(evaluation_papers)} 个评估文件")
    
    return stats

if __name__ == "__main__":
    print("开始筛选提交文件，只保留需要评估的50篇论文...")
    filter_submission_files()