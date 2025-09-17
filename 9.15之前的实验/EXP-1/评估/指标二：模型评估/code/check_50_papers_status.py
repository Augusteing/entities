import os

# 获取需要评估的50篇论文
def get_evaluation_papers():
    evaluation_papers_dir = r"E:\知识图谱构建\9.15之前的实验\EXP-1\评估\需要评估的论文"
    
    if not os.path.exists(evaluation_papers_dir):
        print(f"错误：找不到评估论文目录: {evaluation_papers_dir}")
        return []
    
    papers = []
    for file in os.listdir(evaluation_papers_dir):
        if file.endswith('.md'):
            # 去掉.md扩展名
            paper_name = file[:-3]
            papers.append(paper_name)
    
    print(f"找到 {len(papers)} 篇需要评估的论文")
    return sorted(papers)

# 检查哪些论文已经有了提交文件
def check_submit_files(papers):
    submit_root = r"E:\知识图谱构建\9.15之前的实验\EXP-1\评估\指标二：模型评估\提交文件"
    models = ["deepseek", "gemini", "kimi"]
    
    valid_papers = []
    for paper in papers:
        json_file = f"{paper}.json"
        all_exist = True
        
        for model in models:
            file_path = os.path.join(submit_root, model, json_file)
            if not os.path.isfile(file_path):
                print(f"缺少文件: {model}/{json_file}")
                all_exist = False
                break
        
        if all_exist:
            valid_papers.append(paper)
    
    return valid_papers

# 检查哪些论文已经评估过了
def check_evaluated_files(papers):
    result_root = r"E:\知识图谱构建\9.15之前的实验\EXP-1\评估\指标二：模型评估\结果"
    models = ["deepseek", "gemini", "kimi"]
    
    evaluated_papers = []
    pending_papers = []
    
    for paper in papers:
        json_file = f"{paper}.json"
        all_evaluated = True
        
        for model in models:
            result_path = os.path.join(result_root, model, json_file)
            if not os.path.isfile(result_path):
                all_evaluated = False
                break
        
        if all_evaluated:
            evaluated_papers.append(paper)
        else:
            pending_papers.append(paper)
    
    return evaluated_papers, pending_papers

if __name__ == "__main__":
    print("=== 检查50篇评估论文状态 ===\n")
    
    # 1. 获取评估论文列表
    papers = get_evaluation_papers()
    print(f"\n找到评估论文: {len(papers)} 篇")
    
    # 2. 检查提交文件
    print("\n=== 检查提交文件 ===")
    valid_papers = check_submit_files(papers)
    print(f"有提交文件的论文: {len(valid_papers)} 篇")
    
    if len(valid_papers) < len(papers):
        missing = set(papers) - set(valid_papers)
        print(f"缺少提交文件的论文 ({len(missing)} 篇):")
        for paper in sorted(missing)[:5]:  # 只显示前5篇
            print(f"  - {paper}")
        if len(missing) > 5:
            print(f"  ... 还有 {len(missing)-5} 篇")
    
    # 3. 检查已评估文件
    print("\n=== 检查评估状态 ===")
    evaluated, pending = check_evaluated_files(valid_papers)
    print(f"已评估完成的论文: {len(evaluated)} 篇")
    print(f"待评估的论文: {len(pending)} 篇")
    
    if evaluated:
        print(f"\n已评估的论文示例 (前5篇):")
        for paper in evaluated[:5]:
            print(f"  ✓ {paper}")
        if len(evaluated) > 5:
            print(f"  ... 还有 {len(evaluated)-5} 篇")
    
    if pending:
        print(f"\n待评估的论文 ({len(pending)} 篇):")
        for paper in pending[:10]:  # 显示前10篇待评估的
            print(f"  ○ {paper}")
        if len(pending) > 10:
            print(f"  ... 还有 {len(pending)-10} 篇")
    
    print(f"\n=== 总结 ===")
    print(f"评估论文总数: {len(papers)}")
    print(f"有效论文数量: {len(valid_papers)}")
    print(f"已完成评估: {len(evaluated)}")
    print(f"待评估数量: {len(pending)}")