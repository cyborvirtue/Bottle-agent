#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bottle-Agent: 轻量学术搜索与RAG agent
主入口文件，支持命令行快速启动
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.settings import load_config
from src.paper_search.search_engine import PaperSearchEngine
from src.paper_search.cli_extensions import create_cli_extensions
from src.rag_system.knowledge_base import KnowledgeBaseManager
from src.llm.llm_client import LLMClient
from src.rag_system.embedding_client import EmbeddingClient
from src.ui.cli_interface import CLIInterface
try:
    from src.ui.web_interface import run_streamlit_app
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    print("⚠️  Streamlit未安装，Web界面不可用")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Bottle-Agent: 轻量学术搜索与RAG agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python main.py --mode cli                    # 启动命令行界面
  python main.py --mode web                    # 启动Web界面
  python main.py --search "diffusion models"   # 直接搜索论文
  python main.py --rag --kb llm --query "什么是transformer"  # RAG问答
        """
    )
    
    # 运行模式
    parser.add_argument(
        "--mode", 
        choices=["cli", "web"], 
        default="cli",
        help="运行模式: cli(命令行) 或 web(网页界面)"
    )
    
    # 论文搜索功能
    parser.add_argument(
        "--search", 
        type=str,
        help="直接搜索论文，输入查询关键词"
    )
    
    parser.add_argument(
        "--search-time", 
        type=str,
        help="按时间范围搜索论文，输入查询关键词"
    )
    
    parser.add_argument(
        "--days", 
        type=int,
        default=7,
        help="时间搜索的天数范围（默认7天）"
    )
    
    parser.add_argument(
        "--start-date", 
        type=str,
        help="搜索开始日期 (YYYY-MM-DD)"
    )
    
    parser.add_argument(
        "--end-date", 
        type=str,
        help="搜索结束日期 (YYYY-MM-DD)"
    )
    
    # 标签管理功能
    parser.add_argument(
        "--tag-action", 
        choices=["add", "remove", "list", "update"],
        help="标签操作: add(添加), remove(删除), list(列出), update(更新)"
    )
    
    parser.add_argument(
        "--tag-name", 
        type=str,
        help="标签名称"
    )
    
    parser.add_argument(
        "--tag-keywords", 
        type=str,
        help="标签关键词（逗号分隔）"
    )
    
    parser.add_argument(
        "--tag-categories", 
        type=str,
        help="标签分类（逗号分隔）"
    )
    
    # 通知管理功能
    parser.add_argument(
        "--check-notifications", 
        action="store_true",
        help="检查新论文推送通知"
    )
    
    parser.add_argument(
        "--list-notifications", 
        action="store_true",
        help="列出推送通知"
    )
    
    # RAG功能
    parser.add_argument(
        "--rag", 
        action="store_true",
        help="启用RAG问答模式"
    )
    
    parser.add_argument(
        "--kb", 
        type=str,
        help="指定知识库名称（用于RAG模式）"
    )
    
    parser.add_argument(
        "--query", 
        type=str,
        help="RAG问答查询内容"
    )
    
    # 知识库管理
    parser.add_argument(
        "--create-kb", 
        type=str,
        help="创建新知识库，指定知识库名称"
    )
    
    parser.add_argument(
        "--kb-path", 
        type=str,
        help="知识库对应的文件夹路径"
    )
    
    parser.add_argument(
        "--list-kb", 
        action="store_true",
        help="列出所有知识库"
    )
    
    # 配置选项
    parser.add_argument(
        "--config", 
        type=str,
        default="config.yaml",
        help="配置文件路径"
    )
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config(args.config)
    
    # 初始化组件
    search_engine = PaperSearchEngine(config)
    kb_manager = KnowledgeBaseManager(config)
    cli_extensions = create_cli_extensions(config)
    
    try:
        # 处理标签管理
        if args.tag_action:
            if args.tag_action == "add":
                if not args.tag_name or not args.tag_keywords:
                    print("❌ 添加标签需要指定标签名称(--tag-name)和关键词(--tag-keywords)")
                    return
                keywords = [k.strip() for k in args.tag_keywords.split(',')]
                categories = [c.strip() for c in args.tag_categories.split(',')] if args.tag_categories else []
                cli_extensions.tag_manager.add_tag(args.tag_name, keywords, categories)
            
            elif args.tag_action == "remove":
                if not args.tag_name:
                    print("❌ 删除标签需要指定标签名称(--tag-name)")
                    return
                cli_extensions.tag_manager.remove_tag(args.tag_name)
            
            elif args.tag_action == "list":
                cli_extensions.tag_manager.display_tags()
            
            elif args.tag_action == "update":
                if not args.tag_name:
                    print("❌ 更新标签需要指定标签名称(--tag-name)")
                    return
                keywords = [k.strip() for k in args.tag_keywords.split(',')] if args.tag_keywords else None
                categories = [c.strip() for c in args.tag_categories.split(',')] if args.tag_categories else None
                cli_extensions.tag_manager.update_tag(args.tag_name, keywords=keywords, categories=categories)
            return
        
        # 处理通知管理
        if args.check_notifications:
            print("🔔 检查新论文推送...")
            count = search_engine.check_and_notify_new_papers()
            if count > 0:
                print(f"✅ 发现 {count} 篇匹配的新论文")
                cli_extensions.tag_manager.display_notifications(limit=count)
            else:
                print("📭 暂无新的匹配论文")
            return
        
        if args.list_notifications:
            cli_extensions.tag_manager.display_notifications()
            return
        
        # 处理时间范围搜索
        if args.search_time:
            print(f"🔍 搜索最近 {args.days} 天的论文: {args.search_time}")
            results = search_engine.search_by_time_range(args.search_time, days_back=args.days)
            search_engine.display_results(results)
            return
        
        # 处理日期范围搜索
        if args.search and (args.start_date or args.end_date):
            date_info = ""
            if args.start_date and args.end_date:
                date_info = f" ({args.start_date} 到 {args.end_date})"
            elif args.start_date:
                date_info = f" (从 {args.start_date})"
            elif args.end_date:
                date_info = f" (到 {args.end_date})"
            
            print(f"🔍 搜索论文{date_info}: {args.search}")
            results = search_engine.search(args.search, start_date=args.start_date, end_date=args.end_date)
            search_engine.display_results(results)
            return
        
        # 处理直接搜索
        if args.search:
            print(f"🔍 搜索论文: {args.search}")
            results = search_engine.search(args.search)
            search_engine.display_results(results)
            return
        
        # 处理RAG问答
        if args.rag:
            if not args.kb or not args.query:
                print("❌ RAG模式需要指定知识库(--kb)和查询内容(--query)")
                return
            
            print(f"🧠 RAG问答 - 知识库: {args.kb}, 查询: {args.query}")
            answer = kb_manager.query(args.kb, args.query)
            print(f"\n📝 回答:\n{answer}")
            return
        
        # 处理知识库管理
        if args.create_kb:
            if not args.kb_path:
                print("❌ 创建知识库需要指定文件夹路径(--kb-path)")
                return
            
            print(f"📚 创建知识库: {args.create_kb} -> {args.kb_path}")
            kb_manager.create_knowledge_base(args.create_kb, args.kb_path)
            print("✅ 知识库创建完成")
            return
        
        if args.list_kb:
            print("📚 已有知识库:")
            kb_list = kb_manager.list_knowledge_bases()
            for kb in kb_list:
                print(f"  - {kb}")
            return
        
        # 启动交互界面
        if args.mode == "web":
            run_streamlit_app(search_engine, kb_manager, config)
        else:
            print("💻 启动命令行界面...")
            cli = CLIInterface(search_engine, kb_manager, config)
            cli.run()
            
    except KeyboardInterrupt:
        print("\n👋 再见！")
    except Exception as e:
        print(f"❌ 错误: {e}")
        if config.get('debug', False):
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()