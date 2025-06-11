#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
论文搜索功能演示脚本

本脚本演示了如何使用新增的标签管理和时间范围搜索功能。

使用方法:
1. 标签管理:
   python main.py --tag-action add --tag-name "机器学习" --tag-keywords "machine learning,deep learning,neural network" --tag-categories "cs.LG,cs.AI"
   python main.py --tag-action list
   python main.py --tag-action remove --tag-name "机器学习"

2. 时间范围搜索:
   python main.py --search-time "transformer" --days 7
   python main.py --search "attention mechanism" --start-date "2024-01-01" --end-date "2024-12-31"

3. 通知管理:
   python main.py --check-notifications
   python main.py --list-notifications
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.paper_search.search_engine import PaperSearchEngine
from src.paper_search.tag_manager import TagManager
from src.utils.config_loader import load_config

def demo_tag_management():
    """演示标签管理功能"""
    print("=== 标签管理功能演示 ===")
    
    config = load_config()
    tag_manager = TagManager(config)
    
    # 添加标签
    print("\n1. 添加标签")
    tag_manager.add_tag(
        "深度学习", 
        ["deep learning", "neural network", "CNN", "RNN", "transformer"],
        ["cs.LG", "cs.AI", "cs.CV"]
    )
    
    tag_manager.add_tag(
        "自然语言处理",
        ["natural language processing", "NLP", "language model", "BERT", "GPT"],
        ["cs.CL", "cs.AI"]
    )
    
    # 显示所有标签
    print("\n2. 显示所有标签")
    tag_manager.display_tags()
    
    # 更新标签
    print("\n3. 更新标签")
    tag_manager.update_tag(
        "深度学习",
        keywords=["deep learning", "neural network", "CNN", "RNN", "transformer", "attention"],
        categories=["cs.LG", "cs.AI", "cs.CV", "cs.NE"]
    )
    
    print("\n更新后的标签:")
    tag_manager.display_tags()

def demo_time_search():
    """演示时间范围搜索功能"""
    print("\n=== 时间范围搜索功能演示 ===")
    
    config = load_config()
    search_engine = PaperSearchEngine(config)
    
    # 搜索最近7天的论文
    print("\n1. 搜索最近7天的transformer相关论文")
    results = search_engine.search_by_time_range("transformer", days_back=7)
    print(f"找到 {len(results)} 篇论文")
    if results:
        search_engine.display_results(results[:3])  # 只显示前3篇
    
    # 搜索特定日期范围的论文
    print("\n2. 搜索2024年的attention mechanism相关论文")
    results = search_engine.search(
        "attention mechanism", 
        start_date="2024-01-01", 
        end_date="2024-12-31"
    )
    print(f"找到 {len(results)} 篇论文")
    if results:
        search_engine.display_results(results[:3])  # 只显示前3篇

def demo_notifications():
    """演示通知功能"""
    print("\n=== 通知功能演示 ===")
    
    config = load_config()
    search_engine = PaperSearchEngine(config)
    
    # 检查新论文推送
    print("\n1. 检查新论文推送")
    count = search_engine.check_and_notify_new_papers()
    print(f"发现 {count} 篇匹配的新论文")
    
    # 显示通知历史
    print("\n2. 显示通知历史")
    search_engine.tag_manager.display_notifications(limit=5)

def main():
    """主函数"""
    print("论文搜索功能演示")
    print("==================")
    
    try:
        # 演示标签管理
        demo_tag_management()
        
        # 演示时间搜索
        demo_time_search()
        
        # 演示通知功能
        demo_notifications()
        
        print("\n=== 演示完成 ===")
        print("\n💡 提示: 你可以使用以下命令行参数来使用这些功能:")
        print("\n标签管理:")
        print('  python main.py --tag-action add --tag-name "AI" --tag-keywords "artificial intelligence,machine learning"')
        print('  python main.py --tag-action list')
        print('  python main.py --tag-action remove --tag-name "AI"')
        
        print("\n时间搜索:")
        print('  python main.py --search-time "transformer" --days 7')
        print('  python main.py --search "attention" --start-date "2024-01-01" --end-date "2024-12-31"')
        
        print("\n通知管理:")
        print('  python main.py --check-notifications')
        print('  python main.py --list-notifications')
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        print("请确保配置文件正确，并且网络连接正常。")

if __name__ == "__main__":
    main()