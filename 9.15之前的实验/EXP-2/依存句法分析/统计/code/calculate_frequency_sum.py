#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计算语义句法模式CSV文件中总频次的和
"""

import pandas as pd
import numpy as np

def calculate_total_frequency(csv_file_path):
    """计算CSV文件中总频次列的和"""
    
    try:
        # 读取CSV文件
        df = pd.read_csv(csv_file_path, encoding='utf-8-sig')
        
        # 获取总频次列
        freq_column = df['总频次 (Total Freq)']
        
        # 计算总和
        total_sum = freq_column.sum()
        
        # 统计信息
        print("语义句法模式频次统计分析")
        print("=" * 40)
        print(f"总模式数量: {len(df)}")
        print(f"总频次和: {total_sum}")
        print(f"平均频次: {freq_column.mean():.2f}")
        print(f"最高频次: {freq_column.max()}")
        print(f"最低频次: {freq_column.min()}")
        print(f"频次中位数: {freq_column.median()}")
        
        # 显示频次分布统计
        print("\n频次分布统计:")
        print(f"频次 >= 20: {len(df[df['总频次 (Total Freq)'] >= 20])} 个模式")
        print(f"频次 >= 15: {len(df[df['总频次 (Total Freq)'] >= 15])} 个模式")
        print(f"频次 >= 10: {len(df[df['总频次 (Total Freq)'] >= 10])} 个模式")
        print(f"频次 >= 5: {len(df[df['总频次 (Total Freq)'] >= 5])} 个模式")
        
        # 显示前10个最高频次的模式
        print("\n前10个最高频次的语义模式:")
        top_10 = df.nlargest(10, '总频次 (Total Freq)')
        for idx, row in top_10.iterrows():
            print(f"  {row['语义模式 (Semantic Pattern)']}: {row['总频次 (Total Freq)']} 次")
        
        return total_sum, df
        
    except Exception as e:
        print(f"处理文件时出错: {e}")
        return None, None

def main():
    csv_file = r"e:\知识图谱构建\9.15之前的实验\EXP-3\依存句法分析\统计\统计提取结果\semantic_syntactic_patterns_report_2025-09-14_165241.csv"
    
    total_sum, df = calculate_total_frequency(csv_file)
    
    if total_sum is not None:
        print(f"\n✓ 计算完成！总频次和为: {total_sum}")
    else:
        print("✗ 计算失败！")

if __name__ == "__main__":
    main()