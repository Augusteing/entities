#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨句子路径与句内路径统计脚本
统计依存句法分析结果中跨句子路径和句内路径的数量
"""

import json
import glob
import os
from pathlib import Path
import pandas as pd
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False

class PathStatistics:
    def __init__(self, input_dir):
        self.input_dir = Path(input_dir)
        self.stats = {
            'total_files': 0,
            'total_pairs': 0,
            'intra_sentence_paths': 0,
            'cross_sentence_paths': 0,
            'path_found': 0,
            'no_path_found': 0,
            'files_stats': []
        }
        
    def analyze_json_files(self):
        """分析所有JSON文件"""
        json_files = list(self.input_dir.glob("*依存路径.json"))
        self.stats['total_files'] = len(json_files)
        
        print(f"发现 {len(json_files)} 个JSON文件")
        
        for json_file in json_files:
            file_stats = self.analyze_single_file(json_file)
            self.stats['files_stats'].append(file_stats)
            
        return self.stats
    
    def analyze_single_file(self, json_file):
        """分析单个JSON文件"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            file_stats = {
                'filename': json_file.stem,
                'total_pairs': 0,
                'intra_sentence_paths': 0,
                'cross_sentence_paths': 0,
                'path_found': 0,
                'no_path_found': 0,
                'aligned_pairs': 0
            }
            
            # 从统计信息获取基础数据
            if 'stats' in data:
                file_stats['total_pairs'] = data['stats'].get('total_pairs', 0)
                file_stats['aligned_pairs'] = data['stats'].get('aligned_pairs', 0)
                file_stats['path_found'] = data['stats'].get('path_found', 0)
                
            # 分析具体的实体对路径
            if 'pairs' in data:
                for pair in data['pairs']:
                    if 'path_type' in pair:
                        if pair['path_type'] == 'intra_sentence':
                            file_stats['intra_sentence_paths'] += 1
                        elif pair['path_type'] == 'cross_sentence':
                            file_stats['cross_sentence_paths'] += 1
                    
                    if 'path' in pair and pair['path']:
                        file_stats['path_found'] += 1
                    else:
                        file_stats['no_path_found'] += 1
            
            # 更新总体统计
            self.stats['total_pairs'] += file_stats['total_pairs']
            self.stats['intra_sentence_paths'] += file_stats['intra_sentence_paths']
            self.stats['cross_sentence_paths'] += file_stats['cross_sentence_paths']
            self.stats['path_found'] += file_stats['path_found']
            self.stats['no_path_found'] += file_stats['no_path_found']
            
            print(f"处理文件: {json_file.name}")
            print(f"  - 总实体对: {file_stats['total_pairs']}")
            print(f"  - 句内路径: {file_stats['intra_sentence_paths']}")
            print(f"  - 跨句路径: {file_stats['cross_sentence_paths']}")
            
            return file_stats
            
        except Exception as e:
            print(f"处理文件 {json_file} 时出错: {e}")
            return {
                'filename': json_file.stem,
                'error': str(e),
                'total_pairs': 0,
                'intra_sentence_paths': 0,
                'cross_sentence_paths': 0,
                'path_found': 0,
                'no_path_found': 0,
                'aligned_pairs': 0
            }
    
    def generate_report(self, output_dir="./"):
        """生成统计报告"""
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        print("\n" + "="*50)
        print("跨句子路径与句内路径统计报告")
        print("="*50)
        print(f"总文件数: {self.stats['total_files']}")
        print(f"总实体对数: {self.stats['total_pairs']}")
        print(f"句内路径数: {self.stats['intra_sentence_paths']}")
        print(f"跨句路径数: {self.stats['cross_sentence_paths']}")
        print(f"找到路径数: {self.stats['path_found']}")
        print(f"未找到路径数: {self.stats['no_path_found']}")
        
        # 计算比例
        total_paths = self.stats['intra_sentence_paths'] + self.stats['cross_sentence_paths']
        if total_paths > 0:
            intra_ratio = self.stats['intra_sentence_paths'] / total_paths * 100
            cross_ratio = self.stats['cross_sentence_paths'] / total_paths * 100
            print(f"\n路径类型分布:")
            print(f"句内路径占比: {intra_ratio:.2f}%")
            print(f"跨句路径占比: {cross_ratio:.2f}%")
        
        # 保存详细统计到CSV
        df = pd.DataFrame(self.stats['files_stats'])
        csv_path = output_dir / "path_statistics_detailed.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"\n详细统计已保存到: {csv_path}")
        
        # 创建可视化图表
        self.create_visualizations(output_dir)
        
        # 创建汇总报告
        self.create_summary_report(output_dir)
    
    def create_visualizations(self, output_dir):
        """创建可视化图表"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. 路径类型分布饼图
        path_types = ['句内路径', '跨句路径']
        path_counts = [self.stats['intra_sentence_paths'], self.stats['cross_sentence_paths']]
        
        axes[0, 0].pie(path_counts, labels=path_types, autopct='%1.1f%%', startangle=90)
        axes[0, 0].set_title('路径类型分布')
        
        # 2. 路径发现情况柱状图
        path_status = ['找到路径', '未找到路径']
        path_status_counts = [self.stats['path_found'], self.stats['no_path_found']]
        
        axes[0, 1].bar(path_status, path_status_counts, color=['green', 'red'])
        axes[0, 1].set_title('路径发现情况')
        axes[0, 1].set_ylabel('数量')
        
        # 3. 文件级别的路径分布
        if len(self.stats['files_stats']) > 0:
            df = pd.DataFrame(self.stats['files_stats'])
            # 选择前20个文件显示
            top_files = df.nlargest(20, 'total_pairs')
            
            x_pos = range(len(top_files))
            width = 0.35
            
            axes[1, 0].bar([p - width/2 for p in x_pos], top_files['intra_sentence_paths'], 
                          width, label='句内路径', color='skyblue')
            axes[1, 0].bar([p + width/2 for p in x_pos], top_files['cross_sentence_paths'], 
                          width, label='跨句路径', color='lightcoral')
            
            axes[1, 0].set_title('前20个文件的路径类型分布')
            axes[1, 0].set_xlabel('文件')
            axes[1, 0].set_ylabel('路径数量')
            axes[1, 0].legend()
            axes[1, 0].tick_params(axis='x', rotation=45)
        
        # 4. 路径类型比例对比
        total_paths = self.stats['intra_sentence_paths'] + self.stats['cross_sentence_paths']
        if total_paths > 0:
            ratios = [
                self.stats['intra_sentence_paths'] / total_paths * 100,
                self.stats['cross_sentence_paths'] / total_paths * 100
            ]
            
            axes[1, 1].bar(path_types, ratios, color=['lightblue', 'orange'])
            axes[1, 1].set_title('路径类型比例对比')
            axes[1, 1].set_ylabel('百分比 (%)')
            
            # 在柱子上显示数值
            for i, v in enumerate(ratios):
                axes[1, 1].text(i, v + 0.5, f'{v:.1f}%', ha='center', va='bottom')
        
        plt.tight_layout()
        plot_path = output_dir / "path_statistics_visualization.png"
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"可视化图表已保存到: {plot_path}")
    
    def create_summary_report(self, output_dir):
        """创建汇总报告"""
        report_path = output_dir / "path_statistics_summary.txt"
        
        total_paths = self.stats['intra_sentence_paths'] + self.stats['cross_sentence_paths']
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("跨句子路径与句内路径统计汇总报告\n")
            f.write("="*50 + "\n\n")
            f.write(f"统计时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("总体统计:\n")
            f.write(f"- 分析文件总数: {self.stats['total_files']}\n")
            f.write(f"- 实体对总数: {self.stats['total_pairs']}\n")
            f.write(f"- 成功提取路径数: {self.stats['path_found']}\n")
            f.write(f"- 未找到路径数: {self.stats['no_path_found']}\n\n")
            
            f.write("路径类型分析:\n")
            f.write(f"- 句内路径数量: {self.stats['intra_sentence_paths']}\n")
            f.write(f"- 跨句路径数量: {self.stats['cross_sentence_paths']}\n")
            f.write(f"- 总路径数量: {total_paths}\n\n")
            
            if total_paths > 0:
                intra_ratio = self.stats['intra_sentence_paths'] / total_paths * 100
                cross_ratio = self.stats['cross_sentence_paths'] / total_paths * 100
                f.write("路径类型比例:\n")
                f.write(f"- 句内路径占比: {intra_ratio:.2f}%\n")
                f.write(f"- 跨句路径占比: {cross_ratio:.2f}%\n\n")
            
            # 分文件统计
            f.write("分文件统计摘要:\n")
            df = pd.DataFrame(self.stats['files_stats'])
            if not df.empty:
                f.write(f"- 平均每个文件的实体对数: {df['total_pairs'].mean():.2f}\n")
                f.write(f"- 平均每个文件的句内路径数: {df['intra_sentence_paths'].mean():.2f}\n")
                f.write(f"- 平均每个文件的跨句路径数: {df['cross_sentence_paths'].mean():.2f}\n")
                f.write(f"- 实体对数最多的文件: {df.loc[df['total_pairs'].idxmax(), 'filename']} ({df['total_pairs'].max()}个)\n")
                f.write(f"- 跨句路径最多的文件: {df.loc[df['cross_sentence_paths'].idxmax(), 'filename']} ({df['cross_sentence_paths'].max()}个)\n")
        
        print(f"汇总报告已保存到: {report_path}")


def main():
    # 设置输入和输出路径
    input_directory = r"e:\知识图谱构建\9.15之前的实验\EXP-3\依存句法分析\路径提取算法\4.在2的基础上优化算法(深层次递归）\依存路径提取结果"
    output_directory = r"e:\知识图谱构建\9.15之前的实验\EXP-3\依存句法分析\统计\依存路径提取结果"
    
    # 创建输出目录
    os.makedirs(output_directory, exist_ok=True)
    
    # 创建统计对象并分析
    stats_analyzer = PathStatistics(input_directory)
    stats_analyzer.analyze_json_files()
    stats_analyzer.generate_report(output_directory)
    
    print(f"\n统计完成！结果已保存到: {output_directory}")


if __name__ == "__main__":
    main()